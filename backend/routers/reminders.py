"""Reminders: list, send-now, mark complete, snooze, delete, manual create, background scheduler."""
import asyncio
import logging
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException

from core import (
    db, now_utc, audit,
    get_current_user, require_roles, load_case_for_user,
    ROLE_DOCTOR, ROLE_OWNER_DOCTOR, ROLE_PHARMACY, ROLE_ADMIN,
)
from models import ReminderCreateIn, ReminderUpdateIn
from messaging import send_whatsapp, send_sms, provider_status

router = APIRouter()
log = logging.getLogger(__name__)


def _scope_filter(user: dict) -> dict:
    role = user["role"]
    if role == ROLE_DOCTOR:
        return {"doctor_id": user.get("doctor_id")}
    if role == ROLE_PHARMACY:
        return {"audience": "PHARMACY"}
    return {}


@router.get("/reminders")
async def list_reminders(status: str | None = None, user: dict = Depends(get_current_user)):
    q = _scope_filter(user)
    if status:
        q["status"] = {"$in": status.split(",")}
    reminders = await db.reminders.find(q, {"_id": 0}).sort("scheduled_at", 1).limit(200).to_list(200)
    return {"reminders": reminders, "providers": provider_status()}


@router.post("/reminders")
async def create_reminder(
    payload: ReminderCreateIn,
    user: dict = Depends(require_roles(ROLE_OWNER_DOCTOR, ROLE_DOCTOR, ROLE_ADMIN)),
):
    patient = await db.patients.find_one({"id": payload.patient_id})
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    doctor_id = user.get("doctor_id") or (await db.cases.find_one({"id": payload.case_id}) or {}).get("assigned_doctor_id")
    audience = list(set(payload.audience + (["PHARMACY"] if payload.notify_pharmacy else [])))
    doc = {
        "id": str(uuid.uuid4()),
        "case_id": payload.case_id,
        "patient_id": payload.patient_id,
        "patient_name": f"{patient['first_name']} {patient['last_name']}",
        "patient_uid": patient.get("patient_uid"),
        "doctor_id": doctor_id,
        "scheduled_at": payload.scheduled_at.isoformat(),
        "message": payload.message,
        "audience": audience,
        "status": "PENDING",
        "created_by": user["id"],
        "created_at": now_utc().isoformat(),
    }
    await db.reminders.insert_one(doc)
    doc.pop("_id", None)
    await audit(user, "CREATE", "Reminder", doc["id"], {"audience": audience})
    return {"reminder": doc}


@router.patch("/reminders/{reminder_id}")
async def update_reminder(
    reminder_id: str,
    payload: ReminderUpdateIn,
    user: dict = Depends(get_current_user),
):
    r = await db.reminders.find_one({"id": reminder_id})
    if not r:
        raise HTTPException(status_code=404, detail="Reminder not found")
    # scope check
    role = user["role"]
    if role == ROLE_DOCTOR and r.get("doctor_id") != user.get("doctor_id"):
        raise HTTPException(status_code=403, detail="Not your reminder")
    if role == ROLE_PHARMACY and "PHARMACY" not in (r.get("audience") or []):
        raise HTTPException(status_code=403, detail="Not your reminder")
    update = {}
    if payload.status:
        update["status"] = payload.status
        if payload.status == "COMPLETED":
            update["completed_at"] = now_utc().isoformat()
            update["completed_by"] = user["id"]
            update["completed_by_name"] = user.get("name")
    if payload.snooze_until:
        update["scheduled_at"] = payload.snooze_until.isoformat()
        update["status"] = "PENDING"
        update["snoozed_at"] = now_utc().isoformat()
    if payload.message is not None:
        update["message"] = payload.message
    if payload.notes is not None:
        update["notes"] = payload.notes
    if not update:
        raise HTTPException(status_code=400, detail="Nothing to update")
    update["updated_at"] = now_utc().isoformat()
    await db.reminders.update_one({"id": reminder_id}, {"$set": update})
    await audit(user, "UPDATE", "Reminder", reminder_id, {"fields": list(update.keys())})
    fresh = await db.reminders.find_one({"id": reminder_id}, {"_id": 0})
    return {"reminder": fresh}


