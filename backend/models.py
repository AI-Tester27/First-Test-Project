"""All Pydantic request/response models."""
from datetime import datetime, date
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class LoginIn(BaseModel):
    username: str
    password: str


PATIENT_SOURCES = Literal[
    "TELEVISION", "NEWSPAPER", "MEDICAL_CAMPS", "SIGN_BOARDS", "BANNERS",
    "NEARBY_RESIDENCE", "SOCIAL_MEDIA", "YOUTUBE", "FACEBOOK", "INSTAGRAM",
    "ONLINE_SEARCH", "REFERRAL", "OTHERS",
]

VISIT_TYPES = Literal["WALK_IN", "APPOINTMENT"]
MARITAL_STATUSES = Literal["SINGLE", "MARRIED", "DIVORCED", "WIDOWED", "OTHER"]


class PatientIn(BaseModel):
    first_name: str
    last_name: str = ""
    gender: Literal["MALE", "FEMALE", "OTHER"]
    age: int = Field(ge=0, le=150)
    phone: str
    address: Optional[str] = None
    preferred_language: Literal["EN", "TE"] = "EN"
    # FIR additions (all optional for backward compat)
    marital_status: Optional[MARITAL_STATUSES] = None
    height_cm: Optional[float] = Field(default=None, ge=20, le=300)
    weight_kg: Optional[float] = Field(default=None, ge=1, le=500)
    consulting_doctor_id: Optional[str] = None
    sources: List[PATIENT_SOURCES] = []
    referral_name: Optional[str] = None
    chief_complaint: Optional[str] = None
    visit_type: Optional[VISIT_TYPES] = None


class FIRPatientIn(PatientIn):
    """Full First Information Report — creates patient AND first case in one go.
    Requires consulting_doctor_id + chief_complaint + visit_type."""
    consulting_doctor_id: str
    chief_complaint: str
    visit_type: VISIT_TYPES


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
    next_followup_date: date  # date-only — no time component (per user request, avoids auto-completion confusion)
    followup_note: Optional[str] = ""
    notify_pharmacy: bool = False


class StatusUpdateIn(BaseModel):
    status: str
    bypass_reason: Optional[str] = None  # required only when doctor sends directly to pharmacy (skipping PRO)


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
    password: str = Field(min_length=8, max_length=128)
    role: Literal["ADMIN", "OWNER_DOCTOR", "DOCTOR", "RECEPTION", "PHARMACY", "PRO"]
    doctor_id: Optional[str] = None


class UserUpdateIn(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    active: Optional[bool] = None
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)


class PatientUpdateIn(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    gender: Optional[Literal["MALE", "FEMALE", "OTHER"]] = None
    age: Optional[int] = Field(default=None, ge=0, le=150)
    phone: Optional[str] = None
    address: Optional[str] = None
    preferred_language: Optional[Literal["EN", "TE"]] = None
    marital_status: Optional[MARITAL_STATUSES] = None
    height_cm: Optional[float] = Field(default=None, ge=20, le=300)
    weight_kg: Optional[float] = Field(default=None, ge=1, le=500)
    consulting_doctor_id: Optional[str] = None
    sources: Optional[List[PATIENT_SOURCES]] = None
    referral_name: Optional[str] = None


class ReminderCreateIn(BaseModel):
    patient_id: str
    case_id: Optional[str] = None
    scheduled_at: datetime
    message: str
    audience: List[Literal["DOCTOR", "PHARMACY"]] = ["DOCTOR"]
    notify_pharmacy: bool = False


class ReminderUpdateIn(BaseModel):
    status: Optional[Literal["PENDING", "COMPLETED", "FAILED"]] = None
    snooze_until: Optional[datetime] = None
    message: Optional[str] = None
    notes: Optional[str] = None


class AiSettingsIn(BaseModel):
    provider: Literal["emergent", "openai", "anthropic"] = "emergent"
    api_key: Optional[str] = None
    model: Optional[str] = None


class PastVisitIn(BaseModel):
    """Historical visit entry — creates a backdated CLOSED case."""
    visit_date: datetime
    assigned_doctor_id: str
    complaint_text: str
    diagnosis_summary: Optional[str] = ""
    sensitivity_allergies: Optional[str] = ""
    safety_notes: Optional[str] = ""
    suggestions: Optional[str] = ""
    additional_info: Optional[str] = ""
    prescription_items: List[PrescriptionItemIn] = []
    notes_for_patient: Optional[str] = ""
    consultation_amount: float = 0
    medicine_amount: float = 0
    medicines_taken: bool = False
    amount_paid: float = 0
    payment_mode: Optional[Literal["CASH", "PHONEPE", "CARD", "OTHER"]] = None


class ParseNotesIn(BaseModel):
    """Paste from Google Docs / paper transcripts."""
    text: str
    hint_doctor_id: Optional[str] = None


class MessagingSettingsIn(BaseModel):
    """Admin-managed runtime Twilio + WhatsApp credentials."""
    WHATSAPP_PHONE_NUMBER_ID: Optional[str] = None
    WHATSAPP_ACCESS_TOKEN: Optional[str] = None
    WHATSAPP_API_VERSION: Optional[str] = None
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_FROM: Optional[str] = None
