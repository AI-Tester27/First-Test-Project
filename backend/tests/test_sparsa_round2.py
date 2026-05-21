"""Sparsa Homeoclinic round-2 backend tests.

Covers new features:
- Health providers status
- Case attachments (upload/list/download/delete, RBAC, validations)
- Patient timeline endpoint
- CSV exports (patients, cases, payments, prescriptions, audit) + RBAC
- Reminder send-now graceful PROVIDER_NOT_CONFIGURED fallback
- Audit log entries for new actions
"""
import io
import os
import uuid
from datetime import datetime, timezone, timedelta

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


@pytest.fixture(scope="module")
def case_hemanth(sessions):
    """Create a fresh patient + case assigned to doctor-hemanth via reception."""
    suffix = uuid.uuid4().hex[:6]
    pr = sessions["reception1"].post(f"{API}/patients", json={
        "first_name": f"TEST_R2H_{suffix}", "last_name": "Patient",
        "gender": "MALE", "age": 33, "phone": f"700{suffix}",
        "preferred_language": "EN",
    })
    assert pr.status_code == 200, pr.text
    p = pr.json()["patient"]
    cr = sessions["reception1"].post(f"{API}/cases", json={
        "patient_id": p["id"], "assigned_doctor_id": "doctor-hemanth",
        "complaint_text": "Round2 attach test",
    })
    assert cr.status_code == 200, cr.text
    return {"patient": p, "case": cr.json()["case"]}


@pytest.fixture(scope="module")
def case_jyothi(sessions):
    suffix = uuid.uuid4().hex[:6]
    pr = sessions["reception1"].post(f"{API}/patients", json={
        "first_name": f"TEST_R2J_{suffix}", "last_name": "Patient",
        "gender": "FEMALE", "age": 41, "phone": f"800{suffix}",
        "preferred_language": "EN",
    })
    p = pr.json()["patient"]
    cr = sessions["reception1"].post(f"{API}/cases", json={
        "patient_id": p["id"], "assigned_doctor_id": "doctor-jyothi",
        "complaint_text": "Jyothi case",
    })
    return {"patient": p, "case": cr.json()["case"]}


# Tiny valid PNG (1x1 transparent) so storage accepts it
TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xff"
    b"\xff?\x00\x05\xfe\x02\xfe\xa6\x35\x81\x84\x00\x00\x00\x00IEND\xaeB`\x82"
)
TINY_JPG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00" + b"\x00" * 32 + b"\xff\xd9"
TINY_PDF = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


