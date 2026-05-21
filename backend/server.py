"""Sparsa Homeoclinic — internal clinic management API."""
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import os
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Literal

import bcrypt
import jwt
from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends, status
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field

# ─────────────────────────────────────────────────────────────────────────────
# DB
# ─────────────────────────────────────────────────────────────────────────────
mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALG = "HS256"
ACCESS_TTL = timedelta(hours=12)

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────
ROLE_ADMIN = "ADMIN"
ROLE_OWNER_DOCTOR = "OWNER_DOCTOR"
ROLE_DOCTOR = "DOCTOR"
ROLE_RECEPTION = "RECEPTION"
ROLE_PHARMACY = "PHARMACY"
ROLE_PRO = "PRO"

STATUS_WAITING = "WAITING_FOR_DOCTOR"
STATUS_IN_CONSULT = "IN_CONSULTATION"
STATUS_SENT_PHARMACY = "SENT_TO_PHARMACY"
STATUS_IN_PHARMACY = "IN_PHARMACY"
STATUS_READY_BILLING = "READY_FOR_BILLING"
STATUS_PAYMENT_PENDING = "PAYMENT_PENDING"
STATUS_PARTIALLY_PAID = "PARTIALLY_PAID"
STATUS_CLOSED = "CLOSED"

ALL_STATUSES = [
    STATUS_WAITING, STATUS_IN_CONSULT, STATUS_SENT_PHARMACY, STATUS_IN_PHARMACY,
    STATUS_READY_BILLING, STATUS_PAYMENT_PENDING, STATUS_PARTIALLY_PAID, STATUS_CLOSED,
]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def hash_pw(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def verify_pw(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except Exception:
        return False


def make_token(user_id: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "role": role,
        "exp": now_utc() + ACCESS_TTL,
        "type": "access",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="access_token", value=token, httponly=True, secure=True,
        samesite="none", max_age=int(ACCESS_TTL.total_seconds()), path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie("access_token", path="/")


async def next_counter(key: str) -> int:
    doc = await db.counters.find_one_and_update(
        {"_id": key},
        {"$inc": {"value": 1}},
        upsert=True,
        return_document=True,
    )
    return int(doc["value"]) if doc else 1


def public_user(u: dict) -> dict:
    return {
        "id": u["id"],
        "username": u["username"],
        "name": u["name"],
        "role": u["role"],
        "doctor_id": u.get("doctor_id"),
        "doctor_name": u.get("doctor_name"),
    }


async def audit(actor: dict, action: str, entity_type: str, entity_id: str, metadata: dict = None):
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "actor_user_id": actor.get("id"),
        "actor_username": actor.get("username"),
        "actor_role": actor.get("role"),
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "metadata": metadata or {},
        "created_at": now_utc().isoformat(),
    })


# ─────────────────────────────────────────────────────────────────────────────
# Auth dependencies
# ─────────────────────────────────────────────────────────────────────────────
async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
    if not user or not user.get("active", True):
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


def require_roles(*roles: str):
    async def _dep(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return _dep


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic models
# ─────────────────────────────────────────────────────────────────────────────
class LoginIn(BaseModel):
    username: str
    password: str


class PatientIn(BaseModel):
    first_name: str
    last_name: str
    gender: Literal["MALE", "FEMALE", "OTHER"]
    age: int = Field(ge=0, le=150)
    phone: str
    address: Optional[str] = None
    preferred_language: Literal["EN", "TE"] = "EN"


class CaseCreateIn(BaseModel):
    patient_id: str
    assigned_doctor_id: str
    complaint_text: str


class ClinicalNoteIn(BaseModel):
    diagnosis_summary: Optional[str] = ""
    sensitivity_allergies: Optional[str] = ""
    safety_notes: Optional[str] = ""
    suggestions: Optional[str] = ""
    additional_info: Optional[str] = ""


class PrescriptionItemIn(BaseModel):
    medicine_name: str
    potency: Optional[str] = ""
    dosage: Optional[str] = ""
    frequency: Optional[str] = ""
    duration_days: Optional[int] = None
    instructions: Optional[str] = ""


class PrescriptionIn(BaseModel):
    items: List[PrescriptionItemIn]
    notes_for_patient: Optional[str] = ""
    notes_internal: Optional[str] = ""


class FollowupIn(BaseModel):
    next_followup_at: datetime
    followup_note: Optional[str] = ""


class StatusUpdateIn(BaseModel):
    status: str


class DispenseIn(BaseModel):
    status: Literal["FULL", "PARTIAL", "NOT_DISPENSED"]
    medicine_amount: float = 0
    patient_purchased_medicines: bool = True
    pharmacy_notes: Optional[str] = ""


class PaymentIn(BaseModel):
    consultation_amount: float = 0
    medicines_taken: bool = False
    medicine_amount: float = 0
    amount_paid: float = 0
    payment_mode: Optional[Literal["CASH", "PHONEPE", "CARD", "OTHER"]] = None


class AiActionIn(BaseModel):
    action: Literal["summarize", "advice", "instructions"]


class UserCreateIn(BaseModel):
    username: str
    name: str
    password: str
    role: Literal["ADMIN", "OWNER_DOCTOR", "DOCTOR", "RECEPTION", "PHARMACY", "PRO"]
    doctor_id: Optional[str] = None


class UserUpdateIn(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    active: Optional[bool] = None
    password: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# App + Router
# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(title="Sparsa Homeoclinic API")
api = APIRouter(prefix="/api")


@api.get("/health")
async def health():
    return {"status": "ok", "service": "sparsa-homeoclinic", "time": now_utc().isoformat()}


# ─────────────────────────────────────────────────────────────────────────────
# Auth routes
# ─────────────────────────────────────────────────────────────────────────────
@api.post("/auth/login")
async def login(payload: LoginIn, response: Response):
    user = await db.users.find_one({"username": payload.username.lower().strip()})
    if not user or not verify_pw(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    if not user.get("active", True):
        raise HTTPException(status_code=403, detail="Account disabled")
    token = make_token(user["id"], user["role"])
    set_auth_cookie(response, token)
    await db.users.update_one({"id": user["id"]}, {"$set": {"last_login_at": now_utc().isoformat()}})
    await audit(user, "LOGIN", "User", user["id"])
    return {"user": public_user(user), "access_token": token}


@api.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return {"user": public_user(user)}


@api.post("/auth/logout")
async def logout(response: Response, user: dict = Depends(get_current_user)):
    clear_auth_cookie(response)
    await audit(user, "LOGOUT", "User", user["id"])
    return {"ok": True}


# ─────────────────────────────────────────────────────────────────────────────
# Doctors
# ─────────────────────────────────────────────────────────────────────────────
@api.get("/doctors")
async def list_doctors(user: dict = Depends(get_current_user)):
    docs = await db.doctor_profiles.find({}, {"_id": 0}).to_list(50)
    return {"doctors": docs}


# ─────────────────────────────────────────────────────────────────────────────
# Patients
# ─────────────────────────────────────────────────────────────────────────────
@api.get("/patients")
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


@api.post("/patients")
async def create_patient(payload: PatientIn, user: dict = Depends(require_roles(ROLE_RECEPTION, ROLE_OWNER_DOCTOR, ROLE_ADMIN))):
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


@api.get("/patients/{patient_id}")
async def get_patient(patient_id: str, user: dict = Depends(get_current_user)):
    p = await db.patients.find_one({"id": patient_id}, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Patient not found")
    return {"patient": p}


# ─────────────────────────────────────────────────────────────────────────────
# Cases
# ─────────────────────────────────────────────────────────────────────────────
def _case_filter_for_role(user: dict) -> dict:
    if user["role"] == ROLE_DOCTOR:
        return {"assigned_doctor_id": user["doctor_id"]}
    return {}


async def _enrich_case(c: dict) -> dict:
    patient = await db.patients.find_one({"id": c["patient_id"]}, {"_id": 0})
    doctor = await db.doctor_profiles.find_one({"id": c["assigned_doctor_id"]}, {"_id": 0})
    payment = await db.payments.find_one({"case_id": c["id"]}, {"_id": 0})
    return {
        **c,
        "patient": patient,
        "doctor": doctor,
        "payment_status": payment.get("payment_status") if payment else None,
    }


@api.get("/cases")
async def list_cases(status: Optional[str] = None, user: dict = Depends(get_current_user)):
    q = _case_filter_for_role(user)
    if status:
        if "," in status:
            q["status"] = {"$in": status.split(",")}
        else:
            q["status"] = status
    cases = await db.cases.find(q, {"_id": 0}).sort("created_at", -1).limit(200).to_list(200)
    enriched = [await _enrich_case(c) for c in cases]
    return {"cases": enriched}


@api.post("/cases")
async def create_case(payload: CaseCreateIn, user: dict = Depends(require_roles(ROLE_RECEPTION, ROLE_OWNER_DOCTOR, ROLE_ADMIN))):
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
    return {"case": await _enrich_case(doc)}


async def _load_case_for_user(case_id: str, user: dict) -> dict:
    c = await db.cases.find_one({"id": case_id}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Case not found")
    if user["role"] == ROLE_DOCTOR and c["assigned_doctor_id"] != user.get("doctor_id"):
        raise HTTPException(status_code=403, detail="Not your case")
    return c


@api.get("/cases/{case_id}")
async def get_case(case_id: str, user: dict = Depends(get_current_user)):
    c = await _load_case_for_user(case_id, user)
    patient = await db.patients.find_one({"id": c["patient_id"]}, {"_id": 0})
    doctor = await db.doctor_profiles.find_one({"id": c["assigned_doctor_id"]}, {"_id": 0})

    role = user["role"]
    response: dict = {
        "case": {**c, "patient": patient, "doctor": doctor},
    }

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


@api.patch("/cases/{case_id}/status")
async def update_case_status(case_id: str, payload: StatusUpdateIn, user: dict = Depends(get_current_user)):
    c = await _load_case_for_user(case_id, user)
    if payload.status not in ALL_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    role = user["role"]
    allowed_transitions = {
        ROLE_DOCTOR: {STATUS_IN_CONSULT, STATUS_SENT_PHARMACY},
        ROLE_OWNER_DOCTOR: set(ALL_STATUSES),
        ROLE_ADMIN: set(ALL_STATUSES),
        ROLE_PHARMACY: {STATUS_IN_PHARMACY, STATUS_READY_BILLING},
        ROLE_PRO: {STATUS_PAYMENT_PENDING, STATUS_PARTIALLY_PAID, STATUS_CLOSED},
    }
    if payload.status not in allowed_transitions.get(role, set()):
        raise HTTPException(status_code=403, detail=f"Role {role} cannot set status {payload.status}")

    updates = {"status": payload.status, "updated_at": now_utc().isoformat()}
    if payload.status == STATUS_IN_CONSULT:
        updates["consultation_started_at"] = now_utc().isoformat()
    if payload.status == STATUS_SENT_PHARMACY:
        updates["consultation_completed_at"] = now_utc().isoformat()
        updates["sent_to_pharmacy_at"] = now_utc().isoformat()
    if payload.status == STATUS_READY_BILLING:
        updates["ready_for_billing_at"] = now_utc().isoformat()
    if payload.status == STATUS_CLOSED:
        updates["closed_at"] = now_utc().isoformat()

    await db.cases.update_one({"id": case_id}, {"$set": updates})
    await audit(user, "STATUS_CHANGE", "Case", case_id, {"from": c["status"], "to": payload.status})
    updated = await db.cases.find_one({"id": case_id}, {"_id": 0})
    return {"case": await _enrich_case(updated)}


@api.put("/cases/{case_id}/notes")
async def save_notes(case_id: str, payload: ClinicalNoteIn, user: dict = Depends(require_roles(ROLE_OWNER_DOCTOR, ROLE_DOCTOR, ROLE_ADMIN))):
    await _load_case_for_user(case_id, user)
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


@api.post("/cases/{case_id}/prescription")
async def save_prescription(case_id: str, payload: PrescriptionIn, user: dict = Depends(require_roles(ROLE_OWNER_DOCTOR, ROLE_DOCTOR, ROLE_PHARMACY, ROLE_ADMIN))):
    c = await _load_case_for_user(case_id, user)
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
    await audit(user, "PRESCRIPTION_EDIT" if edited_by_pharmacy else "PRESCRIPTION_CREATE", "Prescription", doc["id"], {"version": next_v})
    return {"prescription": doc}


@api.post("/cases/{case_id}/followup")
async def set_followup(case_id: str, payload: FollowupIn, user: dict = Depends(require_roles(ROLE_OWNER_DOCTOR, ROLE_DOCTOR, ROLE_ADMIN))):
    c = await _load_case_for_user(case_id, user)
    _ = c  # access check
    patient = await db.patients.find_one({"id": c["patient_id"]})
    await db.cases.update_one(
        {"id": case_id},
        {"$set": {"next_followup_at": payload.next_followup_at.isoformat(), "followup_note": payload.followup_note or "", "updated_at": now_utc().isoformat()}},
    )
    # on-screen reminder
    await db.reminders.insert_one({
        "id": str(uuid.uuid4()),
        "case_id": case_id,
        "patient_id": c["patient_id"],
        "patient_name": f"{patient['first_name']} {patient['last_name']}" if patient else "",
        "patient_uid": patient.get("patient_uid") if patient else "",
        "doctor_id": c["assigned_doctor_id"],
        "scheduled_at": payload.next_followup_at.isoformat(),
        "message": payload.followup_note or "Follow-up due",
        "status": "PENDING",
        "created_at": now_utc().isoformat(),
    })
    await audit(user, "FOLLOWUP_SET", "Case", case_id, {"at": payload.next_followup_at.isoformat()})
    return {"ok": True}


@api.post("/cases/{case_id}/dispense")
async def save_dispense(case_id: str, payload: DispenseIn, user: dict = Depends(require_roles(ROLE_PHARMACY, ROLE_OWNER_DOCTOR, ROLE_ADMIN))):
    _ = await _load_case_for_user(case_id, user)
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
    # auto-move to ready_for_billing
    await db.cases.update_one(
        {"id": case_id},
        {"$set": {"status": STATUS_READY_BILLING, "ready_for_billing_at": now_utc().isoformat(), "updated_at": now_utc().isoformat()}},
    )
    await audit(user, "DISPENSE", "Case", case_id, {"status": payload.status, "amount": payload.medicine_amount})
    saved = await db.pharmacy_dispense.find_one({"case_id": case_id}, {"_id": 0})
    return {"pharmacy_dispense": saved}


@api.post("/cases/{case_id}/payment")
async def save_payment(case_id: str, payload: PaymentIn, user: dict = Depends(require_roles(ROLE_PRO, ROLE_OWNER_DOCTOR, ROLE_ADMIN))):
    _ = await _load_case_for_user(case_id, user)
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
    # update case status
    new_status = {"PAID": STATUS_CLOSED, "PARTIAL": STATUS_PARTIALLY_PAID, "UNPAID": STATUS_PAYMENT_PENDING}[pstatus]
    case_updates = {"status": new_status, "updated_at": now_utc().isoformat()}
    if new_status == STATUS_CLOSED:
        case_updates["closed_at"] = now_utc().isoformat()
    await db.cases.update_one({"id": case_id}, {"$set": case_updates})
    await audit(user, "PAYMENT_UPDATE", "Payment", case_id, {"status": pstatus, "total": total, "paid": payload.amount_paid})
    saved = await db.payments.find_one({"case_id": case_id}, {"_id": 0})
    return {"payment": saved, "case_status": new_status}


# ─────────────────────────────────────────────────────────────────────────────
# Reminders
# ─────────────────────────────────────────────────────────────────────────────
@api.get("/reminders")
async def list_reminders(user: dict = Depends(get_current_user)):
    q = {}
    if user["role"] == ROLE_DOCTOR:
        q["doctor_id"] = user.get("doctor_id")
    reminders = await db.reminders.find(q, {"_id": 0}).sort("scheduled_at", 1).limit(50).to_list(50)
    return {"reminders": reminders}


# ─────────────────────────────────────────────────────────────────────────────
# AI Assist (Claude Sonnet 4.5 via Emergent LLM key)
# ─────────────────────────────────────────────────────────────────────────────
@api.post("/cases/{case_id}/ai/{action}")
async def ai_assist(case_id: str, action: str, user: dict = Depends(require_roles(ROLE_OWNER_DOCTOR, ROLE_DOCTOR))):
    if action not in ("summarize", "advice", "instructions"):
        raise HTTPException(status_code=400, detail="Invalid action")
    c = await _load_case_for_user(case_id, user)
    patient = await db.patients.find_one({"id": c["patient_id"]}, {"_id": 0})
    note = await db.clinical_notes.find_one({"case_id": case_id}, {"_id": 0})
    latest = await db.prescriptions.find({"case_id": case_id}).sort("version_no", -1).limit(1).to_list(1)
    latest_p = latest[0] if latest else None
    lang = patient.get("preferred_language", "EN") if patient else "EN"

    if action == "summarize":
        system = ("You are a clinical documentation assistant for a homeopathy clinic. "
                  "Produce a neutral structured draft with sections: Assessment Summary, Questions to Ask, Red Flags. "
                  "Do NOT provide definitive diagnosis. Use 'may/possible' language. Keep concise (under 200 words).")
        user_text = (f"Patient: Age {patient.get('age', '?')}, Gender: {patient.get('gender', '?')}\n"
                     f"Known allergies: {(note or {}).get('sensitivity_allergies') or 'None reported'}\n"
                     f"Complaint: {c['complaint_text']}")
    elif action == "advice":
        lang_note = "Write the patient-facing advice in Telugu script." if lang == "TE" else "Write in clear English."
        system = ("You are writing patient-friendly follow-up advice for a homeopathy patient. "
                  f"Avoid absolute claims. Use simple language. Do not add new medicines. {lang_note} Under 150 words.")
        med_list = ", ".join([(it.get("medicine_name") or "?") for it in (latest_p or {}).get("items", [])]) or "(none yet)"
        user_text = (f"Diagnosis: {(note or {}).get('diagnosis_summary') or c['complaint_text']}\n"
                     f"Medicines: {med_list}\n"
                     f"Follow-up date: {c.get('next_followup_at') or 'Not set'}")
    else:  # instructions
        lang_note = "Write instructions in Telugu." if lang == "TE" else "Write in English."
        system = ("Convert prescription items into a clear, numbered patient instruction list. "
                  f"Do not invent missing details. {lang_note} Be concise.")
        lines = []
        for it in (latest_p or {}).get("items", []):
            lines.append(
                f"- {it.get('medicine_name', '')} {it.get('potency', '')} — {it.get('dosage', '')} "
                f"{it.get('frequency', '')} for {it.get('duration_days') or '?'} days. {it.get('instructions', '')}"
            )
        user_text = "\n".join(lines) or "(no items)"

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = LlmChat(
            api_key=os.environ["EMERGENT_LLM_KEY"],
            session_id=f"ai-{case_id}-{action}-{uuid.uuid4()}",
            system_message=system,
        ).with_model("anthropic", "claude-sonnet-4-5-20250929")
        result = await chat.send_message(UserMessage(text=user_text))
    except Exception as e:
        logging.exception("AI error")
        raise HTTPException(status_code=502, detail=f"AI service error: {e}")

    await audit(user, "AI_USED", "Case", case_id, {"action": action})
    return {"action": action, "result": result}


# ─────────────────────────────────────────────────────────────────────────────
# Admin
# ─────────────────────────────────────────────────────────────────────────────
@api.get("/admin/users")
async def admin_list_users(user: dict = Depends(require_roles(ROLE_ADMIN))):
    users = await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(100)
    return {"users": users}


@api.post("/admin/users")
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


@api.patch("/admin/users/{user_id}")
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


@api.get("/admin/audit-logs")
async def admin_audit_logs(limit: int = 200, user: dict = Depends(require_roles(ROLE_ADMIN))):
    logs = await db.audit_logs.find({}, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    return {"audit_logs": logs}


@api.get("/admin/stats")
async def admin_stats(user: dict = Depends(require_roles(ROLE_ADMIN, ROLE_OWNER_DOCTOR))):
    total_patients = await db.patients.count_documents({})
    total_cases = await db.cases.count_documents({})
    closed_cases = await db.cases.count_documents({"status": STATUS_CLOSED})
    pending_cases = await db.cases.count_documents({"status": {"$nin": [STATUS_CLOSED]}})

    # by status
    by_status = {}
    for s in ALL_STATUSES:
        by_status[s] = await db.cases.count_documents({"status": s})

    # by doctor
    doctors = await db.doctor_profiles.find({}, {"_id": 0}).to_list(20)
    by_doctor = []
    for d in doctors:
        count = await db.cases.count_documents({"assigned_doctor_id": d["id"]})
        by_doctor.append({"doctor": d["display_name"], "cases": count})

    # revenue
    pipeline = [
        {"$match": {"payment_status": "PAID"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount_paid"}}}
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


# ─────────────────────────────────────────────────────────────────────────────
# Seeding
# ─────────────────────────────────────────────────────────────────────────────
SEED_USERS = [
    {"username": "admin1", "name": "System Admin", "role": ROLE_ADMIN, "doctor_id": None, "doctor_name": None},
    {"username": "jyothi", "name": "Dr. Jyothi Vani", "role": ROLE_OWNER_DOCTOR, "doctor_id": "doctor-jyothi", "doctor_name": "Dr. Jyothi Vani"},
    {"username": "hemanth", "name": "Dr. Hemanth", "role": ROLE_DOCTOR, "doctor_id": "doctor-hemanth", "doctor_name": "Dr. Hemanth"},
    {"username": "reception1", "name": "Reception Desk", "role": ROLE_RECEPTION, "doctor_id": None, "doctor_name": None},
    {"username": "pharmacy1", "name": "Pharmacy Counter", "role": ROLE_PHARMACY, "doctor_id": None, "doctor_name": None},
    {"username": "pro1", "name": "Billing Desk", "role": ROLE_PRO, "doctor_id": None, "doctor_name": None},
]


async def seed():
    # doctor profiles
    doctors = [
        {"id": "doctor-jyothi", "display_name": "Dr. Jyothi Vani", "is_owner": True},
        {"id": "doctor-hemanth", "display_name": "Dr. Hemanth", "is_owner": False},
    ]
    for d in doctors:
        await db.doctor_profiles.update_one({"id": d["id"]}, {"$setOnInsert": d}, upsert=True)

    default_pw = "Password@123"
    for u in SEED_USERS:
        existing = await db.users.find_one({"username": u["username"]})
        if existing is None:
            await db.users.insert_one({
                "id": str(uuid.uuid4()),
                **u,
                "active": True,
                "password_hash": hash_pw(default_pw),
                "created_at": now_utc().isoformat(),
            })
        else:
            # ensure password remains seeded (idempotent for testing)
            if not verify_pw(default_pw, existing["password_hash"]):
                await db.users.update_one({"username": u["username"]}, {"$set": {"password_hash": hash_pw(default_pw)}})

    await db.users.create_index("username", unique=True)
    await db.patients.create_index("patient_uid", unique=True)
    await db.patients.create_index("phone")
    await db.cases.create_index("status")
    await db.cases.create_index("assigned_doctor_id")
    await db.audit_logs.create_index("created_at")
    await db.reminders.create_index("scheduled_at")


@app.on_event("startup")
async def on_startup():
    await seed()


# Mount router
app.include_router(api)

# CORS — allow credentials from frontend origin
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origin_regex=".*",
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


@app.on_event("shutdown")
async def shutdown_db():
    client.close()
