"""Shared infrastructure: db, security, helpers, constants, audit."""
import os
import uuid
import bcrypt
import jwt
from datetime import datetime, timezone, timedelta

from fastapi import HTTPException, Request, Response, Depends
from motor.motor_asyncio import AsyncIOMotorClient

# ─── DB ───
mongo_url = os.environ["MONGO_URL"]
mongo_client = AsyncIOMotorClient(mongo_url)
db = mongo_client[os.environ["DB_NAME"]]

# ─── JWT ───
JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALG = "HS256"
ACCESS_TTL = timedelta(hours=12)

# ─── Roles & statuses ───
ROLE_ADMIN = "ADMIN"
ROLE_OWNER_DOCTOR = "OWNER_DOCTOR"
ROLE_DOCTOR = "DOCTOR"
ROLE_RECEPTION = "RECEPTION"
ROLE_PHARMACY = "PHARMACY"
ROLE_PRO = "PRO"

STATUS_WAITING = "WAITING_FOR_DOCTOR"
STATUS_IN_CONSULT = "IN_CONSULTATION"
STATUS_AWAITING_PRO = "AWAITING_PRO_REVIEW"
STATUS_SENT_PHARMACY = "SENT_TO_PHARMACY"
STATUS_IN_PHARMACY = "IN_PHARMACY"
STATUS_READY_BILLING = "READY_FOR_BILLING"
STATUS_PAYMENT_PENDING = "PAYMENT_PENDING"
STATUS_PARTIALLY_PAID = "PARTIALLY_PAID"
STATUS_CLOSED = "CLOSED"

ALL_STATUSES = {
    STATUS_WAITING, STATUS_IN_CONSULT, STATUS_AWAITING_PRO, STATUS_SENT_PHARMACY,
    STATUS_IN_PHARMACY, STATUS_READY_BILLING, STATUS_PAYMENT_PENDING, STATUS_PARTIALLY_PAID,
    STATUS_CLOSED,
}


# ─── Helpers ───
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
        key="access_token", value=token, httponly=True, secure=False,
        samesite="lax", max_age=int(ACCESS_TTL.total_seconds()), path="/",
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


async def audit(actor: dict, action: str, entity_type: str, entity_id: str, metadata: dict | None = None):
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


# ─── Auth deps ───
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


# ─── Case access helpers ───
async def load_case_for_user(case_id: str, user: dict) -> dict:
    c = await db.cases.find_one({"id": case_id}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Case not found")
    if user["role"] == ROLE_DOCTOR and c["assigned_doctor_id"] != user.get("doctor_id"):
        raise HTTPException(status_code=403, detail="Not your case")
    return c


def case_filter_for_role(user: dict) -> dict:
    if user["role"] == ROLE_DOCTOR:
        return {"assigned_doctor_id": user["doctor_id"]}
    return {}


async def enrich_case(c: dict) -> dict:
    patient = await db.patients.find_one({"id": c["patient_id"]}, {"_id": 0})
    doctor = await db.doctor_profiles.find_one({"id": c["assigned_doctor_id"]}, {"_id": 0})
    payment = await db.payments.find_one({"case_id": c["id"]}, {"_id": 0})
    return {
        **c,
        "patient": patient,
        "doctor": doctor,
        "payment_status": payment.get("payment_status") if payment else None,
    }
