"""Iteration 4 — Phase 4 endpoints: admin user delete, patient PATCH/DELETE,
reminders CRUD with audience scoping, follow-up notify_pharmacy, dashboards (pharmacy/pro/admin-analytics).
"""
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")
API = f"{BASE_URL}/api"

CREDS = {
    "admin1": "Password@123",
    "jyothi": "Password@123",
    "hemanth": "Password@123",
    "reception1": "Password@123",
    "pharmacy1": "Password@123",
    "pro1": "Password@123",
}


def _login(username, password):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"username": username, "password": password}, timeout=10)
    assert r.status_code == 200, f"login {username} failed: {r.status_code} {r.text}"
    body = r.json()
    token = body.get("access_token")
    assert token, "access_token missing"
    s.headers.update({"Authorization": f"Bearer {token}"})
    return s, body["user"]


@pytest.fixture(scope="module")
def sessions():
    out = {}
    for u, p in CREDS.items():
        s, info = _login(u, p)
        out[u] = {"s": s, "user": info}
    return out


@pytest.fixture(scope="module")
def doctors(sessions):
    r = sessions["admin1"]["s"].get(f"{API}/doctors", timeout=10)
    assert r.status_code == 200
    return r.json()["doctors"]


@pytest.fixture(scope="module")
def test_patient(sessions):
    """A simple patient with no cases — used for PATCH/DELETE tests."""
    r = sessions["reception1"]["s"].post(f"{API}/patients", json={
        "first_name": "TEST_R4", "last_name": f"P_{uuid.uuid4().hex[:6]}",
        "phone": "9990001111", "preferred_language": "EN", "age": 30, "gender": "MALE",
    }, timeout=10)
    assert r.status_code == 200, r.text
    return r.json()["patient"]


# ───────── ADMIN: delete user ─────────
class TestAdminUserDelete:
    def test_delete_freshly_created_user(self, sessions):
        admin_s = sessions["admin1"]["s"]
        uname = f"test_r4_{uuid.uuid4().hex[:6]}"
        r = admin_s.post(f"{API}/admin/users", json={
            "username": uname, "password": "Password@123", "name": "Test R4",
            "role": "RECEPTION",
        }, timeout=10)
        assert r.status_code == 200, r.text
        uid = r.json()["user"]["id"]

        d = admin_s.delete(f"{API}/admin/users/{uid}", timeout=10)
        assert d.status_code == 200, d.text
        assert d.json().get("ok") is True
        assert d.json().get("soft_deleted") is not True

    def test_cannot_delete_self(self, sessions):
        admin_s = sessions["admin1"]["s"]
        admin_id = sessions["admin1"]["user"]["id"]
        d = admin_s.delete(f"{API}/admin/users/{admin_id}", timeout=10)
        assert d.status_code == 400, d.text

    def test_owner_doctor_soft_delete(self, sessions):
        """Deleting jyothi (OWNER_DOCTOR) should soft-delete (deactivate) not hard delete."""
        admin_s = sessions["admin1"]["s"]
        jy_id = sessions["jyothi"]["user"]["id"]
        d = admin_s.delete(f"{API}/admin/users/{jy_id}", timeout=10)
        assert d.status_code == 200, d.text
        body = d.json()
        assert body.get("soft_deleted") is True
        # restore: re-activate jyothi so subsequent tests still work
        admin_s.patch(f"{API}/admin/users/{jy_id}", json={"active": True}, timeout=10)


