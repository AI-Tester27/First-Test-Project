"""AI settings tests: admin-managed provider keys, model selection, RBAC, validation."""
import os

import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://simple-enterprise-ai.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"


def _login(username: str, password: str) -> requests.Session:
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"username": username, "password": password}, timeout=20)
    assert r.status_code == 200, f"login {username} failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def s_admin():
    return _login("admin1", "Password@123")


@pytest.fixture(scope="module")
def s_reception():
    return _login("reception1", "Password@123")


def test_get_ai_settings_shape(s_admin):
    r = s_admin.get(f"{API}/admin/ai-settings", timeout=20)
    assert r.status_code == 200
    d = r.json()
    for k in ("stored", "active_provider", "active_model", "key_source", "keys_configured", "models"):
        assert k in d
    assert set(d["models"].keys()) == {"anthropic", "openai", "gemini"}
    assert d["key_source"] in ("own", "emergent")


def test_rbac_non_admin_forbidden(s_reception):
    r = s_reception.get(f"{API}/admin/ai-settings", timeout=20)
    assert r.status_code == 403


def test_invalid_provider_rejected(s_admin):
    r = s_admin.post(f"{API}/admin/ai-settings", json={"AI_PROVIDER": "bogus"}, timeout=20)
    assert r.status_code == 400


def test_invalid_model_rejected(s_admin):
    r = s_admin.post(f"{API}/admin/ai-settings", json={"AI_MODEL": "bogus-model"}, timeout=20)
    assert r.status_code == 400


def test_save_key_switch_provider_and_clear(s_admin):
    # Save a fake key + switch provider/model
    r = s_admin.post(f"{API}/admin/ai-settings", json={
        "OPENAI_API_KEY": "sk-fake-test-key",
        "AI_PROVIDER": "openai",
        "AI_MODEL": "gpt-5.4",
    }, timeout=20)
    assert r.status_code == 200
    d = r.json()
    assert d["active_provider"] == "openai"
    assert d["active_model"] == "gpt-5.4"
    assert d["key_source"] == "own"
    assert d["keys_configured"]["openai"] is True

    # Stored key comes back masked, never in full
    g = s_admin.get(f"{API}/admin/ai-settings", timeout=20).json()
    masked = g["stored"].get("OPENAI_API_KEY", "")
    assert "sk-fake-test-key" not in masked and "•" in masked

    # Clear key and restore defaults
    r = s_admin.post(f"{API}/admin/ai-settings", json={
        "OPENAI_API_KEY": "__CLEAR__",
        "AI_PROVIDER": "anthropic",
        "AI_MODEL": "claude-sonnet-4-5-20250929",
    }, timeout=20)
    assert r.status_code == 200
    d = r.json()
    assert d["key_source"] == "emergent"
    assert d["keys_configured"]["openai"] is False


def test_test_endpoint_requires_key(s_admin):
    r = s_admin.post(f"{API}/admin/ai-settings/test", json={"provider": "openai"}, timeout=20)
    assert r.status_code == 400


def test_test_endpoint_invalid_key_returns_ok_false(s_admin):
    r = s_admin.post(f"{API}/admin/ai-settings/test",
                     json={"provider": "anthropic", "api_key": "sk-ant-invalid"}, timeout=60)
    assert r.status_code == 200
    assert r.json()["ok"] is False
