"""Admin endpoints: user management, audit log, stats."""
import uuid
from fastapi import APIRouter, Depends, HTTPException

from core import (
    db, now_utc, hash_pw, audit,
    require_roles,
    ROLE_ADMIN, ROLE_OWNER_DOCTOR,
    STATUS_CLOSED, ALL_STATUSES,
)
from models import UserCreateIn, UserUpdateIn, MessagingSettingsIn, AISettingsIn, AITestIn
from messaging import refresh_messaging_cache, provider_status, provider_source
from ai_settings import PROVIDERS, MODELS, KEY_FIELD, ai_settings_summary

router = APIRouter()


@router.get("/admin/users")
async def admin_list_users(user: dict = Depends(require_roles(ROLE_ADMIN))):
    users = await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(100)
    return {"users": users}


@router.post("/admin/users")
async def admin_create_user(payload: UserCreateIn, user: dict = Depends(require_roles(ROLE_ADMIN))):
    existing = await db.users.find_one({"username": payload.username.lower().strip()})
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    new_user = {
        "id": str(uuid.uuid4()),
        "username": payload.username.lower().strip(),
        "name": payload.name,
        "role": payload.role,
        "doctor_id": payload.doctor_id,
        "active": True,
        "password_hash": hash_pw(payload.password),
        "created_at": now_utc().isoformat(),
    }
    await db.users.insert_one(new_user)
    new_user.pop("_id", None)
    new_user.pop("password_hash", None)
    await audit(user, "CREATE", "User", new_user["id"], {"username": new_user["username"]})
    return {"user": new_user}


@router.patch("/admin/users/{user_id}")
async def admin_update_user(user_id: str, payload: UserUpdateIn, user: dict = Depends(require_roles(ROLE_ADMIN))):
    update = {k: v for k, v in payload.model_dump(exclude_none=True).items() if k != "password"}
    if payload.password:
        update["password_hash"] = hash_pw(payload.password)
    if not update:
        raise HTTPException(status_code=400, detail="Nothing to update")
    await db.users.update_one({"id": user_id}, {"$set": update})
    await audit(user, "UPDATE", "User", user_id, {"fields": list(update.keys())})
    u = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    return {"user": u}


@router.delete("/admin/users/{user_id}")
async def admin_delete_user(user_id: str, user: dict = Depends(require_roles(ROLE_ADMIN))):
    target = await db.users.find_one({"id": user_id})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if user_id == user["id"]:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")
    # Don't actually delete owner doctor accounts (data integrity); only mark inactive
    if target.get("role") == ROLE_OWNER_DOCTOR:
        await db.users.update_one({"id": user_id}, {"$set": {"active": False}})
        await audit(user, "DEACTIVATE", "User", user_id, {"reason": "owner_protect"})
        return {"ok": True, "soft_deleted": True}
    await db.users.delete_one({"id": user_id})
    await audit(user, "DELETE", "User", user_id, {"username": target.get("username")})
    return {"ok": True}


