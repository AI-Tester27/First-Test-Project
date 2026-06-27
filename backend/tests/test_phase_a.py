"""Phase A backend tests:
1) POST /api/patients/fir — create patient + first case in one go (RBAC, validation, BMI auto)
2) POST /api/patients legacy still works (backward compat, BMI null when no h/w)
3) PATCH /api/patients/{id} — BMI auto-recompute when height_cm or weight_kg changes
4) POST /api/cases/{id}/followup — date-only field, anchored 09:00 IST UTC; reminders doc shape
5) Reminders scheduler never auto-COMPLETES (verifies status moves to FAILED/SENT only)
"""
import os
import time
import uuid
import pytest
import requests
from datetime import datetime, timezone, timedelta

def _load_backend_url():
    v = os.environ.get("REACT_APP_BACKEND_URL")
    if v:
        return v.rstrip("/")
    # fallback: read from frontend/.env
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    return line.split("=", 1)[1].strip().rstrip("/")
    except Exception:
        pass
    raise RuntimeError("REACT_APP_BACKEND_URL not set")

BASE_URL = _load_backend_url()
API = f"{BASE_URL}/api"

# ── Auth helpers ──
def _login(username: str, password: str = "Password@123") -> requests.Session:
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"username": username, "password": password}, timeout=15)
    assert r.status_code == 200, f"login {username} failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def reception(): return _login("reception1")

@pytest.fixture(scope="module")
def doctor(): return _login("hemanth")

@pytest.fixture(scope="module")
def pharmacy(): return _login("pharmacy1")

@pytest.fixture(scope="module")
def pro(): return _login("pro1")

@pytest.fixture(scope="module")
def admin(): return _login("admin1")

@pytest.fixture(scope="module")
def jyothi(): return _login("jyothi")


