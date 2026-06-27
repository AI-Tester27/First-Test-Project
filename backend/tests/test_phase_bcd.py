"""Phase B / C / D backend tests for Sparsa Homeo Care.

Phase B: GET /api/patients RBAC for DOCTOR
Phase C: PRO financial-search, PAYMENT_PROOF attachments, pro/analytics
Phase D: AI recap brief vs detailed, admin password reset
"""
import io
import os
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
    """Return {'jyothi': <doctor_id>, 'hemanth': <doctor_id>}."""
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
    assert "jyothi" in out and "hemanth" in out, f"could not map doctors: {docs}"
    return out


@pytest.fixture(scope="module")
def seed_data(reception, doctor_ids):
    """Create 2 patients: one for Hemanth, one for Jyothi. Return {hemanth_pid, jyothi_pid, hemanth_cid, jyothi_cid}."""
    out = {}
    # Hemanth's patient
    r1 = reception.post(f"{API}/patients/fir", json={
        "first_name": "TEST_BCD_Hpatient", "last_name": "X", "gender": "MALE",
        "age": 30, "phone": "9999000111", "preferred_language": "EN",
        "height_cm": 170, "weight_kg": 70,
        "consulting_doctor_id": doctor_ids["hemanth"],
        "chief_complaint": "Test cough for Hemanth",
        "visit_type": "WALK_IN",
    }, timeout=15)
    assert r1.status_code == 200, r1.text
    out["hemanth_pid"] = r1.json()["patient"]["id"]
    out["hemanth_cid"] = r1.json()["case"]["id"]
    # Jyothi's patient
    r2 = reception.post(f"{API}/patients/fir", json={
        "first_name": "TEST_BCD_Jpatient", "last_name": "Y", "gender": "FEMALE",
        "age": 40, "phone": "9999000222", "preferred_language": "EN",
        "consulting_doctor_id": doctor_ids["jyothi"],
        "chief_complaint": "Test cold for Jyothi",
        "visit_type": "WALK_IN",
    }, timeout=15)
    assert r2.status_code == 200, r2.text
    out["jyothi_pid"] = r2.json()["patient"]["id"]
    out["jyothi_cid"] = r2.json()["case"]["id"]
    return out


# ─────────────────────────── Phase B: RBAC on /patients ───────────────────────────
class TestPhaseB_PatientsRBAC:
    def test_doctor_sees_only_own_patients(self, hemanth, seed_data):
        r = hemanth.get(f"{API}/patients?search=TEST_BCD_", timeout=15)
        assert r.status_code == 200
        ids = {p["id"] for p in r.json()["patients"]}
        assert seed_data["hemanth_pid"] in ids, "Hemanth must see his own assigned patient"
        assert seed_data["jyothi_pid"] not in ids, "Hemanth must NOT see Jyothi's patient"

    def test_owner_doctor_sees_all(self, jyothi, seed_data):
        r = jyothi.get(f"{API}/patients?search=TEST_BCD_", timeout=15)
        assert r.status_code == 200
        ids = {p["id"] for p in r.json()["patients"]}
        assert seed_data["hemanth_pid"] in ids
        assert seed_data["jyothi_pid"] in ids

    def test_admin_sees_all(self, admin, seed_data):
        r = admin.get(f"{API}/patients?search=TEST_BCD_", timeout=15)
        assert r.status_code == 200
        ids = {p["id"] for p in r.json()["patients"]}
        assert seed_data["hemanth_pid"] in ids
        assert seed_data["jyothi_pid"] in ids

    def test_reception_sees_all(self, reception, seed_data):
        r = reception.get(f"{API}/patients?search=TEST_BCD_", timeout=15)
        assert r.status_code == 200
        ids = {p["id"] for p in r.json()["patients"]}
        assert seed_data["hemanth_pid"] in ids
        assert seed_data["jyothi_pid"] in ids

    def test_pharmacy_forbidden(self, pharmacy):
        r = pharmacy.get(f"{API}/patients?search=TEST_BCD_", timeout=15)
        assert r.status_code == 403

    def test_pro_forbidden(self, pro):
        r = pro.get(f"{API}/patients?search=TEST_BCD_", timeout=15)
        assert r.status_code == 403