# ───────── PATIENT: PATCH / DELETE ─────────
class TestPatientPatchDelete:
    def test_patch_patient(self, sessions, test_patient):
        s = sessions["reception1"]["s"]
        pid = test_patient["id"]
        new_phone = "9112233445"
        new_first = "TEST_R4_UPD"
        r = s.patch(f"{API}/patients/{pid}", json={"first_name": new_first, "phone": new_phone}, timeout=10)
        assert r.status_code == 200, r.text
        # GET verifies persistence
        g = s.get(f"{API}/patients/{pid}", timeout=10)
        assert g.status_code == 200
        body = g.json()["patient"]
        assert body["first_name"] == new_first
        assert body["phone"] == new_phone

    def test_delete_patient_no_cases(self, sessions):
        s = sessions["reception1"]["s"]
        r = s.post(f"{API}/patients", json={
            "first_name": "TEST_R4_DEL", "last_name": "NoCases",
            "phone": "9990001222", "preferred_language": "EN", "age": 22, "gender": "FEMALE",
        }, timeout=10)
        pid = r.json()["patient"]["id"]
        d = s.delete(f"{API}/patients/{pid}", timeout=10)
        assert d.status_code == 200, d.text
        g = s.get(f"{API}/patients/{pid}", timeout=10)
        assert g.status_code == 404

    def test_reception_cannot_delete_patient_with_cases(self, sessions, doctors):
        recep = sessions["reception1"]["s"]
        # create patient + case
        r = recep.post(f"{API}/patients", json={
            "first_name": "TEST_R4_WITHCASES", "last_name": "Recep",
            "phone": "9990001333", "preferred_language": "EN", "age": 40, "gender": "MALE",
        }, timeout=10)
        pid = r.json()["patient"]["id"]
        c = recep.post(f"{API}/cases", json={
            "patient_id": pid, "assigned_doctor_id": doctors[0]["id"],
            "complaint_text": "Round4 test complaint",
        }, timeout=10)
        assert c.status_code == 200, c.text
        d = recep.delete(f"{API}/patients/{pid}", timeout=10)
        assert d.status_code == 409, d.text

    def test_admin_can_delete_with_cascade(self, sessions, doctors):
        recep = sessions["reception1"]["s"]
        admin = sessions["admin1"]["s"]
        jy = sessions["jyothi"]["s"]
        # create patient + case + notes + prescription + payment + reminder
        r = recep.post(f"{API}/patients", json={
            "first_name": "TEST_R4_CASCADE", "last_name": "X",
            "phone": "9990001444", "preferred_language": "EN", "age": 50, "gender": "MALE",
        }, timeout=10)
        pid = r.json()["patient"]["id"]
        c = recep.post(f"{API}/cases", json={
            "patient_id": pid, "assigned_doctor_id": doctors[0]["id"],
            "complaint_text": "Cascade test",
        }, timeout=10)
        cid = c.json()["case"]["id"]
        jy.put(f"{API}/cases/{cid}/notes", json={
            "diagnosis_summary": "x", "sensitivity_allergies": "", "safety_notes": "",
            "suggestions": "", "additional_info": "",
        }, timeout=10)
        jy.post(f"{API}/cases/{cid}/prescription", json={
            "items": [{"medicine_name": "Arnica 30", "dose": "3 drops", "frequency": "TID", "duration_days": 7}],
            "notes_for_patient": "x", "notes_internal": "",
        }, timeout=10)
        # add reminder
        future = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
        jy.post(f"{API}/reminders", json={
            "patient_id": pid, "case_id": cid, "scheduled_at": future,
            "message": "cascade-rem", "audience": ["DOCTOR"],
        }, timeout=10)

        d = admin.delete(f"{API}/patients/{pid}", timeout=10)
        assert d.status_code == 200, d.text
        # patient gone
        assert admin.get(f"{API}/patients/{pid}", timeout=10).status_code == 404
        # case gone (admin sees all)
        assert admin.get(f"{API}/cases/{cid}", timeout=10).status_code == 404
        # reminders for that patient should be gone — list reminders and check none matches
        rl = jy.get(f"{API}/reminders", timeout=10).json()["reminders"]
        assert not any(rm.get("patient_id") == pid for rm in rl)


