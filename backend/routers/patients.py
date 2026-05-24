"""Doctors list + Patients CRUD + visit timeline + historical (past) visits."""
import uuid
from fastapi import APIRouter, Depends, HTTPException

from core import (
    db, now_utc, next_counter, audit,
    get_current_user, require_roles, case_filter_for_role,
    ROLE_RECEPTION, ROLE_OWNER_DOCTOR, ROLE_ADMIN, ROLE_DOCTOR, ROLE_PHARMACY,
    STATUS_CLOSED,
)
from models import PatientIn, PastVisitIn

router = APIRouter()


# ─── Doctors ───
@router.get("/doctors")
async def list_doctors(user: dict = Depends(get_current_user)):
    docs = await db.doctor_profiles.find({}, {"_id": 0}).to_list(50)
    return {"doctors": docs}


# ─── Patients ───
@router.get("/patients")
async def list_patients(search: str = "", user: dict = Depends(get_current_user)):
    if user["role"] not in (ROLE_RECEPTION, ROLE_OWNER_DOCTOR, ROLE_ADMIN, ROLE_DOCTOR):
        raise HTTPException(status_code=403, detail="Not allowed")
    q = {}
    if search:
        q = {"$or": [
            {"first_name": {"$regex": search, "$options": "i"}},
            {"last_name": {"$regex": search, "$options": "i"}},
            {"phone": {"$regex": search, "$options": "i"}},
            {"patient_uid": {"$regex": search, "$options": "i"}},
        ]}
    patients = await db.patients.find(q, {"_id": 0}).sort("created_at", -1).limit(100).to_list(100)
    return {"patients": patients}


@router.post("/patients")
async def create_patient(
    payload: PatientIn,
    user: dict = Depends(require_roles(ROLE_RECEPTION, ROLE_OWNER_DOCTOR, ROLE_ADMIN)),
):
    seq = await next_counter("patient_uid")
    patient_uid = f"SPARSA-{seq:06d}"
    doc = {
        "id": str(uuid.uuid4()),
        "patient_uid": patient_uid,
        **payload.model_dump(),
        "created_by": user["id"],
        "created_at": now_utc().isoformat(),
    }
    await db.patients.insert_one(doc)
    doc.pop("_id", None)
    await audit(user, "CREATE", "Patient", doc["id"], {"patient_uid": patient_uid})
    return {"patient": doc}


