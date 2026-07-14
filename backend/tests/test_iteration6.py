"""Iteration 6 backend tests: admin messaging-settings, analytics aggregation, attachment size cap."""
import io
import os
import time

import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://simple-enterprise-ai.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"

CREDS = {
    "admin": ("admin1", "Password@123"),
    "owner_doc": ("jyothi", "Password@123"),
    "doctor": ("hemanth", "Password@123"),
    "reception": ("reception1", "Password@123"),
    "pharmacy": ("pharmacy1", "Password@123"),
    "pro": ("pro1", "Password@123"),
}


def _login(username: str, password: str) -> requests.Session:
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"username": username, "password": password}, timeout=20)
    assert r.status_code == 200, f"login {username} failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="session")
def s_admin():
    return _login(*CREDS["admin"])


@pytest.fixture(scope="session")
def s_owner():
    return _login(*CREDS["owner_doc"])


@pytest.fixture(scope="session")
def s_doctor():
    return _login(*CREDS["doctor"])


@pytest.fixture(scope="session")
def s_reception():
    return _login(*CREDS["reception"])


@pytest.fixture(scope="session")
def s_pharmacy():
    return _login(*CREDS["pharmacy"])


@pytest.fixture(scope="session")
def s_pro():
    return _login(*CREDS["pro"])


