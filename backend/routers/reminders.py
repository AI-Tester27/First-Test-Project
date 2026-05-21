"""Reminders: list, send-now, background scheduler."""
import asyncio
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException

from core import (
    db, now_utc, audit,
    get_current_user, require_roles, load_case_for_user,
    ROLE_DOCTOR, ROLE_OWNER_DOCTOR, ROLE_ADMIN,
)
from messaging import send_whatsapp, send_sms, provider_status

router = APIRouter()
log = logging.getLogger(__name__)


@router.get("/reminders")
async def list_reminders(user: dict = Depends(get_current_user)):
    q = {}
    if user["role"] == ROLE_DOCTOR:
        q["doctor_id"] = user.get("doctor_id")
    reminders = await db.reminders.find(q, {"_id": 0}).sort("scheduled_at", 1).limit(50).to_list(50)
    return {"reminders": reminders, "providers": provider_status()}


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
