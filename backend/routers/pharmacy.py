"""Pharmacy dispense endpoint."""
from fastapi import APIRouter, Depends

from core import (
    db, now_utc, audit, require_roles, load_case_for_user,
    ROLE_PHARMACY, ROLE_OWNER_DOCTOR, ROLE_ADMIN,
    STATUS_READY_BILLING,
)
from models import DispenseIn

router = APIRouter()


@router.post("/cases/{case_id}/dispense")
async def save_dispense(
    case_id: str,
    payload: DispenseIn,
    user: dict = Depends(require_roles(ROLE_PHARMACY, ROLE_OWNER_DOCTOR, ROLE_ADMIN)),
):
    await load_case_for_user(case_id, user)
    doc = {
        "case_id": case_id,
        **payload.model_dump(),
        "handled_by": user["id"],
        "updated_at": now_utc().isoformat(),
    }
    await db.pharmacy_dispense.update_one(
        {"case_id": case_id},
        {"$set": doc, "$setOnInsert": {"created_at": now_utc().isoformat()}},
        upsert=True,
    )
    await db.cases.update_one(
        {"id": case_id},
        {"$set": {
            "status": STATUS_READY_BILLING,
            "ready_for_billing_at": now_utc().isoformat(),
            "updated_at": now_utc().isoformat(),
        }},
    )
    await audit(user, "DISPENSE", "Case", case_id, {"status": payload.status, "amount": payload.medicine_amount})
    saved = await db.pharmacy_dispense.find_one({"case_id": case_id}, {"_id": 0})
    return {"pharmacy_dispense": saved}
