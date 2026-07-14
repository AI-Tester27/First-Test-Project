"""Cases: CRUD + status transitions + clinical notes + prescriptions + follow-up."""
import uuid
from datetime import datetime, time, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

from core import (
    db, now_utc, next_counter, audit,
    get_current_user, require_roles,
    load_case_for_user, enrich_case, case_filter_for_role,
    ROLE_OWNER_DOCTOR, ROLE_DOCTOR, ROLE_RECEPTION, ROLE_PHARMACY, ROLE_PRO, ROLE_ADMIN,
    ALL_STATUSES,
    STATUS_WAITING, STATUS_IN_CONSULT, STATUS_AWAITING_PRO, STATUS_SENT_PHARMACY,
    STATUS_IN_PHARMACY, STATUS_READY_BILLING,
    STATUS_PAYMENT_PENDING, STATUS_PARTIALLY_PAID, STATUS_CLOSED,
)
from models import (
    CaseCreateIn, StatusUpdateIn, ClinicalNoteIn, PrescriptionIn, FollowupIn,
)

router = APIRouter()


@router.get("/cases")
async def list_cases(status: Optional[str] = None, user: dict = Depends(get_current_user)):
    q = case_filter_for_role(user)
    if status:
        if "," in status:
            q["status"] = {"$in": status.split(",")}
        else:
            q["status"] = status
    cases = await db.cases.find(q, {"_id": 0}).sort("created_at", -1).limit(200).to_list(200)
    enriched = [await enrich_case(c) for c in cases]
    return {"cases": enriched}


@router.post("/cases")
async def create_case(
    payload: CaseCreateIn,
    user: dict = Depends(require_roles(ROLE_RECEPTION, ROLE_OWNER_DOCTOR, ROLE_ADMIN)),
):
    patient = await db.patients.find_one({"id": payload.patient_id})
    doctor = await db.doctor_profiles.find_one({"id": payload.assigned_doctor_id})
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    seq = await next_counter("case_uid")
    doc = {
        "id": str(uuid.uuid4()),
        "case_uid": f"CASE-{seq:06d}",
        "patient_id": payload.patient_id,
        "assigned_doctor_id": payload.assigned_doctor_id,
        "complaint_text": payload.complaint_text,
        "status": STATUS_WAITING,
        "next_followup_at": None,
        "followup_note": None,
        "created_by": user["id"],
        "created_at": now_utc().isoformat(),
        "updated_at": now_utc().isoformat(),
    }
    await db.cases.insert_one(doc)
    doc.pop("_id", None)
    await audit(user, "CREATE", "Case", doc["id"], {"case_uid": doc["case_uid"]})
    return {"case": await enrich_case(doc)}


@router.get("/cases/{case_id}")
async def get_case(case_id: str, user: dict = Depends(get_current_user)):
    c = await load_case_for_user(case_id, user)
    patient = await db.patients.find_one({"id": c["patient_id"]}, {"_id": 0})
    doctor = await db.doctor_profiles.find_one({"id": c["assigned_doctor_id"]}, {"_id": 0})

    role = user["role"]
    response: dict = {"case": {**c, "patient": patient, "doctor": doctor}}

    if role in (ROLE_OWNER_DOCTOR, ROLE_DOCTOR, ROLE_ADMIN):
        note = await db.clinical_notes.find_one({"case_id": case_id}, {"_id": 0})
        response["clinical_notes"] = note

    if role in (ROLE_OWNER_DOCTOR, ROLE_DOCTOR, ROLE_PHARMACY, ROLE_ADMIN):
        prescriptions = await db.prescriptions.find({"case_id": case_id}, {"_id": 0}).sort("version_no", -1).to_list(20)
        response["prescriptions"] = prescriptions
        response["latest_prescription"] = prescriptions[0] if prescriptions else None

    if role in (ROLE_PHARMACY, ROLE_OWNER_DOCTOR, ROLE_DOCTOR, ROLE_ADMIN):
        dispense = await db.pharmacy_dispense.find_one({"case_id": case_id}, {"_id": 0})
        response["pharmacy_dispense"] = dispense

    if role in (ROLE_PRO, ROLE_OWNER_DOCTOR, ROLE_RECEPTION, ROLE_ADMIN):
        payment = await db.payments.find_one({"case_id": case_id}, {"_id": 0})
        response["payment"] = payment

    return response


