"""Sparsa Homeoclinic backend integration tests.

Covers: auth, RBAC, patients, cases workflow (reception→doctor→pharmacy→PRO),
prescriptions versioning, payments + receipt no, reminders, AI assist, admin.
"""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://simple-enterprise-ai.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
PWD = "Password@123"

USERS = ["admin1", "jyothi", "hemanth", "reception1", "pharmacy1", "pro1"]


def _login(session: requests.Session, username: str, password: str = PWD):
    r = session.post(f"{API}/auth/login", json={"username": username, "password": password})
    return r


@pytest.fixture(scope="session")
def sessions():
    """Create one Session per user, logged in. Use Bearer for reliability."""
    out = {}
    for u in USERS:
        s = requests.Session()
        r = _login(s, u)
        assert r.status_code == 200, f"login failed for {u}: {r.status_code} {r.text}"
        token = r.json().get("access_token")
        assert token, "access_token missing"
        s.headers.update({"Authorization": f"Bearer {token}"})
        out[u] = s
    return out


# ─────────────────────────── Auth ───────────────────────────
class TestAuth:
    def test_health(self):
        r = requests.get(f"{API}/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    @pytest.mark.parametrize("uname", USERS)
    def test_login_all_seeded(self, uname):
        s = requests.Session()
        r = _login(s, uname)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["user"]["username"] == uname
        assert "access_token" in data and len(data["access_token"]) > 20
        # httpOnly cookie set
        assert any(c.name == "access_token" for c in s.cookies), "access_token cookie not set"

    def test_login_invalid(self):
        r = requests.post(f"{API}/auth/login", json={"username": "admin1", "password": "wrong"})
        assert r.status_code == 401

    def test_me_with_cookie(self):
        s = requests.Session()
        _login(s, "admin1")
        # remove auth header path: use cookie only
        r = s.get(f"{API}/auth/me")
        assert r.status_code == 200
        assert r.json()["user"]["username"] == "admin1"

    def test_me_no_auth(self):
        r = requests.get(f"{API}/auth/me")
        assert r.status_code == 401

    def test_logout_clears_cookie(self):
        s = requests.Session()
        _login(s, "admin1")
        r = s.post(f"{API}/auth/logout")
        assert r.status_code == 200
        # subsequent /me must 401 (cookie cleared)
        r2 = s.get(f"{API}/auth/me")
        assert r2.status_code == 401


# ─────────────────────────── Doctors ───────────────────────────
class TestDoctors:
    def test_list_doctors(self, sessions):
        r = sessions["reception1"].get(f"{API}/doctors")
        assert r.status_code == 200
        docs = r.json()["doctors"]
        names = {d["display_name"] for d in docs}
        assert "Dr. Jyothi Vani" in names
        assert "Dr. Hemanth" in names
        assert len(docs) >= 2


# ─────────────────────── Shared fixtures for workflow ───────────────────────
@pytest.fixture(scope="session")
def patient_hemanth(sessions):
    """Create patient + case assigned to Hemanth."""
    suffix = uuid.uuid4().hex[:6]
    pr = sessions["reception1"].post(f"{API}/patients", json={
        "first_name": f"TEST_H_{suffix}", "last_name": "Patient",
        "gender": "MALE", "age": 30, "phone": f"99{suffix}",
        "address": "Test", "preferred_language": "EN",
    })
    assert pr.status_code == 200, pr.text
    p = pr.json()["patient"]
    assert p["patient_uid"].startswith("SPARSA-")
    cr = sessions["reception1"].post(f"{API}/cases", json={
        "patient_id": p["id"], "assigned_doctor_id": "doctor-hemanth",
        "complaint_text": "Headache and mild fever",
    })
    assert cr.status_code == 200, cr.text
    c = cr.json()["case"]
    assert c["status"] == "WAITING_FOR_DOCTOR"
    return {"patient": p, "case": c}


@pytest.fixture(scope="session")
def patient_jyothi(sessions):
    suffix = uuid.uuid4().hex[:6]
    pr = sessions["reception1"].post(f"{API}/patients", json={
        "first_name": f"TEST_J_{suffix}", "last_name": "Patient",
        "gender": "FEMALE", "age": 28, "phone": f"88{suffix}",
        "preferred_language": "EN",
    })
    p = pr.json()["patient"]
    cr = sessions["reception1"].post(f"{API}/cases", json={
        "patient_id": p["id"], "assigned_doctor_id": "doctor-jyothi",
        "complaint_text": "Cough",
    })
    return {"patient": p, "case": cr.json()["case"]}


# ─────────────────────────── Patients & Cases ───────────────────────────
class TestPatientsCases:
    def test_patient_uid_format(self, patient_hemanth):
        uid = patient_hemanth["patient"]["patient_uid"]
        assert uid.startswith("SPARSA-")
        assert len(uid) == len("SPARSA-000001")

    def test_get_patient(self, sessions, patient_hemanth):
        pid = patient_hemanth["patient"]["id"]
        r = sessions["reception1"].get(f"{API}/patients/{pid}")
        assert r.status_code == 200
        assert r.json()["patient"]["id"] == pid

    def test_reception_cant_access_admin(self, sessions):
        r = sessions["reception1"].get(f"{API}/admin/users")
        assert r.status_code == 403

    def test_pharmacy_cant_create_patient(self, sessions):
        r = sessions["pharmacy1"].post(f"{API}/patients", json={
            "first_name": "X", "last_name": "Y", "gender": "MALE",
            "age": 10, "phone": "1",
        })
        assert r.status_code == 403


# ─────────────────────────── RBAC on cases listing ───────────────────────────
class TestCasesRBAC:
    def test_hemanth_sees_only_own(self, sessions, patient_hemanth, patient_jyothi):
        r = sessions["hemanth"].get(f"{API}/cases")
        assert r.status_code == 200
        cases = r.json()["cases"]
        # All cases must be assigned to doctor-hemanth
        assert all(c["assigned_doctor_id"] == "doctor-hemanth" for c in cases), \
            f"Hemanth saw foreign cases: {[c['assigned_doctor_id'] for c in cases]}"
        ids = [c["id"] for c in cases]
        assert patient_hemanth["case"]["id"] in ids
        assert patient_jyothi["case"]["id"] not in ids

    def test_jyothi_sees_all(self, sessions, patient_hemanth, patient_jyothi):
        r = sessions["jyothi"].get(f"{API}/cases")
        assert r.status_code == 200
        ids = [c["id"] for c in r.json()["cases"]]
        assert patient_hemanth["case"]["id"] in ids
        assert patient_jyothi["case"]["id"] in ids

    def test_admin_sees_all(self, sessions, patient_hemanth, patient_jyothi):
        r = sessions["admin1"].get(f"{API}/cases")
        assert r.status_code == 200
        ids = [c["id"] for c in r.json()["cases"]]
        assert patient_hemanth["case"]["id"] in ids
        assert patient_jyothi["case"]["id"] in ids

    def test_hemanth_cannot_open_jyothis_case(self, sessions, patient_jyothi):
        cid = patient_jyothi["case"]["id"]
        r = sessions["hemanth"].get(f"{API}/cases/{cid}")
        assert r.status_code == 403


# ─────────────────────────── Full workflow ───────────────────────────
class TestWorkflow:
    def test_full_flow(self, sessions, patient_hemanth):
        cid = patient_hemanth["case"]["id"]
        # Doctor: move to IN_CONSULTATION
        r = sessions["hemanth"].patch(f"{API}/cases/{cid}/status", json={"status": "IN_CONSULTATION"})
        assert r.status_code == 200, r.text
        assert r.json()["case"]["status"] == "IN_CONSULTATION"

        # Save clinical notes
        r = sessions["hemanth"].put(f"{API}/cases/{cid}/notes", json={
            "diagnosis_summary": "Acute viral", "sensitivity_allergies": "None",
            "safety_notes": "", "suggestions": "Rest", "additional_info": "",
        })
        assert r.status_code == 200
        assert r.json()["clinical_notes"]["diagnosis_summary"] == "Acute viral"

        # Prescription v1 by doctor
        r = sessions["hemanth"].post(f"{API}/cases/{cid}/prescription", json={
            "items": [{"medicine_name": "Belladonna", "potency": "30C", "dosage": "5 drops",
                       "frequency": "TID", "duration_days": 3, "instructions": "After food"}],
            "notes_for_patient": "Take regularly",
        })
        assert r.status_code == 200, r.text
        p1 = r.json()["prescription"]
        assert p1["version_no"] == 1
        assert p1["edited_by_pharmacy"] is False

        # Send to pharmacy
        r = sessions["hemanth"].patch(f"{API}/cases/{cid}/status", json={"status": "SENT_TO_PHARMACY"})
        assert r.status_code == 200

        # Followup
        from datetime import datetime, timezone, timedelta
        future = datetime.now(timezone.utc) + timedelta(days=7)
        r = sessions["hemanth"].post(f"{API}/cases/{cid}/followup", json={
            "next_followup_at": future.isoformat(), "followup_note": "Recheck in a week",
        })
        assert r.status_code == 200

        # Pharmacy edits prescription -> v2
        r = sessions["pharmacy1"].post(f"{API}/cases/{cid}/prescription", json={
            "items": [{"medicine_name": "Belladonna", "potency": "30C", "dosage": "5 drops",
                       "frequency": "BID", "duration_days": 3, "instructions": ""}],
        })
        assert r.status_code == 200, r.text
        p2 = r.json()["prescription"]
        assert p2["version_no"] == 2
        assert p2["edited_by_pharmacy"] is True

        # Pharmacy dispenses → auto READY_FOR_BILLING
        r = sessions["pharmacy1"].post(f"{API}/cases/{cid}/dispense", json={
            "status": "FULL", "medicine_amount": 250.0,
            "patient_purchased_medicines": True, "pharmacy_notes": "ok",
        })
        assert r.status_code == 200
        # verify case status
        r2 = sessions["admin1"].get(f"{API}/cases/{cid}")
        assert r2.json()["case"]["status"] == "READY_FOR_BILLING"

        # Partial payment
        r = sessions["pro1"].post(f"{API}/cases/{cid}/payment", json={
            "consultation_amount": 300, "medicines_taken": True,
            "medicine_amount": 250, "amount_paid": 200, "payment_mode": "CASH",
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["case_status"] == "PARTIALLY_PAID"
        pay = body["payment"]
        assert pay["payment_status"] == "PARTIAL"
        assert pay["total_amount"] == 550
        assert pay["balance_amount"] == 350
        assert pay["receipt_no"].startswith("SPH-RC-")
        first_receipt = pay["receipt_no"]

        # Full payment closes the case (receipt_no stable)
        r = sessions["pro1"].post(f"{API}/cases/{cid}/payment", json={
            "consultation_amount": 300, "medicines_taken": True,
            "medicine_amount": 250, "amount_paid": 550, "payment_mode": "CASH",
        })
        assert r.status_code == 200
        body = r.json()
        assert body["case_status"] == "CLOSED"
        assert body["payment"]["payment_status"] == "PAID"
        assert body["payment"]["receipt_no"] == first_receipt


# ─────────────────────────── Reminders ───────────────────────────
class TestReminders:
    def test_hemanth_reminders_filtered(self, sessions, patient_hemanth):
        r = sessions["hemanth"].get(f"{API}/reminders")
        assert r.status_code == 200
        items = r.json()["reminders"]
        assert all(rem["doctor_id"] == "doctor-hemanth" for rem in items)

    def test_jyothi_reminders_unfiltered(self, sessions):
        r = sessions["jyothi"].get(f"{API}/reminders")
        assert r.status_code == 200


# ─────────────────────────── AI assist ───────────────────────────
class TestAI:
    def test_ai_summarize(self, sessions, patient_hemanth):
        cid = patient_hemanth["case"]["id"]
        r = sessions["hemanth"].post(f"{API}/cases/{cid}/ai/summarize", json={})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["action"] == "summarize"
        assert isinstance(body["result"], str) and len(body["result"]) > 10

    def test_ai_advice(self, sessions, patient_hemanth):
        cid = patient_hemanth["case"]["id"]
        r = sessions["hemanth"].post(f"{API}/cases/{cid}/ai/advice", json={})
        assert r.status_code == 200, r.text
        assert len(r.json()["result"]) > 10

    def test_ai_instructions(self, sessions, patient_hemanth):
        cid = patient_hemanth["case"]["id"]
        r = sessions["hemanth"].post(f"{API}/cases/{cid}/ai/instructions", json={})
        assert r.status_code == 200, r.text
        assert len(r.json()["result"]) > 5

    def test_ai_forbidden_for_non_doctor(self, sessions, patient_hemanth):
        cid = patient_hemanth["case"]["id"]
        r = sessions["reception1"].post(f"{API}/cases/{cid}/ai/summarize", json={})
        assert r.status_code == 403


# ─────────────────────────── Admin ───────────────────────────
class TestAdmin:
    def test_admin_list_users(self, sessions):
        r = sessions["admin1"].get(f"{API}/admin/users")
        assert r.status_code == 200
        usernames = {u["username"] for u in r.json()["users"]}
        for u in USERS:
            assert u in usernames

    def test_non_admin_blocked_audit(self, sessions):
        r = sessions["jyothi"].get(f"{API}/admin/audit-logs")
        assert r.status_code == 403

    def test_admin_audit_logs(self, sessions):
        r = sessions["admin1"].get(f"{API}/admin/audit-logs?limit=50")
        assert r.status_code == 200
        logs = r.json()["audit_logs"]
        actions = {l["action"] for l in logs}
        # LOGIN must exist (we logged in many times)
        assert "LOGIN" in actions

    def test_admin_stats(self, sessions):
        r = sessions["admin1"].get(f"{API}/admin/stats")
        assert r.status_code == 200
        body = r.json()
        for k in ("total_patients", "total_cases", "by_status", "by_doctor", "total_revenue"):
            assert k in body

    def test_admin_create_user(self, sessions):
        uname = f"test_user_{uuid.uuid4().hex[:6]}"
        r = sessions["admin1"].post(f"{API}/admin/users", json={
            "username": uname, "name": "Test User", "password": "TempPass@1",
            "role": "RECEPTION",
        })
        assert r.status_code == 200, r.text
        assert r.json()["user"]["username"] == uname
        assert "password_hash" not in r.json()["user"]
        # verify new user can login
        s = requests.Session()
        r2 = _login(s, uname, "TempPass@1")
        assert r2.status_code == 200

    def test_admin_create_duplicate(self, sessions):
        r = sessions["admin1"].post(f"{API}/admin/users", json={
            "username": "admin1", "name": "Dup", "password": "x", "role": "ADMIN",
        })
        assert r.status_code == 400