@router.delete("/reminders/{reminder_id}")
async def delete_reminder(
    reminder_id: str,
    user: dict = Depends(require_roles(ROLE_OWNER_DOCTOR, ROLE_DOCTOR, ROLE_ADMIN)),
):
    r = await db.reminders.find_one({"id": reminder_id})
    if not r:
        raise HTTPException(status_code=404, detail="Reminder not found")
    if user["role"] == ROLE_DOCTOR and r.get("doctor_id") != user.get("doctor_id"):
        raise HTTPException(status_code=403, detail="Not your reminder")
    await db.reminders.delete_one({"id": reminder_id})
    await audit(user, "DELETE", "Reminder", reminder_id)
    return {"ok": True}


@router.post("/reminders/{reminder_id}/send-now")
async def send_reminder_now(
    reminder_id: str,
    user: dict = Depends(require_roles(ROLE_OWNER_DOCTOR, ROLE_DOCTOR, ROLE_ADMIN)),
):
    r = await db.reminders.find_one({"id": reminder_id})
    if not r:
        raise HTTPException(status_code=404, detail="Reminder not found")
    await deliver_reminder(r)
    await audit(user, "REMINDER_SEND_NOW", "Reminder", reminder_id)
    fresh = await db.reminders.find_one({"id": reminder_id}, {"_id": 0})
    return {"reminder": fresh}


async def deliver_reminder(reminder: dict) -> None:
    """Attempt WhatsApp first, fall back to SMS. Mark SENT/FAILED."""
    if reminder.get("status") == "COMPLETED":
        return
    patient = await db.patients.find_one({"id": reminder["patient_id"]})
    if not patient or not patient.get("phone"):
        await db.reminders.update_one({"id": reminder["id"]}, {"$set": {
            "status": "FAILED", "fail_reason": "NO_PHONE", "sent_at": now_utc().isoformat(),
        }})
        return
    lang = patient.get("preferred_language", "EN")
    name = f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip()
    when = reminder.get("scheduled_at", "")
    try:
        when_dt = datetime.fromisoformat(when.replace("Z", "+00:00"))
        when_str = when_dt.strftime("%d-%b-%Y %I:%M %p")
    except Exception:
        when_str = when
    if lang == "TE":
        body = f"నమస్తే {name},\nమీ ఫాలో-అప్ {when_str}కి సిద్ధంగా ఉంది. — Sparsa Homeoclinic"
    else:
        body = f"Hi {name}, your follow-up is on {when_str}. — Sparsa Homeoclinic"
    if reminder.get("message"):
        body += f"\n{reminder['message']}"

    ok_wa, reason_wa = send_whatsapp(patient["phone"], body)
    if ok_wa:
        await db.reminders.update_one({"id": reminder["id"]}, {"$set": {
            "status": "SENT", "channel": "WHATSAPP", "sent_at": now_utc().isoformat(),
            "message_rendered": body,
        }})
        return
    ok_sms, reason_sms = send_sms(patient["phone"], body)
    if ok_sms:
        await db.reminders.update_one({"id": reminder["id"]}, {"$set": {
            "status": "SENT", "channel": "SMS", "sent_at": now_utc().isoformat(),
            "message_rendered": body, "fail_reason": f"WA: {reason_wa}",
        }})
        return
    await db.reminders.update_one({"id": reminder["id"]}, {"$set": {
        "status": "FAILED", "fail_reason": f"WA: {reason_wa} | SMS: {reason_sms}",
        "sent_at": now_utc().isoformat(),
    }})


async def reminder_scheduler():
    """Background task — every 60s, deliver any PENDING reminder whose scheduled_at has passed."""
    while True:
        try:
            now_iso = now_utc().isoformat()
            cur = db.reminders.find({"status": "PENDING", "scheduled_at": {"$lte": now_iso}}).limit(20)
            async for r in cur:
                await deliver_reminder(r)
        except Exception:
            log.exception("reminder_scheduler error")
        await asyncio.sleep(60)
