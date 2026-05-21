"""Admin endpoints: user management, audit log, stats."""
import uuid
from fastapi import APIRouter, Depends, HTTPException

from core import (
    db, now_utc, hash_pw, audit,
    require_roles,
    ROLE_ADMIN, ROLE_OWNER_DOCTOR,
    STATUS_CLOSED, ALL_STATUSES,
)
from models import UserCreateIn, UserUpdateIn

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
