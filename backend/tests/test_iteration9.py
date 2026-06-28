"""Iteration 9 backend tests: workflow re-order, bypass reasons, reminders enhancements, AI Master Prompt."""
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"

CREDS = {
    "admin1": "Password@123",
    "jyothi": "Password@123",
    "hemanth": "Password@123",
    "reception1": "Password@123",
    "pharmacy1": "Password@123",
    "pro1": "Password@123",
}


def _session(username: str) -> requests.Session:
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"username": username, "password": CREDS[username]}, timeout=15)
    assert r.status_code == 200, f"login {username} failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def admin():
    return _session("admin1")


@pytest.fixture(scope="module")
def jyothi():
    return _session("jyothi")


@pytest.fixture(scope="module")
def hemanth():
    return _session("hemanth")


@pytest.fixture(scope="module")
def reception():
    return _session("reception1")


@pytest.fixture(scope="module")
def pharmacy():
    return _session("pharmacy1")


@pytest.fixture(scope="module")
def pro():
    return _session("pro1")


@pytest.fixture(scope="module")
def doctor_ids(admin):
    r = admin.get(f"{API}/doctors", timeout=15)
    assert r.status_code == 200
    docs = r.json()["doctors"]
    out = {}
    for d in docs:
        name = (d.get("display_name") or "").lower()
        if "jyothi" in name:
            out["jyothi"] = d["id"]
        elif "hemanth" in name:
            out["hemanth"] = d["id"]
    return out