# ─────────────────────────── Phase C: PRO financial-search ───────────────────────────
class TestPhaseC_FinancialSearch:
    def test_pro_can_search(self, pro, seed_data):
        r = pro.get(f"{API}/pro/financial-search?q=TEST_BCD_", timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "results" in body
        ids = {x["patient"]["id"] for x in body["results"]}
        assert seed_data["hemanth_pid"] in ids or seed_data["jyothi_pid"] in ids
        for res in body["results"]:
            assert "total_billed" in res
            assert "total_paid" in res
            assert "outstanding" in res
            assert "visits_count" in res
            assert isinstance(res["visits"], list)

    def test_q_too_short(self, pro):
        r = pro.get(f"{API}/pro/financial-search?q=a", timeout=15)
        assert r.status_code == 400

    def test_q_missing(self, pro):
        r = pro.get(f"{API}/pro/financial-search", timeout=15)
        assert r.status_code == 400

    def test_owner_doctor_allowed(self, jyothi):
        r = jyothi.get(f"{API}/pro/financial-search?q=TEST_BCD_", timeout=15)
        assert r.status_code == 200

    def test_admin_allowed(self, admin):
        r = admin.get(f"{API}/pro/financial-search?q=TEST_BCD_", timeout=15)
        assert r.status_code == 200

    def test_doctor_forbidden(self, hemanth):
        r = hemanth.get(f"{API}/pro/financial-search?q=TEST_BCD_", timeout=15)
        assert r.status_code == 403

    def test_reception_forbidden(self, reception):
        r = reception.get(f"{API}/pro/financial-search?q=TEST_BCD_", timeout=15)
        assert r.status_code == 403

    def test_pharmacy_forbidden(self, pharmacy):
        r = pharmacy.get(f"{API}/pro/financial-search?q=TEST_BCD_", timeout=15)
        assert r.status_code == 403


# ─────────────────────────── Phase C: PAYMENT_PROOF attachments ───────────────────────────
_TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08"
    b"\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xcf\xc0\x00"
    b"\x00\x00\x03\x00\x01\xc6\xc7\xa4\x1f\x00\x00\x00\x00IEND\xaeB`\x82"
)


class TestPhaseC_PaymentProof:
    def test_pro_uploads_payment_proof(self, pro, seed_data):
        files = {"file": ("proof.png", io.BytesIO(_TINY_PNG), "image/png")}
        data = {"kind": "PAYMENT_PROOF"}
        r = pro.post(f"{API}/cases/{seed_data['jyothi_cid']}/attachments", files=files, data=data, timeout=20)
        assert r.status_code == 200, r.text
        assert r.json()["attachment"]["kind"] == "PAYMENT_PROOF"

    def test_pro_cannot_upload_general(self, pro, seed_data):
        files = {"file": ("g.png", io.BytesIO(_TINY_PNG), "image/png")}
        data = {"kind": "GENERAL"}
        r = pro.post(f"{API}/cases/{seed_data['jyothi_cid']}/attachments", files=files, data=data, timeout=20)
        assert r.status_code == 403

    def test_reception_general_default(self, reception, seed_data):
        files = {"file": ("g.png", io.BytesIO(_TINY_PNG), "image/png")}
        r = reception.post(f"{API}/cases/{seed_data['jyothi_cid']}/attachments", files=files, timeout=20)
        assert r.status_code == 200
        assert r.json()["attachment"]["kind"] == "GENERAL"

    def test_filter_by_kind(self, pro, seed_data):
        r = pro.get(f"{API}/cases/{seed_data['jyothi_cid']}/attachments?kind=PAYMENT_PROOF", timeout=15)
        assert r.status_code == 200
        kinds = {a["kind"] for a in r.json()["attachments"]}
        assert kinds == {"PAYMENT_PROOF"} or len(kinds) == 0

    def test_invalid_kind_filter(self, pro, seed_data):
        r = pro.get(f"{API}/cases/{seed_data['jyothi_cid']}/attachments?kind=BOGUS", timeout=15)
        assert r.status_code == 400

    def test_invalid_kind_upload(self, reception, seed_data):
        files = {"file": ("g.png", io.BytesIO(_TINY_PNG), "image/png")}
        data = {"kind": "BOGUS"}
        r = reception.post(f"{API}/cases/{seed_data['jyothi_cid']}/attachments", files=files, data=data, timeout=20)
        assert r.status_code == 400


# ─────────────────────────── Phase C: /pro/analytics ───────────────────────────
class TestPhaseC_Analytics:
    def _validate_shape(self, body):
        for key in ("patient_metrics", "visit_metrics", "revenue_metrics", "operational_metrics", "financial_metrics"):
            assert key in body, f"missing {key}"
        pm = body["patient_metrics"]
        for k in ("total", "new_today", "new_7d", "new_30d", "by_gender", "by_age_group", "age_group_order", "sources_30d"):
            assert k in pm, f"patient_metrics missing {k}"
        rm = body["revenue_metrics"]
        assert "trend_30d" in rm
        assert len(rm["trend_30d"]) == 30
        assert "by_mode_30d" in rm
        assert "consult_vs_medicine_30d" in rm
        om = body["operational_metrics"]
        assert "avg_turnaround_minutes" in om
        assert "closed_cases_30d" in om

    def test_pro_allowed(self, pro):
        r = pro.get(f"{API}/pro/analytics", timeout=20)
        assert r.status_code == 200, r.text
        self._validate_shape(r.json())

    def test_owner_doctor_allowed(self, jyothi):
        r = jyothi.get(f"{API}/pro/analytics", timeout=20)
        assert r.status_code == 200
        self._validate_shape(r.json())

    def test_admin_allowed(self, admin):
        r = admin.get(f"{API}/pro/analytics", timeout=20)
        assert r.status_code == 200

    def test_doctor_forbidden(self, hemanth):
        r = hemanth.get(f"{API}/pro/analytics", timeout=20)
        assert r.status_code == 403

    def test_reception_forbidden(self, reception):
        r = reception.get(f"{API}/pro/analytics", timeout=20)
        assert r.status_code == 403

    def test_pharmacy_forbidden(self, pharmacy):
        r = pharmacy.get(f"{API}/pro/analytics", timeout=20)
        assert r.status_code == 403