@router.get("/patients/{patient_id}")
async def get_patient(patient_id: str, user: dict = Depends(get_current_user)):
    p = await db.patients.find_one({"id": patient_id}, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Patient not found")
    return {"patient": p}


@router.get("/patients/{patient_id}/timeline")
async def patient_timeline(patient_id: str, user: dict = Depends(get_current_user)):
    patient = await db.patients.find_one({"id": patient_id}, {"_id": 0})
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    q = {"patient_id": patient_id}
    if user["role"] == ROLE_DOCTOR:
        q["assigned_doctor_id"] = user.get("doctor_id")
    cases = await db.cases.find(q, {"_id": 0}).sort("created_at", -1).to_list(200)

    entries = []
    for c in cases:
        doctor = await db.doctor_profiles.find_one({"id": c["assigned_doctor_id"]}, {"_id": 0})
        payment = await db.payments.find_one({"case_id": c["id"]}, {"_id": 0})
        notes = None
        prescriptions = []
        if user["role"] in (ROLE_OWNER_DOCTOR, ROLE_DOCTOR, ROLE_ADMIN):
            notes = await db.clinical_notes.find_one({"case_id": c["id"]}, {"_id": 0})
        if user["role"] in (ROLE_OWNER_DOCTOR, ROLE_DOCTOR, ROLE_PHARMACY, ROLE_ADMIN):
            prescriptions = await db.prescriptions.find({"case_id": c["id"]}, {"_id": 0}).sort("version_no", -1).to_list(10)
        attachments_count = await db.attachments.count_documents({"case_id": c["id"], "is_deleted": False})
        entries.append({
            "case": c,
            "doctor": doctor,
            "payment": payment if user["role"] != ROLE_DOCTOR or c["assigned_doctor_id"] == user.get("doctor_id") else None,
            "clinical_notes": notes,
            "prescriptions": prescriptions,
            "attachments_count": attachments_count,
        })

    return {"patient": patient, "timeline": entries}


@router.post("/patients/{patient_id}/past-visit")
async def create_past_visit(
    patient_id: str,
    payload: PastVisitIn,
    user: dict = Depends(require_roles(ROLE_OWNER_DOCTOR, ROLE_DOCTOR, ROLE_RECEPTION, ROLE_ADMIN)),
):
    """Record a historical visit (notebook / Google Docs migration).

    Creates a backdated case with status=CLOSED and matching clinical notes,
    prescription (v1) and payment record. visit_date becomes the case's created_at.
    """
    patient = await db.patients.find_one({"id": patient_id})
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    doctor = await db.doctor_profiles.find_one({"id": payload.assigned_doctor_id})
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    # DOCTOR role can only backfill for their own doctor profile
    if user["role"] == ROLE_DOCTOR and payload.assigned_doctor_id != user.get("doctor_id"):
        raise HTTPException(status_code=403, detail="Doctors can only backfill their own visits")

    visit_iso = payload.visit_date.isoformat()
    seq = await next_counter("case_uid")
    case_id = str(uuid.uuid4())
    case_doc = {
        "id": case_id,
        "case_uid": f"CASE-{seq:06d}",
        "patient_id": patient_id,
        "assigned_doctor_id": payload.assigned_doctor_id,
        "complaint_text": payload.complaint_text,
        "status": STATUS_CLOSED,
        "next_followup_at": None,
        "followup_note": None,
        "created_by": user["id"],
        "is_historical": True,
        "created_at": visit_iso,
        "updated_at": visit_iso,
        "consultation_started_at": visit_iso,
        "consultation_completed_at": visit_iso,
        "sent_to_pharmacy_at": visit_iso,
        "ready_for_billing_at": visit_iso,
        "closed_at": visit_iso,
    }
    await db.cases.insert_one(case_doc)
    case_doc.pop("_id", None)

    if any([
        payload.diagnosis_summary, payload.sensitivity_allergies, payload.safety_notes,
        payload.suggestions, payload.additional_info,
    ]):
        await db.clinical_notes.insert_one({
            "case_id": case_id,
            "diagnosis_summary": payload.diagnosis_summary or "",
            "sensitivity_allergies": payload.sensitivity_allergies or "",
            "safety_notes": payload.safety_notes or "",
            "suggestions": payload.suggestions or "",
            "additional_info": payload.additional_info or "",
            "created_by": user["id"],
            "created_at": visit_iso,
            "updated_by": user["id"],
            "updated_at": visit_iso,
        })

    if payload.prescription_items:
        await db.prescriptions.insert_one({
            "id": str(uuid.uuid4()),
            "case_id": case_id,
            "version_no": 1,
            "items": [it.model_dump() for it in payload.prescription_items],
            "notes_for_patient": payload.notes_for_patient or "",
            "notes_internal": "Historical entry — imported.",
            "created_by_user_id": user["id"],
            "edited_by_pharmacy": False,
            "created_at": visit_iso,
        })

    total = payload.consultation_amount + (payload.medicine_amount if payload.medicines_taken else 0)
    if total > 0 or payload.amount_paid > 0:
        balance = max(0, total - payload.amount_paid)
        if payload.amount_paid >= total and total > 0:
            pstatus = "PAID"
        elif payload.amount_paid > 0:
            pstatus = "PARTIAL"
        else:
            pstatus = "UNPAID"
        receipt_no = f"SPH-RC-{await next_counter('receipt_no'):06d}"
        await db.payments.insert_one({
            "case_id": case_id,
            "consultation_amount": payload.consultation_amount,
            "medicine_amount": payload.medicine_amount if payload.medicines_taken else 0,
            "total_amount": total,
            "amount_paid": payload.amount_paid,
            "balance_amount": balance,
            "payment_status": pstatus,
            "payment_mode": payload.payment_mode,
            "medicines_taken": payload.medicines_taken,
            "receipt_no": receipt_no,
            "collected_by": user["id"],
            "is_historical": True,
            "created_at": visit_iso,
            "updated_at": visit_iso,
        })

    await audit(user, "CREATE_HISTORICAL", "Case", case_id, {
        "case_uid": case_doc["case_uid"],
        "patient_id": patient_id,
        "visit_date": visit_iso,
    })
    return {"case": case_doc}
