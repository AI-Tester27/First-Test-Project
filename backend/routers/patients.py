"""Doctors list + Patients CRUD + visit timeline."""
import uuid
from fastapi import APIRouter, Depends, HTTPException

from core import (
    db, now_utc, next_counter, audit,
    get_current_user, require_roles, case_filter_for_role,
    ROLE_RECEPTION, ROLE_OWNER_DOCTOR, ROLE_ADMIN, ROLE_DOCTOR, ROLE_PHARMACY,
)
from models import PatientIn

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