@router.patch("/cases/{case_id}/status")
async def update_case_status(case_id: str, payload: StatusUpdateIn, user: dict = Depends(get_current_user)):
    c = await load_case_for_user(case_id, user)
    if payload.status not in ALL_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    role = user["role"]
    # New workflow: Reception → Doctor → PRO → Pharmacy → Completed.
    # Doctor's default exit is AWAITING_PRO_REVIEW; SENT_TO_PHARMACY is a controlled bypass
    # (requires bypass_reason — e.g. quick refills for known patients).
    allowed = {
        ROLE_DOCTOR: {STATUS_IN_CONSULT, STATUS_AWAITING_PRO, STATUS_SENT_PHARMACY},
        ROLE_OWNER_DOCTOR: set(ALL_STATUSES),
        ROLE_ADMIN: set(ALL_STATUSES),
        # Pharmacy now closes the case after dispensing (formerly forwarded to billing).
        ROLE_PHARMACY: {STATUS_IN_PHARMACY, STATUS_CLOSED, STATUS_READY_BILLING},
        # PRO now forwards to pharmacy after billing.
        ROLE_PRO: {STATUS_PAYMENT_PENDING, STATUS_PARTIALLY_PAID, STATUS_CLOSED, STATUS_SENT_PHARMACY},
    }
    if payload.status not in allowed.get(role, set()):
        raise HTTPException(status_code=403, detail=f"Role {role} cannot set status {payload.status}")

    # Doctor bypass-to-pharmacy must include an audit-friendly reason.
    if role == ROLE_DOCTOR and payload.status == STATUS_SENT_PHARMACY:
        if not (payload.bypass_reason and payload.bypass_reason.strip()):
            raise HTTPException(
                status_code=400,
                detail="A bypass reason is required when a doctor sends a case directly to pharmacy (skipping PRO).",
            )

    updates = {"status": payload.status, "updated_at": now_utc().isoformat()}
    if payload.status == STATUS_IN_CONSULT:
        updates["consultation_started_at"] = now_utc().isoformat()
    if payload.status == STATUS_AWAITING_PRO:
        updates["consultation_completed_at"] = now_utc().isoformat()
        updates["sent_to_pro_at"] = now_utc().isoformat()
    if payload.status == STATUS_SENT_PHARMACY:
        # Set consultation_completed_at only if doctor bypass; otherwise PRO forwarding doesn't change it.
        if role == ROLE_DOCTOR:
            updates["consultation_completed_at"] = now_utc().isoformat()
            updates["pharmacy_bypass_reason"] = payload.bypass_reason.strip()
            updates["pharmacy_bypassed_pro"] = True
        updates["sent_to_pharmacy_at"] = now_utc().isoformat()
    if payload.status == STATUS_READY_BILLING:
        updates["ready_for_billing_at"] = now_utc().isoformat()
    if payload.status == STATUS_CLOSED:
        updates["closed_at"] = now_utc().isoformat()

    await db.cases.update_one({"id": case_id}, {"$set": updates})
    await audit(user, "STATUS_CHANGE", "Case", case_id, {
        "from": c["status"], "to": payload.status,
        **({"bypass_reason": payload.bypass_reason} if payload.bypass_reason else {}),
    })
    updated = await db.cases.find_one({"id": case_id}, {"_id": 0})
    return {"case": await enrich_case(updated)}