@router.get("/admin/audit-logs")
async def admin_audit_logs(limit: int = 200, user: dict = Depends(require_roles(ROLE_ADMIN))):
    logs = await db.audit_logs.find({}, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    return {"audit_logs": logs}


@router.get("/admin/stats")
async def admin_stats(user: dict = Depends(require_roles(ROLE_ADMIN, ROLE_OWNER_DOCTOR))):
    total_patients = await db.patients.count_documents({})
    total_cases = await db.cases.count_documents({})
    closed_cases = await db.cases.count_documents({"status": STATUS_CLOSED})
    pending_cases = await db.cases.count_documents({"status": {"$nin": [STATUS_CLOSED]}})

    by_status = {}
    for s in ALL_STATUSES:
        by_status[s] = await db.cases.count_documents({"status": s})

    doctors = await db.doctor_profiles.find({}, {"_id": 0}).to_list(20)
    by_doctor = []
    for d in doctors:
        count = await db.cases.count_documents({"assigned_doctor_id": d["id"]})
        by_doctor.append({"doctor": d["display_name"], "cases": count})

    pipeline = [
        {"$match": {"payment_status": "PAID"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount_paid"}}},
    ]
    rev = await db.payments.aggregate(pipeline).to_list(1)
    total_revenue = rev[0]["total"] if rev else 0

    return {
        "total_patients": total_patients,
        "total_cases": total_cases,
        "closed_cases": closed_cases,
        "pending_cases": pending_cases,
        "by_status": by_status,
        "by_doctor": by_doctor,
        "total_revenue": total_revenue,
    }



def _mask(value: str | None) -> str:
    if not value:
        return ""
    if len(value) <= 6:
        return "•" * len(value)
    return f"{value[:3]}{'•' * (len(value) - 6)}{value[-3:]}"


@router.get("/admin/messaging-settings")
async def get_messaging_settings(user: dict = Depends(require_roles(ROLE_ADMIN))):
    """Return masked stored creds plus provider status/source for the admin UI."""
    doc = await db.settings.find_one({"_id": "messaging"}) or {}
    masked = {k: _mask(v) for k, v in doc.items() if k != "_id"}
    return {
        "stored": masked,            # e.g. {"TWILIO_ACCOUNT_SID": "AC•••XYZ"}
        "status": provider_status(),  # bool flags per channel
        "source": provider_source(),  # "db" | "env" | "partial" | "none" per channel
    }


@router.post("/admin/messaging-settings")
async def set_messaging_settings(
    payload: MessagingSettingsIn,
    user: dict = Depends(require_roles(ROLE_ADMIN)),
):
    """Persist provided fields (non-empty). Empty/missing fields are left as-is.
    Pass an explicit empty-string sentinel "__CLEAR__" to clear a field.
    """
    raw = payload.model_dump(exclude_none=True)
    to_set: dict = {}
    to_unset: dict = {}
    for k, v in raw.items():
        if v == "__CLEAR__":
            to_unset[k] = ""
        elif v.strip():
            to_set[k] = v.strip()
    if not (to_set or to_unset):
        raise HTTPException(status_code=400, detail="Nothing to update")
    update: dict = {}
    if to_set:
        update["$set"] = to_set
    if to_unset:
        update["$unset"] = to_unset
    await db.settings.update_one({"_id": "messaging"}, update, upsert=True)
    await refresh_messaging_cache(db)
    await audit(user, "UPDATE", "MessagingSettings", "messaging", {
        "set": list(to_set.keys()), "cleared": list(to_unset.keys()),
    })
    return {
        "ok": True,
        "status": provider_status(),
        "source": provider_source(),
    }


# ─── AI provider settings ───

@router.get("/admin/ai-settings")
async def get_ai_settings(user: dict = Depends(require_roles(ROLE_ADMIN))):
    doc = await db.settings.find_one({"_id": "ai"}) or {}
    masked = {k: _mask(v) for k, v in doc.items() if k in KEY_FIELD.values()}
    summary = await ai_settings_summary(db)
    return {"stored": masked, **summary}


@router.post("/admin/ai-settings")
async def set_ai_settings(
    payload: AISettingsIn,
    user: dict = Depends(require_roles(ROLE_ADMIN)),
):
    raw = payload.model_dump(exclude_none=True)
    if raw.get("AI_PROVIDER") and raw["AI_PROVIDER"] not in PROVIDERS:
        raise HTTPException(status_code=400, detail=f"AI_PROVIDER must be one of {PROVIDERS}")
    if raw.get("AI_MODEL"):
        provider = raw.get("AI_PROVIDER")
        if not provider:
            doc = await db.settings.find_one({"_id": "ai"}) or {}
            provider = doc.get("AI_PROVIDER") or "anthropic"
        if raw["AI_MODEL"] not in MODELS.get(provider, []):
            raise HTTPException(status_code=400, detail=f"Unknown model for {provider}")
    to_set: dict = {}
    to_unset: dict = {}
    for k, v in raw.items():
        if v == "__CLEAR__":
            to_unset[k] = ""
        elif v.strip():
            to_set[k] = v.strip()
    if not (to_set or to_unset):
        raise HTTPException(status_code=400, detail="Nothing to update")
    update: dict = {}
    if to_set:
        update["$set"] = to_set
    if to_unset:
        update["$unset"] = to_unset
    await db.settings.update_one({"_id": "ai"}, update, upsert=True)
    await audit(user, "UPDATE", "AISettings", "ai", {
        "set": list(to_set.keys()), "cleared": list(to_unset.keys()),
    })
    summary = await ai_settings_summary(db)
    return {"ok": True, **summary}


@router.post("/admin/ai-settings/test")
async def test_ai_key(
    payload: AITestIn,
    user: dict = Depends(require_roles(ROLE_ADMIN)),
):
    """Fire a tiny prompt at the provider with the given (or stored) key."""
    if payload.provider not in PROVIDERS:
        raise HTTPException(status_code=400, detail=f"provider must be one of {PROVIDERS}")
    key = (payload.api_key or "").strip()
    if not key:
        doc = await db.settings.find_one({"_id": "ai"}) or {}
        key = (doc.get(KEY_FIELD[payload.provider]) or "").strip()
    if not key:
        raise HTTPException(status_code=400, detail="No key provided and none stored for this provider")
    model = MODELS[payload.provider][0]
    try:
        import uuid as _uuid
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = LlmChat(
            api_key=key,
            session_id=f"keytest-{_uuid.uuid4()}",
            system_message="You are a connectivity test. Reply with exactly: OK",
        ).with_model(payload.provider, model)
        reply = await chat.send_message(UserMessage(text="Reply with exactly: OK"))
        return {"ok": True, "provider": payload.provider, "model": model, "reply": str(reply)[:100]}
    except Exception as e:
        return {"ok": False, "provider": payload.provider, "model": model, "error": str(e)[:300]}
