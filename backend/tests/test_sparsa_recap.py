"""Sparsa Homeoclinic — Phase 3 backend tests.

Covers:
- POST /api/patients/{id}/ai/recap (new endpoint): RBAC, doctor scope, audit log
- Sanity re-check of refactored endpoints still responding under /api
"""
import os
import uuid

import pytest
import requests

BASE_URL = os.environ.get(
    "REACT_APP_BACKEND_URL",
    "https://simple-enterprise-ai.preview.emergentagent.com",
).rstrip("/")
API = f"{BASE_URL}/api"
PWD = "Password@123"

USERS = ["admin1", "jyothi", "hemanth", "reception1", "pharmacy1", "pro1"]


def _login(session: requests.Session, username: str, password: str = PWD):
    return session.post(f"{API}/auth/login", json={"username": username, "password": password})


@pytest.fixture(scope="module")
def sessions():
    out = {}
    for u in USERS:
        s = requests.Session()
        r = _login(s, u)
        assert r.status_code == 200, f"login failed for {u}: {r.status_code} {r.text}"
        tok = r.json().get("access_token")
        assert tok
        s.headers.update({"Authorization": f"Bearer {tok}"})
        out[u] = s
    return out


def _add_clinical_note(session, case_id, complaint, diagnosis="Probable seasonal allergy",
                      allergies="No known drug allergies"):
    body = {
        "diagnosis_summary": diagnosis,
        "sensitivity_allergies": allergies,
        "safety_notes": "No major safety concerns noted",
        "suggestions": f"Suggested investigation for {complaint}",
        "additional_info": "",
    }
    r = session.put(f"{API}/cases/{case_id}/notes", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def _add_prescription(session, case_id, meds):
    body = {
        "items": [
            {"medicine_name": m, "potency": "30C", "dosage": "4 globules",
             "frequency": "TID", "duration_days": 5, "instructions": "Before food"}
            for m in meds
        ],
        "notes_for_patient": "Avoid spicy food.",
        "notes_internal": "Standard regimen",
    }
    r = session.post(f"{API}/cases/{case_id}/prescription", json=body)
    assert r.status_code == 200, r.text
    return r.json()


# ─────────────────────────── Fixtures: Two patients ───────────────────────────
@pytest.fixture(scope="module")
def patient_hem_multi(sessions):
    """Patient with 2 cases — BOTH assigned to Hemanth (so Hemanth can recap)."""
    suffix = uuid.uuid4().hex[:6]
    pr = sessions["reception1"].post(f"{API}/patients", json={
        "first_name": f"TEST_RECAP_HEM_{suffix}", "last_name": "Patient",
        "gender": "MALE", "age": 45, "phone": f"910{suffix}",
        "preferred_language": "EN",
    })
    assert pr.status_code == 200, pr.text
    p = pr.json()["patient"]

    cases = []
    for i, complaint in enumerate(
        ["Cough since 3 days", "Recurrent headache 2 weeks"], start=1
    ):
        cr = sessions["reception1"].post(f"{API}/cases", json={
            "patient_id": p["id"],
            "assigned_doctor_id": "doctor-hemanth",
            "complaint_text": complaint,
        })
        assert cr.status_code == 200, cr.text
        c = cr.json()["case"]
        cases.append(c)
        _add_clinical_note(sessions["hemanth"], c["id"], complaint,
                          diagnosis=f"Visit {i} working diagnosis")
        _add_prescription(sessions["hemanth"], c["id"],
                         ["Bryonia" if i == 1 else "Belladonna"])
    return {"patient": p, "cases": cases}


@pytest.fixture(scope="module")
def patient_jyothi_only(sessions):
    """Patient with cases ONLY assigned to Jyothi — Hemanth must NOT see recap."""
    suffix = uuid.uuid4().hex[:6]
    pr = sessions["reception1"].post(f"{API}/patients", json={
        "first_name": f"TEST_RECAP_JYO_{suffix}", "last_name": "Patient",
        "gender": "FEMALE", "age": 38, "phone": f"920{suffix}",
        "preferred_language": "EN",
    })
    assert pr.status_code == 200, pr.text
    p = pr.json()["patient"]
    cr = sessions["reception1"].post(f"{API}/cases", json={
        "patient_id": p["id"],
        "assigned_doctor_id": "doctor-jyothi",
        "complaint_text": "Migraine flare",
    })
    assert cr.status_code == 200, cr.text
    c = cr.json()["case"]
    _add_clinical_note(sessions["jyothi"], c["id"], "Migraine flare",
                      diagnosis="Migraine NOS")
    _add_prescription(sessions["jyothi"], c["id"], ["Natrum Mur"])
    return {"patient": p, "case": c}


@pytest.fixture(scope="module")
def patient_mixed(sessions):
    """Patient with 3 cases: 2 assigned to Hemanth, 1 to Jyothi.
    Hemanth recap should see only 2 visits; Jyothi recap should see 3."""
    suffix = uuid.uuid4().hex[:6]
    pr = sessions["reception1"].post(f"{API}/patients", json={
        "first_name": f"TEST_RECAP_MIX_{suffix}", "last_name": "Patient",
        "gender": "MALE", "age": 50, "phone": f"930{suffix}",
        "preferred_language": "EN",
    })
    assert pr.status_code == 200, pr.text
    p = pr.json()["patient"]
    assigns = [
        ("doctor-hemanth", "Joint pain visit 1", "hemanth"),
        ("doctor-jyothi",  "Skin rash visit 2", "jyothi"),
        ("doctor-hemanth", "Joint pain visit 3 follow-up", "hemanth"),
    ]
    cases = []
    for doc_id, complaint, who in assigns:
        cr = sessions["reception1"].post(f"{API}/cases", json={
            "patient_id": p["id"],
            "assigned_doctor_id": doc_id,
            "complaint_text": complaint,
        })
        assert cr.status_code == 200, cr.text
        c = cr.json()["case"]
        cases.append(c)
        _add_clinical_note(sessions[who], c["id"], complaint)
        _add_prescription(sessions[who], c["id"], ["Rhus Tox"])
    return {"patient": p, "cases": cases}


# ─────────────────────────── New endpoint tests ───────────────────────────
class TestAIRecap:
    def test_recap_jyothi_full_visits(self, sessions, patient_hem_multi):
        pid = patient_hem_multi["patient"]["id"]
        n_cases = len(patient_hem_multi["cases"])
        r = sessions["jyothi"].post(f"{API}/patients/{pid}/ai/recap")
        assert r.status_code == 200, r.text
        body = r.json()
        assert "result" in body and isinstance(body["result"], str)
        assert len(body["result"].strip()) > 0
        assert body["visits_analysed"] == n_cases

    def test_recap_admin_can_access(self, sessions, patient_hem_multi):
        pid = patient_hem_multi["patient"]["id"]
        r = sessions["admin1"].post(f"{API}/patients/{pid}/ai/recap")
        assert r.status_code == 200, r.text
        assert r.json()["visits_analysed"] == len(patient_hem_multi["cases"])

    def test_recap_hemanth_no_accessible_visits(self, sessions, patient_jyothi_only):
        pid = patient_jyothi_only["patient"]["id"]
        r = sessions["hemanth"].post(f"{API}/patients/{pid}/ai/recap")
        assert r.status_code == 404, r.text
        # Body should contain "No accessible visits" detail
        try:
            detail = r.json().get("detail", "")
        except Exception:
            detail = r.text
        assert "accessible" in detail.lower() or "visit" in detail.lower()

    def test_recap_hemanth_only_sees_his_cases(self, sessions, patient_mixed):
        pid = patient_mixed["patient"]["id"]
        # Hemanth has 2 of 3 cases for this patient
        r = sessions["hemanth"].post(f"{API}/patients/{pid}/ai/recap")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["visits_analysed"] == 2, f"Expected 2 (hemanth's cases), got {body['visits_analysed']}"
        assert isinstance(body["result"], str) and body["result"].strip()

    def test_recap_jyothi_sees_all_for_mixed(self, sessions, patient_mixed):
        pid = patient_mixed["patient"]["id"]
        r = sessions["jyothi"].post(f"{API}/patients/{pid}/ai/recap")
        assert r.status_code == 200, r.text
        assert r.json()["visits_analysed"] == 3

    def test_recap_nonexistent_patient(self, sessions):
        bogus = "nonexistent-" + uuid.uuid4().hex
        r = sessions["jyothi"].post(f"{API}/patients/{bogus}/ai/recap")
        assert r.status_code == 404, r.text

    def test_recap_reception_forbidden(self, sessions, patient_hem_multi):
        pid = patient_hem_multi["patient"]["id"]
        r = sessions["reception1"].post(f"{API}/patients/{pid}/ai/recap")
        assert r.status_code == 403, r.text

    def test_recap_pharmacy_forbidden(self, sessions, patient_hem_multi):
        pid = patient_hem_multi["patient"]["id"]
        r = sessions["pharmacy1"].post(f"{API}/patients/{pid}/ai/recap")
        assert r.status_code == 403, r.text

    def test_recap_pro_forbidden(self, sessions, patient_hem_multi):
        pid = patient_hem_multi["patient"]["id"]
        r = sessions["pro1"].post(f"{API}/patients/{pid}/ai/recap")
        assert r.status_code == 403, r.text

    def test_recap_audit_log_entry(self, sessions, patient_hem_multi):
        """After recap calls above, admin audit log must contain AI_USED Patient/recap entry."""
        pid = patient_hem_multi["patient"]["id"]
        # Fire one more recap to ensure recent entry
        r = sessions["jyothi"].post(f"{API}/patients/{pid}/ai/recap")
        assert r.status_code == 200, r.text
        n_cases = r.json()["visits_analysed"]

        # Pull audit logs (admin only)
        ar = sessions["admin1"].get(f"{API}/admin/audit-logs?limit=200")
        assert ar.status_code == 200, ar.text
        logs = ar.json()
        # logs may be list or {logs: [...]} or {audit_logs: [...]}
        if isinstance(logs, dict):
            logs = logs.get("audit_logs") or logs.get("logs") or logs.get("items") or []
        matching = [
            lg for lg in logs
            if lg.get("action") == "AI_USED"
            and lg.get("entity_type") == "Patient"
            and lg.get("entity_id") == pid
            and (lg.get("metadata") or {}).get("action") == "recap"
        ]
        assert matching, f"No AI_USED/Patient/recap audit entry for patient {pid}"
        # Verify visits count is present
        assert any(
            (lg.get("metadata") or {}).get("visits") == n_cases for lg in matching
        ), "Audit metadata.visits did not match returned visits_analysed"


# ─────────────────────────── Regression sanity (refactor) ───────────────────────────
class TestRefactorSanity:
    def test_health_with_providers(self):
        r = requests.get(f"{API}/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert "providers" in body
        assert "whatsapp" in body["providers"]
        assert "sms" in body["providers"]

    def test_login_endpoint(self):
        r = requests.post(f"{API}/auth/login", json={"username": "jyothi", "password": PWD})
        assert r.status_code == 200
        assert "access_token" in r.json()

    def test_cases_list(self, sessions):
        r = sessions["jyothi"].get(f"{API}/cases")
        assert r.status_code == 200
        # cases endpoint returns either list or dict {cases: [...]}
        body = r.json()
        if isinstance(body, dict):
            body = body.get("cases", body.get("items", []))
        assert isinstance(body, list)

    def test_patient_timeline(self, sessions, patient_hem_multi):
        pid = patient_hem_multi["patient"]["id"]
        r = sessions["jyothi"].get(f"{API}/patients/{pid}/timeline")
        assert r.status_code == 200, r.text

    def test_case_attachments_list(self, sessions, patient_hem_multi):
        cid = patient_hem_multi["cases"][0]["id"]
        r = sessions["jyothi"].get(f"{API}/cases/{cid}/attachments")
        assert r.status_code == 200, r.text

    def test_reminders_list(self, sessions):
        r = sessions["jyothi"].get(f"{API}/reminders")
        assert r.status_code == 200, r.text

    def test_admin_csv_export_patients(self, sessions):
        r = sessions["admin1"].get(f"{API}/admin/export/patients.csv")
        assert r.status_code == 200, r.text
        assert "text/csv" in r.headers.get("content-type", "").lower()

    def test_admin_csv_export_cases(self, sessions):
        r = sessions["admin1"].get(f"{API}/admin/export/cases.csv")
        assert r.status_code == 200, r.text
        assert "text/csv" in r.headers.get("content-type", "").lower()