@router.put("/cases/{case_id}/notes")
async def save_notes(
    case_id: str,
    payload: ClinicalNoteIn,
    user: dict = Depends(require_roles(ROLE_OWNER_DOCTOR, ROLE_DOCTOR, ROLE_ADMIN)),
):
    await load_case_for_user(case_id, user)
    note_doc = {
        "case_id": case_id,
        **payload.model_dump(),
        "updated_by": user["id"],
        "updated_at": now_utc().isoformat(),
    }
    await db.clinical_notes.update_one(
        {"case_id": case_id},
        {"$set": note_doc, "$setOnInsert": {"created_by": user["id"], "created_at": now_utc().isoformat()}},
        upsert=True,
    )
    await audit(user, "UPDATE", "ClinicalNote", case_id)
    saved = await db.clinical_notes.find_one({"case_id": case_id}, {"_id": 0})
    return {"clinical_notes": saved}


@router.post("/cases/{case_id}/prescription")
async def save_prescription(
    case_id: str,
    payload: PrescriptionIn,
    user: dict = Depends(require_roles(ROLE_OWNER_DOCTOR, ROLE_DOCTOR, ROLE_PHARMACY, ROLE_ADMIN)),
):
    await load_case_for_user(case_id, user)
    latest = await db.prescriptions.find({"case_id": case_id}).sort("version_no", -1).limit(1).to_list(1)
    next_v = (latest[0]["version_no"] + 1) if latest else 1
    edited_by_pharmacy = user["role"] == ROLE_PHARMACY
    doc = {
        "id": str(uuid.uuid4()),
        "case_id": case_id,
        "version_no": next_v,
        "items": [it.model_dump() for it in payload.items],
        "notes_for_patient": payload.notes_for_patient or "",
        "notes_internal": payload.notes_internal or "",
        "created_by_user_id": user["id"],
        "edited_by_pharmacy": edited_by_pharmacy,
        "created_at": now_utc().isoformat(),
    }
    await db.prescriptions.insert_one(doc)
    doc.pop("_id", None)
    await audit(
        user,
        "PRESCRIPTION_EDIT" if edited_by_pharmacy else "PRESCRIPTION_CREATE",
        "Prescription", doc["id"], {"version": next_v},
    )
    return {"prescription": doc}


@router.post("/cases/{case_id}/followup")
async def set_followup(
    case_id: str,
    payload: FollowupIn,
    user: dict = Depends(require_roles(ROLE_OWNER_DOCTOR, ROLE_DOCTOR, ROLE_ADMIN)),
):
    c = await load_case_for_user(case_id, user)
    patient = await db.patients.find_one({"id": c["patient_id"]})
    # Anchor the date-only follow-up to 09:00 IST of that day for scheduler delivery.
    ist = timezone(timedelta(hours=5, minutes=30))
    scheduled_dt = datetime.combine(payload.next_followup_date, time(9, 0, tzinfo=ist)).astimezone(timezone.utc)
    scheduled_iso = scheduled_dt.isoformat()
    followup_date_iso = payload.next_followup_date.isoformat()  # YYYY-MM-DD (display)
    await db.cases.update_one(
        {"id": case_id},
        {"$set": {
            "next_followup_at": scheduled_iso,        # kept for legacy/scheduler use
            "next_followup_date": followup_date_iso,  # date-only for display
            "followup_note": payload.followup_note or "",
            "updated_at": now_utc().isoformat(),
        }},
    )
    await db.reminders.insert_one({
        "id": str(uuid.uuid4()),
        "case_id": case_id,
        "patient_id": c["patient_id"],
        "patient_name": f"{patient['first_name']} {patient['last_name']}" if patient else "",
        "patient_uid": patient.get("patient_uid") if patient else "",
        "patient_phone": patient.get("phone") if patient else "",
        "doctor_id": c["assigned_doctor_id"],
        "scheduled_at": scheduled_iso,
        "scheduled_date": followup_date_iso,
        "message": payload.followup_note or "Follow-up due",
        "audience": ["DOCTOR", "PHARMACY"] if payload.notify_pharmacy else ["DOCTOR"],
        "status": "PENDING",
        "created_at": now_utc().isoformat(),
    })
    await audit(user, "FOLLOWUP_SET", "Case", case_id, {"date": followup_date_iso})
    return {"ok": True, "scheduled_date": followup_date_iso}
