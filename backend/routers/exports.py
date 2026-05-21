"""CSV exports for admin / owner_doctor."""
import io
import csv
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from core import (
    db, audit, require_roles,
    ROLE_ADMIN, ROLE_OWNER_DOCTOR,
)

router = APIRouter()


def _csv_response(rows: list[dict], fieldnames: list[str], filename: str) -> StreamingResponse:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/admin/export/patients.csv")
async def export_patients(user: dict = Depends(require_roles(ROLE_ADMIN, ROLE_OWNER_DOCTOR))):
    rows = await db.patients.find({}, {"_id": 0}).to_list(100000)
    await audit(user, "EXPORT", "Patient", "csv", {"rows": len(rows)})
    return _csv_response(
        rows,
        ["patient_uid", "first_name", "last_name", "gender", "age", "phone", "address", "preferred_language", "created_at"],
        "sparsa-patients.csv",
    )


@router.get("/admin/export/cases.csv")
async def export_cases(user: dict = Depends(require_roles(ROLE_ADMIN, ROLE_OWNER_DOCTOR))):
    cases = await db.cases.find({}, {"_id": 0}).to_list(100000)
    rows = []
    for c in cases:
        patient = await db.patients.find_one(
            {"id": c["patient_id"]},
            {"_id": 0, "patient_uid": 1, "first_name": 1, "last_name": 1, "phone": 1},
        )
        doctor = await db.doctor_profiles.find_one(
            {"id": c["assigned_doctor_id"]}, {"_id": 0, "display_name": 1}
        )
        rows.append({
            **c,
            "patient_uid": (patient or {}).get("patient_uid"),
            "patient_name": f"{(patient or {}).get('first_name', '')} {(patient or {}).get('last_name', '')}".strip(),
            "patient_phone": (patient or {}).get("phone"),
            "doctor": (doctor or {}).get("display_name"),
        })
    await audit(user, "EXPORT", "Case", "csv", {"rows": len(rows)})
    return _csv_response(
        rows,
        ["case_uid", "patient_uid", "patient_name", "patient_phone", "doctor", "complaint_text", "status",
         "next_followup_at", "created_at", "consultation_started_at", "consultation_completed_at",
         "sent_to_pharmacy_at", "ready_for_billing_at", "closed_at"],
        "sparsa-cases.csv",
    )


@router.get("/admin/export/payments.csv")
async def export_payments(user: dict = Depends(require_roles(ROLE_ADMIN, ROLE_OWNER_DOCTOR))):
    pays = await db.payments.find({}, {"_id": 0}).to_list(100000)
    rows = []
    for p in pays:
        c = await db.cases.find_one(
            {"id": p["case_id"]},
            {"_id": 0, "case_uid": 1, "patient_id": 1, "assigned_doctor_id": 1},
        )
        patient = await db.patients.find_one(
            {"id": (c or {}).get("patient_id")},
            {"_id": 0, "patient_uid": 1, "first_name": 1, "last_name": 1},
        )
        doctor = await db.doctor_profiles.find_one(
            {"id": (c or {}).get("assigned_doctor_id")}, {"_id": 0, "display_name": 1}
        )
        rows.append({
            **p,
            "case_uid": (c or {}).get("case_uid"),
            "patient_uid": (patient or {}).get("patient_uid"),
            "patient_name": f"{(patient or {}).get('first_name', '')} {(patient or {}).get('last_name', '')}".strip(),
            "doctor": (doctor or {}).get("display_name"),
        })
    await audit(user, "EXPORT", "Payment", "csv", {"rows": len(rows)})
    return _csv_response(
        rows,
        ["receipt_no", "case_uid", "patient_uid", "patient_name", "doctor", "consultation_amount",
         "medicine_amount", "total_amount", "amount_paid", "balance_amount", "payment_status",
         "payment_mode", "medicines_taken", "created_at", "updated_at"],
        "sparsa-payments.csv",
    )


@router.get("/admin/export/prescriptions.csv")
async def export_prescriptions(user: dict = Depends(require_roles(ROLE_ADMIN, ROLE_OWNER_DOCTOR))):
    rx = await db.prescriptions.find({}, {"_id": 0}).to_list(100000)
    rows = []
    for p in rx:
        c = await db.cases.find_one({"id": p["case_id"]}, {"_id": 0, "case_uid": 1, "patient_id": 1})
        patient = await db.patients.find_one({"id": (c or {}).get("patient_id")}, {"_id": 0, "patient_uid": 1})
        for item in (p.get("items") or []):
            rows.append({
                "case_uid": (c or {}).get("case_uid"),
                "patient_uid": (patient or {}).get("patient_uid"),
                "version_no": p.get("version_no"),
                "edited_by_pharmacy": p.get("edited_by_pharmacy", False),
                "created_at": p.get("created_at"),
                **item,
            })
    await audit(user, "EXPORT", "Prescription", "csv", {"rows": len(rows)})
    return _csv_response(
        rows,
        ["case_uid", "patient_uid", "version_no", "edited_by_pharmacy", "medicine_name",
         "potency", "dosage", "frequency", "duration_days", "instructions", "created_at"],
        "sparsa-prescriptions.csv",
    )


@router.get("/admin/export/audit.csv")
async def export_audit(user: dict = Depends(require_roles(ROLE_ADMIN))):
    rows = await db.audit_logs.find({}, {"_id": 0}).sort("created_at", -1).limit(50000).to_list(50000)
    flat = [{**r, "metadata": str(r.get("metadata") or "")} for r in rows]
    await audit(user, "EXPORT", "AuditLog", "csv", {"rows": len(flat)})
    return _csv_response(
        flat,
        ["created_at", "actor_username", "actor_role", "action", "entity_type", "entity_id", "metadata"],
        "sparsa-audit.csv",
    )