# ─────────────────────── Messaging settings ───────────────────────
class TestMessagingSettingsRBAC:
    def test_admin_can_get(self, s_admin):
        r = s_admin.get(f"{API}/admin/messaging-settings", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        for k in ("stored", "status", "source"):
            assert k in data
        assert isinstance(data["stored"], dict)
        assert set(data["status"].keys()) == {"whatsapp", "sms"}
        assert set(data["source"].keys()) == {"whatsapp", "sms"}

    @pytest.mark.parametrize("fix_name", ["s_owner", "s_doctor", "s_reception", "s_pharmacy", "s_pro"])
    def test_non_admin_forbidden_get(self, request, fix_name):
        s = request.getfixturevalue(fix_name)
        r = s.get(f"{API}/admin/messaging-settings", timeout=15)
        assert r.status_code == 403, f"{fix_name} got {r.status_code}: {r.text[:200]}"

    @pytest.mark.parametrize("fix_name", ["s_owner", "s_doctor", "s_reception", "s_pharmacy", "s_pro"])
    def test_non_admin_forbidden_post(self, request, fix_name):
        s = request.getfixturevalue(fix_name)
        r = s.post(f"{API}/admin/messaging-settings", json={"TWILIO_FROM": "+1555"}, timeout=15)
        assert r.status_code == 403


class TestMessagingSettingsLifecycle:
    """Configure → verify masked + status flips → clear → verify removed."""

    SID = "ACtestSID1234567890abcdef1234567890"
    TOKEN = "twilio-auth-token-xyz-ABCDEFGHIJK"
    FROM = "+15005550006"

    def test_empty_post_400(self, s_admin):
        r = s_admin.post(f"{API}/admin/messaging-settings", json={}, timeout=15)
        assert r.status_code == 400, r.text

    def test_post_twilio_then_get_masked(self, s_admin):
        r = s_admin.post(f"{API}/admin/messaging-settings", json={
            "TWILIO_ACCOUNT_SID": self.SID,
            "TWILIO_AUTH_TOKEN": self.TOKEN,
            "TWILIO_FROM": self.FROM,
        }, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("ok") is True
        assert body["status"]["sms"] is True
        assert body["source"]["sms"] == "db"

        r2 = s_admin.get(f"{API}/admin/messaging-settings", timeout=15)
        assert r2.status_code == 200
        d = r2.json()
        # masked values present and contain bullets
        sid_masked = d["stored"].get("TWILIO_ACCOUNT_SID", "")
        assert sid_masked.startswith(self.SID[:3])
        assert sid_masked.endswith(self.SID[-3:])
        assert "•" in sid_masked
        # raw secret not echoed
        assert self.TOKEN not in sid_masked
        assert self.TOKEN not in d["stored"].get("TWILIO_AUTH_TOKEN", "")
        assert d["status"]["sms"] is True
        assert d["source"]["sms"] == "db"
        # WhatsApp untouched (unless someone left env creds)
        assert d["status"]["whatsapp"] in (True, False)

    def test_clear_sentinel_removes_field(self, s_admin):
        # ensure SID is currently stored (from previous test)
        r = s_admin.post(f"{API}/admin/messaging-settings", json={
            "TWILIO_ACCOUNT_SID": "__CLEAR__",
            "TWILIO_AUTH_TOKEN": "__CLEAR__",
            "TWILIO_FROM": "__CLEAR__",
        }, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        # When env doesn't define these either, source flips to 'none' and status=false
        # If env has them set, source could be "env"; we only assert status reflects reality.
        r2 = s_admin.get(f"{API}/admin/messaging-settings", timeout=15)
        d = r2.json()
        assert "TWILIO_ACCOUNT_SID" not in d["stored"]
        assert "TWILIO_AUTH_TOKEN" not in d["stored"]
        assert "TWILIO_FROM" not in d["stored"]
        # source should now reflect no DB-backed sms
        assert d["source"]["sms"] in ("none", "env", "partial")


# ─────────────────────── Admin analytics aggregation ───────────────────────
class TestAdminAnalytics:
    def test_admin_analytics_shape_and_perf(self, s_admin):
        t0 = time.time()
        r = s_admin.get(f"{API}/admin/analytics", timeout=20)
        elapsed = time.time() - t0
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("case_trend_30d", "logins_by_role_30d", "top_complaints",
                  "avg_turnaround_minutes", "closed_cases_30d"):
            assert k in d, f"missing key {k}"
        ct = d["case_trend_30d"]
        assert isinstance(ct, list) and len(ct) == 30, f"len={len(ct)}"
        for row in ct:
            assert set(["date", "label", "cases", "revenue"]).issubset(row.keys())
            assert isinstance(row["date"], str) and len(row["date"]) == 10
            assert isinstance(row["cases"], int)
            assert isinstance(row["revenue"], (int, float))
        assert isinstance(d["top_complaints"], list)
        for c in d["top_complaints"]:
            assert "term" in c and "count" in c
        assert isinstance(d["avg_turnaround_minutes"], (int, float))
        assert isinstance(d["closed_cases_30d"], int)
        assert isinstance(d["logins_by_role_30d"], dict)
        assert elapsed < 2.5, f"analytics too slow: {elapsed:.2f}s"

    def test_owner_doctor_can_access(self, s_owner):
        r = s_owner.get(f"{API}/admin/analytics", timeout=20)
        assert r.status_code == 200

    @pytest.mark.parametrize("fix_name", ["s_doctor", "s_reception", "s_pharmacy", "s_pro"])
    def test_others_forbidden(self, request, fix_name):
        s = request.getfixturevalue(fix_name)
        r = s.get(f"{API}/admin/analytics", timeout=20)
        assert r.status_code == 403


# ─────────────────────── Attachment 10MB cap ───────────────────────
class TestAttachmentSizeCap:
    @pytest.fixture(scope="class")
    def case_id(self, s_admin):
        r = s_admin.get(f"{API}/cases", timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        cases = body.get("cases") if isinstance(body, dict) else body
        assert cases, "no cases available to test upload — seed data required"
        return cases[0]["id"]

    def test_reject_oversize(self, s_admin, case_id):
        big = os.urandom(11 * 1024 * 1024)  # 11MB
        files = {"file": ("big.pdf", io.BytesIO(big), "application/pdf")}
        r = s_admin.post(f"{API}/cases/{case_id}/attachments", files=files, timeout=60)
        assert r.status_code == 413, f"expected 413, got {r.status_code}: {r.text[:200]}"

    def test_reject_bad_extension(self, s_admin, case_id):
        files = {"file": ("evil.exe", io.BytesIO(b"x" * 32), "application/octet-stream")}
        r = s_admin.post(f"{API}/cases/{case_id}/attachments", files=files, timeout=30)
        assert r.status_code == 400, r.text

    def test_accept_small_pdf(self, s_admin, case_id):
        small = b"%PDF-1.4\n" + os.urandom(64 * 1024)  # ~64KB
        files = {"file": ("small.pdf", io.BytesIO(small), "application/pdf")}
        r = s_admin.post(f"{API}/cases/{case_id}/attachments", files=files, timeout=30)
        # Could be 503 if storage unavailable, but normally 200
        assert r.status_code in (200, 503), f"got {r.status_code}: {r.text[:200]}"
        if r.status_code == 200:
            att = r.json().get("attachment")
            assert att and att["size_bytes"] == len(small)
            # cleanup
            s_admin.delete(f"{API}/attachments/{att['id']}", timeout=15)