# ─────────────────────────── Phase D: AI recap brief vs detailed ───────────────────────────
class TestPhaseD_AIRecap:
    def test_brief_mode_default(self, jyothi, seed_data):
        # Default no mode → brief
        r = jyothi.post(f"{API}/patients/{seed_data['jyothi_pid']}/ai/recap", timeout=60)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["mode"] == "brief"
        assert isinstance(body["result"], str) and len(body["result"]) > 10

    def test_brief_mode_explicit(self, jyothi, seed_data):
        r = jyothi.post(f"{API}/patients/{seed_data['jyothi_pid']}/ai/recap?mode=brief", timeout=60)
        assert r.status_code == 200
        assert r.json()["mode"] == "brief"

    def test_detailed_mode_owner(self, jyothi, seed_data):
        r = jyothi.post(f"{API}/patients/{seed_data['jyothi_pid']}/ai/recap?mode=detailed", timeout=60)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["mode"] == "detailed"
        result = body["result"]
        # Validate markdown structure
        assert "## 1." in result or "##1." in result, "missing section 1"
        assert "Disclaimer" in result, "missing disclaimer section"
        assert "Tincture" in result or "tincture" in result, "missing tincture section"

    def test_detailed_mode_doctor_forbidden(self, hemanth, seed_data):
        r = hemanth.post(f"{API}/patients/{seed_data['hemanth_pid']}/ai/recap?mode=detailed", timeout=15)
        assert r.status_code == 403

    def test_invalid_mode(self, jyothi, seed_data):
        r = jyothi.post(f"{API}/patients/{seed_data['jyothi_pid']}/ai/recap?mode=bogus", timeout=15)
        assert r.status_code == 400


# ─────────────────────────── Phase D: Admin password reset ───────────────────────────
class TestPhaseD_PasswordReset:
    @pytest.fixture(scope="class")
    def temp_user(self, admin):
        # Create a throwaway user
        r = admin.post(f"{API}/admin/users", json={
            "username": "test_pwd_reset_user",
            "name": "TEST PwdReset",
            "password": "OldPass@1234",
            "role": "RECEPTION",
        }, timeout=15)
        if r.status_code == 400 and "exists" in r.text.lower():
            # already exists from previous run — look it up + reset to known password
            lr = admin.get(f"{API}/admin/users", timeout=15)
            for u in lr.json()["users"]:
                if u["username"] == "test_pwd_reset_user":
                    admin.patch(f"{API}/admin/users/{u['id']}", json={"password": "OldPass@1234"}, timeout=15)
                    return u
            pytest.fail("user exists but cannot be retrieved")
        assert r.status_code == 200, r.text
        return r.json()["user"]

    def test_reset_password_and_login(self, admin, temp_user):
        # Reset
        r = admin.patch(f"{API}/admin/users/{temp_user['id']}", json={"password": "NewPass@9999"}, timeout=15)
        assert r.status_code == 200, r.text
        # Old should fail
        s = requests.Session()
        old = s.post(f"{API}/auth/login", json={"username": "test_pwd_reset_user", "password": "OldPass@1234"}, timeout=15)
        assert old.status_code in (401, 400, 403)
        # New should succeed
        new = s.post(f"{API}/auth/login", json={"username": "test_pwd_reset_user", "password": "NewPass@9999"}, timeout=15)
        assert new.status_code == 200, new.text

    def test_non_admin_forbidden(self, reception, temp_user):
        r = reception.patch(f"{API}/admin/users/{temp_user['id']}", json={"password": "Whatever@1234"}, timeout=15)
        assert r.status_code == 403

    def test_short_password_rejected(self, admin, temp_user):
        # NB: backend model has no min_length on password — this may currently return 200.
        # Spec says <8 chars should be 422 / 400. Failure here = backend code gap.
        r = admin.patch(f"{API}/admin/users/{temp_user['id']}", json={"password": "short"}, timeout=15)
        assert r.status_code in (400, 422), f"expected 400/422 for short password, got {r.status_code}"