# ── Tests for POST /api/patients/fir ──
class TestFIREndpoint:
    def test_fir_full_payload_success(self, reception):
        payload = {
            "first_name": "TEST_FIR_Alpha",
            "last_name": "Patient",
            "gender": "FEMALE",
            "age": 32,
            "phone": "9876500001",
            "address": "1-2-3 Hyderabad",
            "marital_status": "MARRIED",
            "height_cm": 170,
            "weight_kg": 80,
            "consulting_doctor_id": "doctor-hemanth",
            "sources": ["SOCIAL_MEDIA", "REFERRAL"],
            "referral_name": "Dr Friend",
            "chief_complaint": "Severe migraine",
            "visit_type": "WALK_IN",
        }
        r = reception.post(f"{API}/patients/fir", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "patient" in data and "case" in data
        p = data["patient"]
        c = data["case"]
        # patient
        assert p["bmi"] == 27.7, f"expected bmi=27.7 got {p['bmi']}"
        assert p["marital_status"] == "MARRIED"
        assert p["consulting_doctor_id"] == "doctor-hemanth"
        assert "SOCIAL_MEDIA" in p["sources"] and "REFERRAL" in p["sources"]
        assert p["patient_uid"].startswith("SPARSA-")
        # case
        assert c["status"] == "WAITING_FOR_DOCTOR"
        assert c["complaint_text"] == "Severe migraine"
        assert c["visit_type"] == "WALK_IN"
        assert c["assigned_doctor_id"] == "doctor-hemanth"
        assert c["patient_id"] == p["id"]
        # stash for later
        TestFIREndpoint._patient_id = p["id"]
        TestFIREndpoint._case_id = c["id"]

    def test_fir_missing_consulting_doctor_id_422(self, reception):
        payload = {
            "first_name": "TEST_FIR_NoDoc", "gender": "MALE", "age": 25, "phone": "9876500002",
            "chief_complaint": "x", "visit_type": "WALK_IN",
        }
        r = reception.post(f"{API}/patients/fir", json=payload, timeout=10)
        assert r.status_code == 422, f"expected 422, got {r.status_code} {r.text}"

    def test_fir_nonexistent_doctor_404(self, reception):
        payload = {
            "first_name": "TEST_FIR_BadDoc", "gender": "MALE", "age": 25, "phone": "9876500003",
            "consulting_doctor_id": "doctor-doesnotexist",
            "chief_complaint": "x", "visit_type": "WALK_IN",
        }
        r = reception.post(f"{API}/patients/fir", json=payload, timeout=10)
        assert r.status_code == 404, r.text

    def test_fir_pharmacy_403(self, pharmacy):
        payload = {
            "first_name": "TEST_FIR_Phx", "gender": "MALE", "age": 25, "phone": "9876500004",
            "consulting_doctor_id": "doctor-hemanth",
            "chief_complaint": "x", "visit_type": "WALK_IN",
        }
        r = pharmacy.post(f"{API}/patients/fir", json=payload, timeout=10)
        assert r.status_code == 403, r.text

    def test_fir_doctor_403(self, doctor):
        payload = {
            "first_name": "TEST_FIR_Doc", "gender": "MALE", "age": 25, "phone": "9876500005",
            "consulting_doctor_id": "doctor-hemanth",
            "chief_complaint": "x", "visit_type": "WALK_IN",
        }
        r = doctor.post(f"{API}/patients/fir", json=payload, timeout=10)
        assert r.status_code == 403, r.text

    def test_fir_pro_403(self, pro):
        payload = {
            "first_name": "TEST_FIR_Pro", "gender": "MALE", "age": 25, "phone": "9876500006",
            "consulting_doctor_id": "doctor-hemanth",
            "chief_complaint": "x", "visit_type": "WALK_IN",
        }
        r = pro.post(f"{API}/patients/fir", json=payload, timeout=10)
        assert r.status_code == 403, r.text


# ── Legacy POST /api/patients (backward compat) ──
class TestLegacyCreatePatient:
    def test_minimal_payload(self, reception):
        payload = {
            "first_name": "TEST_Legacy",
            "gender": "MALE", "age": 40, "phone": "9876500010",
        }
        r = reception.post(f"{API}/patients", json=payload, timeout=10)
        assert r.status_code == 200, r.text
        p = r.json()["patient"]
        assert p["bmi"] is None
        assert p["patient_uid"].startswith("SPARSA-")
        TestLegacyCreatePatient._pid = p["id"]


# ── PATCH /api/patients/{id} BMI recompute ──
class TestPatchBMI:
    @pytest.fixture(scope="class")
    def pid(self, reception):
        # Create a patient first
        r = reception.post(f"{API}/patients", json={
            "first_name": "TEST_PatchBMI", "gender": "MALE", "age": 30, "phone": "9876500020",
            "height_cm": 170, "weight_kg": 70,
        }, timeout=10)
        assert r.status_code == 200, r.text
        p = r.json()["patient"]
        assert p["bmi"] == 24.2
        return p["id"]

    def test_patch_weight_recomputes(self, reception, pid):
        r = reception.patch(f"{API}/patients/{pid}", json={"weight_kg": 80}, timeout=10)
        assert r.status_code == 200, r.text
        assert r.json()["patient"]["bmi"] == 27.7

    def test_patch_height_recomputes(self, reception, pid):
        # weight is now 80, change height to 180 -> 80/(1.8^2)=24.7
        r = reception.patch(f"{API}/patients/{pid}", json={"height_cm": 180}, timeout=10)
        assert r.status_code == 200, r.text
        assert r.json()["patient"]["bmi"] == 24.7


# ── POST /api/cases/{id}/followup (date-only) ──
class TestFollowupDateOnly:
    @pytest.fixture(scope="class")
    def case_id_and_patient(self, reception):
        # Create patient via FIR for proper assignment
        r = reception.post(f"{API}/patients/fir", json={
            "first_name": "TEST_Followup", "last_name": "Case",
            "gender": "FEMALE", "age": 28, "phone": "9876500030",
            "consulting_doctor_id": "doctor-hemanth",
            "chief_complaint": "Cough", "visit_type": "WALK_IN",
        }, timeout=10)
        assert r.status_code == 200, r.text
        return r.json()["case"]["id"], r.json()["patient"]["id"], r.json()["patient"]["phone"]

    def test_followup_set_and_response(self, doctor, case_id_and_patient):
        case_id, _, _ = case_id_and_patient
        r = doctor.post(f"{API}/cases/{case_id}/followup", json={
            "next_followup_date": "2026-07-15",
            "followup_note": "Review labs",
            "notify_pharmacy": False,
        }, timeout=10)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body == {"ok": True, "scheduled_date": "2026-07-15"}

    def test_followup_persistence_case_doc(self, doctor, case_id_and_patient):
        case_id, _, _ = case_id_and_patient
        r = doctor.get(f"{API}/cases/{case_id}", timeout=10)
        assert r.status_code == 200, r.text
        c = r.json()["case"]
        assert c["next_followup_date"] == "2026-07-15"
        # 09:00 IST = 03:30 UTC
        assert c["next_followup_at"].startswith("2026-07-15T03:30:00")

    def test_followup_creates_reminder(self, admin, case_id_and_patient):
        case_id, _, phone = case_id_and_patient
        r = admin.get(f"{API}/reminders", timeout=10)
        assert r.status_code == 200, r.text
        rems = r.json()["reminders"]
        match = [x for x in rems if x.get("case_id") == case_id]
        assert match, "no reminder found for the case"
        rem = match[0]
        assert rem["scheduled_date"] == "2026-07-15"
        assert rem["scheduled_at"].startswith("2026-07-15T03:30:00")
        assert rem["patient_phone"] == phone
        assert rem["status"] == "PENDING"

    def test_followup_invalid_date_format_422(self, doctor, case_id_and_patient):
        case_id, _, _ = case_id_and_patient
        r = doctor.post(f"{API}/cases/{case_id}/followup", json={
            "next_followup_date": "not-a-date", "followup_note": "x",
        }, timeout=10)
        assert r.status_code == 422, r.text

    def test_followup_missing_date_422(self, doctor, case_id_and_patient):
        case_id, _, _ = case_id_and_patient
        r = doctor.post(f"{API}/cases/{case_id}/followup", json={"followup_note": "x"}, timeout=10)
        assert r.status_code == 422, r.text


# ── Scheduler: never auto-COMPLETE ──
class TestSchedulerNoAutoComplete:
    def test_scheduler_marks_failed_not_completed(self, admin, reception):
        """Insert a PENDING reminder with past scheduled_at via /api/reminders create endpoint,
        then wait ~70s and verify status flips to FAILED/SENT but never COMPLETED."""
        # Create a patient/case so the reminder has valid links
        r = reception.post(f"{API}/patients/fir", json={
            "first_name": "TEST_Sched", "gender": "MALE", "age": 22, "phone": "9876500040",
            "consulting_doctor_id": "doctor-hemanth",
            "chief_complaint": "x", "visit_type": "WALK_IN",
        }, timeout=10)
        assert r.status_code == 200
        case_id = r.json()["case"]["id"]
        patient_id = r.json()["patient"]["id"]

        past = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        r = admin.post(f"{API}/reminders", json={
            "patient_id": patient_id, "case_id": case_id,
            "scheduled_at": past, "message": "TEST scheduler check",
            "audience": ["DOCTOR"], "notify_pharmacy": False,
        }, timeout=10)
        assert r.status_code == 200, r.text
        rid = r.json()["reminder"]["id"]

        # Wait for scheduler tick (interval ~60s)
        deadline = time.time() + 90
        final_status = None
        while time.time() < deadline:
            time.sleep(10)
            lr = admin.get(f"{API}/reminders", timeout=10)
            assert lr.status_code == 200
            match = [x for x in lr.json()["reminders"] if x["id"] == rid]
            if match and match[0]["status"] != "PENDING":
                final_status = match[0]["status"]
                break

        assert final_status is not None, "scheduler did not process the reminder in 90s"
        assert final_status in ("FAILED", "SENT"), f"unexpected status {final_status}"
        assert final_status != "COMPLETED", "scheduler auto-completed reminder, regression!"