# ─────────────────────────── Health ───────────────────────────
class TestHealthProviders:
    def test_health_returns_providers(self):
        r = requests.get(f"{API}/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert "providers" in body and isinstance(body["providers"], dict)
        assert "whatsapp" in body["providers"]
        assert "sms" in body["providers"]
        # In this env Twilio/WhatsApp keys are intentionally absent
        assert body["providers"]["whatsapp"] is False
        assert body["providers"]["sms"] is False


# ─────────────────────────── Attachments ───────────────────────────
class TestAttachments:
    def test_upload_png(self, sessions, case_hemanth):
        cid = case_hemanth["case"]["id"]
        r = sessions["hemanth"].post(
            f"{API}/cases/{cid}/attachments",
            files={"file": ("lab.png", TINY_PNG, "image/png")},
        )
        assert r.status_code == 200, r.text
        a = r.json()["attachment"]
        assert a["case_id"] == cid
        assert a["content_type"] == "image/png"
        assert a["is_deleted"] is False
        assert a["storage_path"]
        assert a["size_bytes"] == len(TINY_PNG)
        pytest.png_attach_id = a["id"]

    def test_upload_jpg(self, sessions, case_hemanth):
        cid = case_hemanth["case"]["id"]
        r = sessions["hemanth"].post(
            f"{API}/cases/{cid}/attachments",
            files={"file": ("scan.jpg", TINY_JPG, "image/jpeg")},
        )
        assert r.status_code == 200, r.text
        assert r.json()["attachment"]["content_type"] == "image/jpeg"

    def test_upload_pdf(self, sessions, case_hemanth):
        cid = case_hemanth["case"]["id"]
        r = sessions["hemanth"].post(
            f"{API}/cases/{cid}/attachments",
            files={"file": ("report.pdf", TINY_PDF, "application/pdf")},
        )
        assert r.status_code == 200, r.text
        assert r.json()["attachment"]["content_type"] == "application/pdf"

    def test_reject_exe(self, sessions, case_hemanth):
        cid = case_hemanth["case"]["id"]
        r = sessions["hemanth"].post(
            f"{API}/cases/{cid}/attachments",
            files={"file": ("malware.exe", b"MZ\x90\x00", "application/octet-stream")},
        )
        assert r.status_code == 400, r.text

    def test_reject_oversize(self, sessions, case_hemanth):
        cid = case_hemanth["case"]["id"]
        big = b"\x00" * (10 * 1024 * 1024 + 100)
        r = sessions["hemanth"].post(
            f"{API}/cases/{cid}/attachments",
            files={"file": ("big.pdf", big, "application/pdf")},
        )
        assert r.status_code == 413, r.text

    def test_list_attachments(self, sessions, case_hemanth):
        cid = case_hemanth["case"]["id"]
        r = sessions["hemanth"].get(f"{API}/cases/{cid}/attachments")
        assert r.status_code == 200
        files = r.json()["attachments"]
        assert len(files) >= 3
        assert all(not f["is_deleted"] for f in files)
        ids = [f["id"] for f in files]
        assert pytest.png_attach_id in ids

    def test_download_png(self, sessions):
        aid = pytest.png_attach_id
        r = sessions["hemanth"].get(f"{API}/attachments/{aid}/download")
        assert r.status_code == 200, r.text
        assert r.headers.get("content-type", "").startswith("image/png")
        # bytes should match exactly what we uploaded
        assert r.content == TINY_PNG

    def test_rbac_hemanth_blocked_on_jyothi_case_attachments(self, sessions, case_jyothi):
        cid = case_jyothi["case"]["id"]
        # list
        r = sessions["hemanth"].get(f"{API}/cases/{cid}/attachments")
        assert r.status_code == 403, r.text
        # upload
        r2 = sessions["hemanth"].post(
            f"{API}/cases/{cid}/attachments",
            files={"file": ("x.png", TINY_PNG, "image/png")},
        )
        assert r2.status_code == 403, r2.text

    def test_soft_delete(self, sessions, case_hemanth):
        aid = pytest.png_attach_id
        r = sessions["hemanth"].delete(f"{API}/attachments/{aid}")
        assert r.status_code == 200, r.text
        # Subsequent list must exclude it
        cid = case_hemanth["case"]["id"]
        r2 = sessions["hemanth"].get(f"{API}/cases/{cid}/attachments")
        ids = [f["id"] for f in r2.json()["attachments"]]
        assert aid not in ids
        # download of deleted should 404
        r3 = sessions["hemanth"].get(f"{API}/attachments/{aid}/download")
        assert r3.status_code == 404


# ─────────────────────────── Timeline ───────────────────────────
class TestTimeline:
    def test_timeline_basic(self, sessions, case_hemanth):
        pid = case_hemanth["patient"]["id"]
        r = sessions["hemanth"].get(f"{API}/patients/{pid}/timeline")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["patient"]["id"] == pid
        assert isinstance(body["timeline"], list)
        assert len(body["timeline"]) >= 1
        entry = body["timeline"][0]
        for k in ("case", "doctor", "payment", "clinical_notes", "prescriptions", "attachments_count"):
            assert k in entry, f"missing {k} in timeline entry"
        assert isinstance(entry["attachments_count"], int)
        # Two non-deleted attachments remaining after the soft-delete test
        assert entry["attachments_count"] >= 2

    def test_timeline_doctor_scope(self, sessions, case_jyothi):
        pid = case_jyothi["patient"]["id"]
        # hemanth viewing jyothi's patient: should see patient but NO cases since not his
        r = sessions["hemanth"].get(f"{API}/patients/{pid}/timeline")
        assert r.status_code == 200, r.text
        body = r.json()
        for entry in body["timeline"]:
            assert entry["case"]["assigned_doctor_id"] == "doctor-hemanth"


# ─────────────────────────── CSV exports ───────────────────────────
class TestCSVExports:
    def _check_csv(self, r, must_have_header_tokens):
        assert r.status_code == 200, r.text
        assert "text/csv" in r.headers.get("content-type", "")
        assert "attachment" in r.headers.get("content-disposition", "").lower()
        first_line = r.text.split("\n", 1)[0]
        for tok in must_have_header_tokens:
            assert tok in first_line, f"{tok} missing in CSV header: {first_line}"

    def test_export_patients(self, sessions):
        r = sessions["admin1"].get(f"{API}/admin/export/patients.csv")
        self._check_csv(r, ["patient_uid", "first_name", "phone"])
        assert "TEST_R2H_" in r.text or "TEST_R2J_" in r.text

    def test_export_cases(self, sessions):
        r = sessions["admin1"].get(f"{API}/admin/export/cases.csv")
        self._check_csv(r, ["case_uid", "patient_uid", "doctor", "status"])

    def test_export_payments(self, sessions):
        r = sessions["admin1"].get(f"{API}/admin/export/payments.csv")
        self._check_csv(r, ["receipt_no", "amount_paid", "total_amount"])

    def test_export_prescriptions(self, sessions):
        r = sessions["admin1"].get(f"{API}/admin/export/prescriptions.csv")
        self._check_csv(r, ["version_no", "edited_by_pharmacy", "medicine_name"])

    def test_export_audit_admin(self, sessions):
        r = sessions["admin1"].get(f"{API}/admin/export/audit.csv")
        self._check_csv(r, ["action", "actor_username", "entity_type"])
        # We've triggered EXPORT actions multiple times above already
        assert "EXPORT" in r.text

    def test_export_audit_rbac_reception(self, sessions):
        r = sessions["reception1"].get(f"{API}/admin/export/audit.csv")
        assert r.status_code == 403


# ─────────────────────────── Reminder send-now (graceful fallback) ───────────────────────────
class TestReminderSendNow:
    def test_send_now_provider_not_configured(self, sessions, case_hemanth):
        cid = case_hemanth["case"]["id"]
        # Create a followup -> creates reminder
        future = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
        fr = sessions["hemanth"].post(
            f"{API}/cases/{cid}/followup",
            json={"next_followup_at": future, "followup_note": "round2 reminder"},
        )
        assert fr.status_code == 200, fr.text

        # Find the new reminder for this case
        rl = sessions["hemanth"].get(f"{API}/reminders")
        assert rl.status_code == 200
        body = rl.json()
        assert "providers" in body
        assert body["providers"]["whatsapp"] is False
        assert body["providers"]["sms"] is False
        reminders = [r for r in body["reminders"] if r["case_id"] == cid]
        assert reminders, "expected at least one reminder for the case"
        rid = reminders[0]["id"]

        # Send now -> should NOT crash; should return reminder marked FAILED w/ PROVIDER_NOT_CONFIGURED
        sr = sessions["hemanth"].post(f"{API}/reminders/{rid}/send-now")
        assert sr.status_code == 200, sr.text
        upd = sr.json()["reminder"]
        assert upd["id"] == rid
        assert upd["status"] == "FAILED", upd
        assert "PROVIDER_NOT_CONFIGURED" in (upd.get("fail_reason") or ""), upd.get("fail_reason")


# ─────────────────────────── Audit entries for new actions ───────────────────────────
class TestAuditNewActions:
    def test_audit_contains_new_actions(self, sessions):
        r = sessions["admin1"].get(f"{API}/admin/audit-logs?limit=200")
        assert r.status_code == 200
        actions = {row["action"] for row in r.json()["audit_logs"]}
        for a in ("ATTACHMENT_UPLOAD", "ATTACHMENT_DOWNLOAD", "ATTACHMENT_DELETE", "EXPORT"):
            assert a in actions, f"audit log missing {a}: present={actions}"