def _create_case(reception, doctor_id, suffix="ITER9"):
    r = reception.post(f"{API}/patients/fir", json={
        "first_name": f"TEST_{suffix}_{uuid.uuid4().hex[:6]}", "last_name": "Z",
        "gender": "MALE", "age": 33, "phone": "9990001234",
        "preferred_language": "EN",
        "consulting_doctor_id": doctor_id,
        "chief_complaint": "Iter9 test",
        "visit_type": "WALK_IN",
    }, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["case"]["id"], r.json()["patient"]["id"]


# ---------------- Workflow: Doctor transitions ----------------
class TestWorkflowDoctor:
    def test_doctor_send_to_pro(self, reception, hemanth, doctor_ids):
        cid, _ = _create_case(reception, doctor_ids["hemanth"])
        # in-consult first
        r = hemanth.patch(f"{API}/cases/{cid}/status", json={"status": "IN_CONSULTATION"}, timeout=15)
        assert r.status_code == 200, r.text
        r = hemanth.patch(f"{API}/cases/{cid}/status", json={"status": "AWAITING_PRO_REVIEW"}, timeout=15)
        assert r.status_code == 200, r.text
        case = r.json()["case"]
        assert case["status"] == "AWAITING_PRO_REVIEW"
        assert case.get("sent_to_pro_at")
        assert case.get("consultation_completed_at")

    def test_doctor_bypass_requires_reason(self, reception, hemanth, doctor_ids):
        cid, _ = _create_case(reception, doctor_ids["hemanth"])
        hemanth.patch(f"{API}/cases/{cid}/status", json={"status": "IN_CONSULTATION"}, timeout=15)
        # No reason → 400
        r = hemanth.patch(f"{API}/cases/{cid}/status", json={"status": "SENT_TO_PHARMACY"}, timeout=15)
        assert r.status_code == 400, r.text
        # Empty reason → 400
        r = hemanth.patch(f"{API}/cases/{cid}/status", json={"status": "SENT_TO_PHARMACY", "bypass_reason": "   "}, timeout=15)
        assert r.status_code == 400
        # With reason → 200
        r = hemanth.patch(f"{API}/cases/{cid}/status", json={"status": "SENT_TO_PHARMACY", "bypass_reason": "Refill — known patient"}, timeout=15)
        assert r.status_code == 200, r.text
        case = r.json()["case"]
        assert case["status"] == "SENT_TO_PHARMACY"
        assert case.get("pharmacy_bypassed_pro") is True
        assert case.get("pharmacy_bypass_reason") == "Refill — known patient"


# ---------------- Workflow: PRO ----------------
class TestWorkflowPRO:
    def test_pro_can_set_sent_to_pharmacy(self, reception, hemanth, pro, doctor_ids):
        cid, _ = _create_case(reception, doctor_ids["hemanth"])
        hemanth.patch(f"{API}/cases/{cid}/status", json={"status": "IN_CONSULTATION"})
        hemanth.patch(f"{API}/cases/{cid}/status", json={"status": "AWAITING_PRO_REVIEW"})
        r = pro.patch(f"{API}/cases/{cid}/status", json={"status": "SENT_TO_PHARMACY"}, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json()["case"]["status"] == "SENT_TO_PHARMACY"

    def test_pro_payment_paid_with_medicines_auto_forwards(self, reception, hemanth, pro, doctor_ids):
        cid, _ = _create_case(reception, doctor_ids["hemanth"])
        hemanth.patch(f"{API}/cases/{cid}/status", json={"status": "IN_CONSULTATION"})
        hemanth.patch(f"{API}/cases/{cid}/status", json={"status": "AWAITING_PRO_REVIEW"})
        r = pro.post(f"{API}/cases/{cid}/payment", json={
            "consultation_amount": 300, "medicine_amount": 200,
            "amount_paid": 500, "payment_mode": "CASH", "medicines_taken": True,
        }, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json()["case_status"] == "SENT_TO_PHARMACY"

    def test_pro_paid_no_medicines_closes(self, reception, hemanth, pro, doctor_ids):
        cid, _ = _create_case(reception, doctor_ids["hemanth"])
        hemanth.patch(f"{API}/cases/{cid}/status", json={"status": "IN_CONSULTATION"})
        hemanth.patch(f"{API}/cases/{cid}/status", json={"status": "AWAITING_PRO_REVIEW"})
        r = pro.post(f"{API}/cases/{cid}/payment", json={
            "consultation_amount": 300, "medicine_amount": 0,
            "amount_paid": 300, "payment_mode": "CASH", "medicines_taken": False,
        }, timeout=15)
        assert r.status_code == 200
        assert r.json()["case_status"] == "CLOSED"

    def test_pro_partial(self, reception, hemanth, pro, doctor_ids):
        cid, _ = _create_case(reception, doctor_ids["hemanth"])
        hemanth.patch(f"{API}/cases/{cid}/status", json={"status": "IN_CONSULTATION"})
        hemanth.patch(f"{API}/cases/{cid}/status", json={"status": "AWAITING_PRO_REVIEW"})
        r = pro.post(f"{API}/cases/{cid}/payment", json={
            "consultation_amount": 300, "medicine_amount": 200,
            "amount_paid": 100, "payment_mode": "CASH", "medicines_taken": True,
        }, timeout=15)
        assert r.json()["case_status"] == "PARTIALLY_PAID"

    def test_pro_unpaid(self, reception, hemanth, pro, doctor_ids):
        cid, _ = _create_case(reception, doctor_ids["hemanth"])
        hemanth.patch(f"{API}/cases/{cid}/status", json={"status": "IN_CONSULTATION"})
        hemanth.patch(f"{API}/cases/{cid}/status", json={"status": "AWAITING_PRO_REVIEW"})
        r = pro.post(f"{API}/cases/{cid}/payment", json={
            "consultation_amount": 300, "medicine_amount": 200,
            "amount_paid": 0, "payment_mode": "CASH", "medicines_taken": True,
        }, timeout=15)
        assert r.json()["case_status"] == "PAYMENT_PENDING"


# ---------------- Workflow: Pharmacy dispense closes ----------------
class TestWorkflowPharmacy:
    def test_dispense_closes_case(self, reception, hemanth, pro, pharmacy, doctor_ids):
        cid, _ = _create_case(reception, doctor_ids["hemanth"])
        hemanth.patch(f"{API}/cases/{cid}/status", json={"status": "IN_CONSULTATION"})
        hemanth.patch(f"{API}/cases/{cid}/status", json={"status": "AWAITING_PRO_REVIEW"})
        pro.post(f"{API}/cases/{cid}/payment", json={
            "consultation_amount": 300, "medicine_amount": 200,
            "amount_paid": 500, "payment_mode": "CASH", "medicines_taken": True,
        })
        r = pharmacy.post(f"{API}/cases/{cid}/dispense", json={
            "status": "FULL", "medicine_amount": 200, "notes": "ok",
        }, timeout=15)
        assert r.status_code == 200, r.text
        # Verify status
        r2 = pharmacy.get(f"{API}/cases/{cid}", timeout=15)
        case = r2.json()["case"]
        assert case["status"] == "CLOSED"
        assert case.get("dispensed_at")
        assert case.get("closed_at")


# ---------------- Reminders ----------------
class TestReminders:
    @pytest.fixture(scope="class")
    def seed(self, reception, doctor_ids):
        cid, pid = _create_case(reception, doctor_ids["jyothi"], suffix="ITER9R")
        return {"cid": cid, "pid": pid}

    def test_create_reminder_sets_phone_and_date(self, jyothi, seed):
        sched = (datetime.now(timezone.utc) + timedelta(days=3)).replace(microsecond=0)
        r = jyothi.post(f"{API}/reminders", json={
            "patient_id": seed["pid"],
            "case_id": seed["cid"],
            "scheduled_at": sched.isoformat(),
            "message": "Iter9 reminder test",
            "audience": ["DOCTOR"],
        }, timeout=15)
        assert r.status_code == 200, r.text
        rem = r.json()["reminder"]
        assert rem.get("patient_phone")
        assert rem.get("scheduled_date") == sched.isoformat()[:10]
        return rem["id"]

    def test_snooze_writes_scheduled_date(self, jyothi, seed):
        sched = (datetime.now(timezone.utc) + timedelta(days=1)).replace(microsecond=0)
        r = jyothi.post(f"{API}/reminders", json={
            "patient_id": seed["pid"], "case_id": seed["cid"],
            "scheduled_at": sched.isoformat(), "message": "snz",
        }, timeout=15)
        rid = r.json()["reminder"]["id"]
        new_dt = (datetime.now(timezone.utc) + timedelta(days=5)).replace(microsecond=0)
        r2 = jyothi.patch(f"{API}/reminders/{rid}", json={"snooze_until": new_dt.isoformat()}, timeout=15)
        assert r2.status_code == 200, r2.text
        rem = r2.json()["reminder"]
        assert rem["status"] == "PENDING"
        assert rem.get("scheduled_date") == new_dt.isoformat()[:10]
        assert rem["scheduled_at"].startswith(new_dt.isoformat()[:13])

    def test_pharmacy_can_snooze_pharmacy_audience(self, jyothi, pharmacy, seed):
        sched = (datetime.now(timezone.utc) + timedelta(days=1)).replace(microsecond=0)
        r = jyothi.post(f"{API}/reminders", json={
            "patient_id": seed["pid"], "case_id": seed["cid"],
            "scheduled_at": sched.isoformat(), "message": "rx-refill",
            "audience": ["PHARMACY"], "notify_pharmacy": True,
        }, timeout=15)
        rid = r.json()["reminder"]["id"]
        new_dt = (datetime.now(timezone.utc) + timedelta(days=2)).replace(microsecond=0)
        r2 = pharmacy.patch(f"{API}/reminders/{rid}", json={"snooze_until": new_dt.isoformat()}, timeout=15)
        assert r2.status_code == 200, r2.text
        assert r2.json()["reminder"]["status"] == "PENDING"

    def test_pharmacy_cannot_snooze_non_pharmacy(self, jyothi, pharmacy, seed):
        sched = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        r = jyothi.post(f"{API}/reminders", json={
            "patient_id": seed["pid"], "case_id": seed["cid"],
            "scheduled_at": sched, "message": "doctor-only",
            "audience": ["DOCTOR"],
        }, timeout=15)
        rid = r.json()["reminder"]["id"]
        new_dt = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
        r2 = pharmacy.patch(f"{API}/reminders/{rid}", json={"snooze_until": new_dt}, timeout=15)
        assert r2.status_code == 403

    def test_audience_filter_mine(self, jyothi, seed):
        # Create a pharmacy-audience reminder owned by jyothi
        sched = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        jyothi.post(f"{API}/reminders", json={
            "patient_id": seed["pid"], "case_id": seed["cid"],
            "scheduled_at": sched, "message": "ph-only",
            "audience": ["PHARMACY"], "notify_pharmacy": True,
        }, timeout=15)
        r = jyothi.get(f"{API}/reminders?audience=MINE", timeout=15)
        assert r.status_code == 200
        rems = r.json()["reminders"]
        # All should belong to Jyothi's doctor_id
        me = jyothi.get(f"{API}/auth/me", timeout=15).json().get("user") or jyothi.get(f"{API}/auth/me", timeout=15).json()
        my_doc_id = me.get("doctor_id")
        for rem in rems:
            assert rem.get("doctor_id") == my_doc_id

    def test_audience_filter_pharmacy(self, jyothi):
        r = jyothi.get(f"{API}/reminders?audience=PHARMACY", timeout=15)
        assert r.status_code == 200
        for rem in r.json()["reminders"]:
            assert "PHARMACY" in (rem.get("audience") or [])

    def test_audience_filter_all(self, jyothi):
        r = jyothi.get(f"{API}/reminders?audience=ALL", timeout=15)
        assert r.status_code == 200

    def test_non_owner_doctor_ignores_audience(self, hemanth):
        # Doctor scope filter takes precedence — audience=PHARMACY param ignored
        r = hemanth.get(f"{API}/reminders?audience=PHARMACY", timeout=15)
        assert r.status_code == 200
        # All returned should still be Hemanth's
        me = hemanth.get(f"{API}/auth/me", timeout=15).json()
        my_doc_id = (me.get("user") or me).get("doctor_id")
        for rem in r.json()["reminders"]:
            assert rem.get("doctor_id") == my_doc_id


# ---------------- AI Master Prompt ----------------
class TestAIMasterPrompt:
    REQUIRED_SECTIONS = [
        "## 1. Executive Summary",
        "## 2. Clinical Assessment",
        "## 3. Homeopathic Analysis",
        "## 4. Remedy Suggestions",
        "## 5. Mother Tincture Suggestions",
        "## 6. Patient Advice",
        "## 7. Prescription Instructions",
        "## 8. Follow-up Recommendations",
        "## 9. Lifestyle Advice",
        "## 10. Confidence Score",
        "## 11. Missing Information",
    ]

    def test_detailed_master_prompt(self, reception, jyothi, doctor_ids):
        cid, pid = _create_case(reception, doctor_ids["jyothi"], suffix="ITER9AI")
        r = jyothi.post(f"{API}/patients/{pid}/ai/recap?mode=detailed", timeout=90)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["mode"] == "detailed"
        result = body["result"]
        for sec in self.REQUIRED_SECTIONS:
            assert sec in result, f"missing section: {sec}"
        assert "Disclaimer" in result
        assert ("**Confidence: LOW**" in result
                or "**Confidence: MEDIUM**" in result
                or "**Confidence: HIGH**" in result), "missing confidence marker"
