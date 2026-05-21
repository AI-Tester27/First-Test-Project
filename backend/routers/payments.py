"""Payments endpoint."""
from fastapi import APIRouter, Depends

from core import (
    db, now_utc, next_counter, audit,
    require_roles, load_case_for_user,
    ROLE_PRO, ROLE_OWNER_DOCTOR, ROLE_ADMIN,
    STATUS_CLOSED, STATUS_PARTIALLY_PAID, STATUS_PAYMENT_PENDING,
)
from models import PaymentIn

router = APIRouter()


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
