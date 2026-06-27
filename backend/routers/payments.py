"""Payments endpoint."""
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timedelta, timezone

from core import (
    db, now_utc, next_counter, audit,
    require_roles, load_case_for_user,
    ROLE_PRO, ROLE_OWNER_DOCTOR, ROLE_ADMIN,
    STATUS_CLOSED, STATUS_PARTIALLY_PAID, STATUS_PAYMENT_PENDING,
)
from models import PaymentIn

router = APIRouter()


@router.get("/pro/financial-search")
async def financial_search(
    q: str = "",
    user: dict = Depends(require_roles(ROLE_PRO, ROLE_OWNER_DOCTOR, ROLE_ADMIN)),
):
    """Search patients by name/UID/phone and return their billing summary + payments."""
    if not q or len(q.strip()) < 2:
        raise HTTPException(status_code=400, detail="Provide a search term (≥2 chars)")
    q = q.strip()
    patient_query = {"$or": [
        {"first_name": {"$regex": q, "$options": "i"}},
        {"last_name": {"$regex": q, "$options": "i"}},
        {"phone": {"$regex": q, "$options": "i"}},
        {"patient_uid": {"$regex": q, "$options": "i"}},
    ]}
    patients = await db.patients.find(patient_query, {"_id": 0}).limit(20).to_list(20)
    results = []
    for p in patients:
        cases = await db.cases.find({"patient_id": p["id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)
        case_ids = [c["id"] for c in cases]
        payments = await db.payments.find({"case_id": {"$in": case_ids}}, {"_id": 0}).to_list(200)
        pay_by_case = {pay["case_id"]: pay for pay in payments}
        total_billed = sum(pay.get("total_amount", 0) for pay in payments)
        total_paid = sum(pay.get("amount_paid", 0) for pay in payments)
        outstanding = sum(pay.get("balance_amount", 0) for pay in payments)
        visits = []
        for c in cases[:30]:
            pay = pay_by_case.get(c["id"]) or {}
            visits.append({
                "case_id": c["id"],
                "case_uid": c.get("case_uid"),
                "created_at": c.get("created_at"),
                "status": c.get("status"),
                "complaint": c.get("complaint_text"),
                "total_amount": pay.get("total_amount", 0),
                "amount_paid": pay.get("amount_paid", 0),
                "balance_amount": pay.get("balance_amount", 0),
                "payment_status": pay.get("payment_status") or "UNBILLED",
                "payment_mode": pay.get("payment_mode"),
                "receipt_no": pay.get("receipt_no"),
            })
        results.append({
            "patient": {k: p.get(k) for k in ("id", "patient_uid", "first_name", "last_name", "phone", "age", "gender")},
            "total_billed": total_billed,
            "total_paid": total_paid,
            "outstanding": outstanding,
            "visits_count": len(cases),
            "visits": visits,
        })
    return {"results": results, "count": len(results)}


@router.post("/cases/{case_id}/payment")
async def save_payment(
    case_id: str,
    payload: PaymentIn,
    user: dict = Depends(require_roles(ROLE_PRO, ROLE_OWNER_DOCTOR, ROLE_ADMIN)),
):
    await load_case_for_user(case_id, user)
    medicine_amount = payload.medicine_amount if payload.medicines_taken else 0
    total = payload.consultation_amount + medicine_amount
    balance = max(0, total - payload.amount_paid)
    if payload.amount_paid >= total and total > 0:
        pstatus = "PAID"
    elif payload.amount_paid > 0:
        pstatus = "PARTIAL"
    else:
        pstatus = "UNPAID"

    existing = await db.payments.find_one({"case_id": case_id})
    receipt_no = existing["receipt_no"] if existing else f"SPH-RC-{await next_counter('receipt_no'):06d}"

    doc = {
        "case_id": case_id,
        "consultation_amount": payload.consultation_amount,
        "medicine_amount": medicine_amount,
        "total_amount": total,
        "amount_paid": payload.amount_paid,
        "balance_amount": balance,
        "payment_status": pstatus,
        "payment_mode": payload.payment_mode,
        "medicines_taken": payload.medicines_taken,
        "receipt_no": receipt_no,
        "collected_by": user["id"],
        "updated_at": now_utc().isoformat(),
    }
    await db.payments.update_one(
        {"case_id": case_id},
        {"$set": doc, "$setOnInsert": {"created_at": now_utc().isoformat()}},
        upsert=True,
    )
    new_status = {"PAID": STATUS_CLOSED, "PARTIAL": STATUS_PARTIALLY_PAID, "UNPAID": STATUS_PAYMENT_PENDING}[pstatus]
    case_updates = {"status": new_status, "updated_at": now_utc().isoformat()}
    if new_status == STATUS_CLOSED:
        case_updates["closed_at"] = now_utc().isoformat()
    await db.cases.update_one({"id": case_id}, {"$set": case_updates})
    await audit(user, "PAYMENT_UPDATE", "Payment", case_id, {"status": pstatus, "total": total, "paid": payload.amount_paid})
    saved = await db.payments.find_one({"case_id": case_id}, {"_id": 0})
    return {"payment": saved, "case_status": new_status}