# ───────── REMINDERS ─────────
class TestReminders:
    @pytest.fixture(scope="class")
    def fixture_patient(self, sessions, doctors):
        recep = sessions["reception1"]["s"]
        r = recep.post(f"{API}/patients", json={
            "first_name": "TEST_R4_REM", "last_name": "X",
            "phone": "9990002000", "preferred_language": "EN", "age": 30, "gender": "MALE",
        }, timeout=10)
        pid = r.json()["patient"]["id"]
        c = recep.post(f"{API}/cases", json={
            "patient_id": pid, "assigned_doctor_id": doctors[0]["id"],
            "complaint_text": "Reminder fixture",
        }, timeout=10)
        return {"patient_id": pid, "case_id": c.json()["case"]["id"]}

    def test_create_reminder_with_audience(self, sessions, fixture_patient):
        future = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        r = sessions["jyothi"]["s"].post(f"{API}/reminders", json={
            "patient_id": fixture_patient["patient_id"],
            "case_id": fixture_patient["case_id"],
            "scheduled_at": future, "message": "Pharmacy reminder TEST_R4",
            "audience": ["DOCTOR", "PHARMACY"],
        }, timeout=10)
        assert r.status_code == 200, r.text
        rid = r.json()["reminder"]["id"]
        assert "PHARMACY" in r.json()["reminder"]["audience"]
        # Pharmacy sees it
        pharm = sessions["pharmacy1"]["s"]
        plist = pharm.get(f"{API}/reminders", timeout=10).json()["reminders"]
        assert any(x["id"] == rid for x in plist), "pharmacy1 should see PHARMACY-audience reminder"
        # store for later test
        TestReminders._pharmacy_rid = rid

    def test_pharmacy_doesnt_see_doctor_only_reminder(self, sessions, fixture_patient):
        future = (datetime.now(timezone.utc) + timedelta(hours=3)).isoformat()
        r = sessions["jyothi"]["s"].post(f"{API}/reminders", json={
            "patient_id": fixture_patient["patient_id"],
            "case_id": fixture_patient["case_id"],
            "scheduled_at": future, "message": "Doctor only TEST_R4",
            "audience": ["DOCTOR"],
        }, timeout=10)
        assert r.status_code == 200
        rid = r.json()["reminder"]["id"]
        plist = sessions["pharmacy1"]["s"].get(f"{API}/reminders", timeout=10).json()["reminders"]
        assert not any(x["id"] == rid for x in plist), "pharmacy1 should NOT see DOCTOR-only reminder"
        TestReminders._doctor_only_rid = rid

    def test_pharmacy_can_complete_pharmacy_reminder(self, sessions):
        rid = TestReminders._pharmacy_rid
        pharm = sessions["pharmacy1"]["s"]
        r = pharm.patch(f"{API}/reminders/{rid}", json={"status": "COMPLETED"}, timeout=10)
        assert r.status_code == 200, r.text
        body = r.json()["reminder"]
        assert body["status"] == "COMPLETED"
        assert body.get("completed_at")
        assert body.get("completed_by")

    def test_reception_cannot_patch_reminder(self, sessions):
        rid = TestReminders._pharmacy_rid
        r = sessions["reception1"]["s"].patch(f"{API}/reminders/{rid}", json={"status": "PENDING"}, timeout=10)
        assert r.status_code == 403, r.text

    def test_snooze_resets_status_pending(self, sessions, fixture_patient):
        future = (datetime.now(timezone.utc) + timedelta(hours=4)).isoformat()
        r = sessions["jyothi"]["s"].post(f"{API}/reminders", json={
            "patient_id": fixture_patient["patient_id"],
            "case_id": fixture_patient["case_id"],
            "scheduled_at": future, "message": "Snooze test", "audience": ["DOCTOR"],
        }, timeout=10).json()["reminder"]
        rid = r["id"]
        # mark SENT-ish via complete
        sessions["jyothi"]["s"].patch(f"{API}/reminders/{rid}", json={"status": "COMPLETED"}, timeout=10)
        snooze_iso = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        upd = sessions["jyothi"]["s"].patch(f"{API}/reminders/{rid}", json={"snooze_until": snooze_iso}, timeout=10)
        assert upd.status_code == 200, upd.text
        body = upd.json()["reminder"]
        assert body["status"] == "PENDING"
        assert body["scheduled_at"].startswith(snooze_iso[:19])

    def test_hemanth_cannot_delete_jyothi_reminder(self, sessions):
        rid = TestReminders._doctor_only_rid
        r = sessions["hemanth"]["s"].delete(f"{API}/reminders/{rid}", timeout=10)
        assert r.status_code == 403, r.text

    def test_jyothi_can_delete_her_reminder(self, sessions):
        rid = TestReminders._doctor_only_rid
        r = sessions["jyothi"]["s"].delete(f"{API}/reminders/{rid}", timeout=10)
        assert r.status_code == 200, r.text

    def test_status_query_filter(self, sessions):
        r = sessions["jyothi"]["s"].get(f"{API}/reminders?status=COMPLETED", timeout=10)
        assert r.status_code == 200
        for rm in r.json()["reminders"]:
            assert rm["status"] == "COMPLETED"


