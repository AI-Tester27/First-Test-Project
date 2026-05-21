"""All Pydantic request/response models."""
from datetime import datetime
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


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
