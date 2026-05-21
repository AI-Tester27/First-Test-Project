"""Seed initial doctor profiles + users."""
import uuid
from core import db, now_utc, hash_pw, verify_pw
from core import (
    ROLE_ADMIN, ROLE_OWNER_DOCTOR, ROLE_DOCTOR,
    ROLE_RECEPTION, ROLE_PHARMACY, ROLE_PRO,
)

SEED_USERS = [
    {"username": "admin1", "name": "System Admin", "role": ROLE_ADMIN, "doctor_id": None, "doctor_name": None},
    {"username": "jyothi", "name": "Dr. Jyothi Vani", "role": ROLE_OWNER_DOCTOR, "doctor_id": "doctor-jyothi", "doctor_name": "Dr. Jyothi Vani"},
    {"username": "hemanth", "name": "Dr. Hemanth", "role": ROLE_DOCTOR, "doctor_id": "doctor-hemanth", "doctor_name": "Dr. Hemanth"},
    {"username": "reception1", "name": "Reception Desk", "role": ROLE_RECEPTION, "doctor_id": None, "doctor_name": None},
    {"username": "pharmacy1", "name": "Pharmacy Counter", "role": ROLE_PHARMACY, "doctor_id": None, "doctor_name": None},
    {"username": "pro1", "name": "Billing Desk", "role": ROLE_PRO, "doctor_id": None, "doctor_name": None},
]


async def seed_all():
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
        elif not verify_pw(default_pw, existing["password_hash"]):
            await db.users.update_one(
                {"username": u["username"]},
                {"$set": {"password_hash": hash_pw(default_pw)}},
            )

    await db.users.create_index("username", unique=True)
    await db.patients.create_index("patient_uid", unique=True)
    await db.patients.create_index("phone")
    await db.cases.create_index("status")
    await db.cases.create_index("assigned_doctor_id")
    await db.audit_logs.create_index("created_at")
    await db.reminders.create_index("scheduled_at")