# ───────── FOLLOW-UP notify_pharmacy ─────────
class TestFollowupNotifyPharmacy:
    def test_followup_with_notify_pharmacy(self, sessions, doctors):
        recep = sessions["reception1"]["s"]
        jy = sessions["jyothi"]["s"]
        r = recep.post(f"{API}/patients", json={
            "first_name": "TEST_R4_FU", "last_name": "X",
            "phone": "9990003000", "preferred_language": "EN", "age": 35, "gender": "MALE",
        }, timeout=10)
        pid = r.json()["patient"]["id"]
        c = recep.post(f"{API}/cases", json={
            "patient_id": pid, "assigned_doctor_id": doctors[0]["id"],
            "complaint_text": "Followup notify_pharmacy test",
        }, timeout=10)
        cid = c.json()["case"]["id"]
        future = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
        f = jy.post(f"{API}/cases/{cid}/followup", json={
            "next_followup_at": future, "followup_note": "TEST_R4_FU pharmacy",
            "notify_pharmacy": True,
        }, timeout=10)
        assert f.status_code == 200, f.text
        plist = sessions["pharmacy1"]["s"].get(f"{API}/reminders", timeout=10).json()["reminders"]
        assert any(x.get("case_id") == cid for x in plist), \
            "Pharmacy should see follow-up reminder when notify_pharmacy=True"


# ───────── DASHBOARDS ─────────
class TestDashboards:
    def test_pharmacy_dashboard(self, sessions):
        r = sessions["pharmacy1"]["s"].get(f"{API}/pharmacy/dashboard", timeout=10)
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ("pending_dispense_count", "dispensed_today_count",
                  "medicine_revenue_today", "pharmacy_reminders_pending"):
            assert k in body, f"missing key {k}"

    def test_pharmacy_dashboard_forbidden_for_reception(self, sessions):
        r = sessions["reception1"]["s"].get(f"{API}/pharmacy/dashboard", timeout=10)
        assert r.status_code == 403, r.text

    def test_pro_dashboard(self, sessions):
        r = sessions["pro1"]["s"].get(f"{API}/pro/dashboard", timeout=10)
        assert r.status_code == 200, r.text
        body = r.json()
        assert isinstance(body["today_revenue"], (int, float))
        trend = body["revenue_trend_7d"]
        assert isinstance(trend, list) and len(trend) == 7
        for item in trend:
            assert "date" in item and "label" in item and "revenue" in item
        assert isinstance(body["followups_today"], list)
        assert isinstance(body["by_mode_today"], dict)

    def test_pro_dashboard_forbidden_pharmacy(self, sessions):
        r = sessions["pharmacy1"]["s"].get(f"{API}/pro/dashboard", timeout=10)
        assert r.status_code == 403, r.text

    def test_admin_analytics_as_admin(self, sessions):
        r = sessions["admin1"]["s"].get(f"{API}/admin/analytics", timeout=10)
        assert r.status_code == 200, r.text
        body = r.json()
        assert isinstance(body["case_trend_30d"], list) and len(body["case_trend_30d"]) == 30
        # label like "20 Jun"
        import re
        label = body["case_trend_30d"][0]["label"]
        assert re.match(r"^\d{1,2} [A-Z][a-z]{2}$", label), f"bad label format: {label}"
        assert isinstance(body["logins_by_role_30d"], dict)
        assert isinstance(body["top_complaints"], list)
        assert isinstance(body["avg_turnaround_minutes"], (int, float))

    def test_admin_analytics_owner_doctor_allowed(self, sessions):
        r = sessions["jyothi"]["s"].get(f"{API}/admin/analytics", timeout=10)
        assert r.status_code == 200, r.text

    def test_admin_analytics_reception_forbidden(self, sessions):
        r = sessions["reception1"]["s"].get(f"{API}/admin/analytics", timeout=10)
        assert r.status_code == 403, r.text

    def test_pro_dashboard_trend_last_is_today_ist(self, sessions):
        r = sessions["pro1"]["s"].get(f"{API}/pro/dashboard", timeout=10).json()
        trend = r["revenue_trend_7d"]
        ist = timezone(timedelta(hours=5, minutes=30))
        today_label = datetime.now(ist).strftime("%a")
        assert trend[-1]["label"] == today_label, f"last item should be today's IST weekday {today_label}, got {trend[-1]['label']}"
