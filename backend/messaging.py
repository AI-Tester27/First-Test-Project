"""WhatsApp Cloud API + Twilio SMS providers for follow-up reminders.

Settings precedence: runtime DB-backed admin settings → environment variables.
Admins can update keys at runtime via /api/admin/messaging-settings without
restarting the backend. Missing creds → providers return (False, PROVIDER_NOT_CONFIGURED)
so the app keeps running and reminders are marked FAILED with that reason.
"""
import os
import logging
import re
import time
import requests

log = logging.getLogger(__name__)

# ── Runtime settings cache (refreshed every 30s by the loader below) ─────────
_cache: dict = {}
_cache_at: float = 0.0
_CACHE_TTL = 30.0


def _get(key: str) -> str | None:
    """Return runtime DB setting if present (string, non-empty), else env var."""
    val = _cache.get(key)
    if val:
        return val
    return os.environ.get(key) or None


async def refresh_messaging_cache(db) -> None:
    """Called by /admin/messaging-settings writes and on startup to refresh."""
    global _cache, _cache_at
    doc = await db.settings.find_one({"_id": "messaging"}) or {}
    _cache = {k: v for k, v in doc.items() if k != "_id" and v}
    _cache_at = time.time()


async def _maybe_refresh(db) -> None:
    if time.time() - _cache_at > _CACHE_TTL:
        await refresh_messaging_cache(db)


def _normalize_phone(phone: str) -> str:
    digits = re.sub(r"[^0-9]", "", phone or "")
    if len(digits) == 10:  # assume India
        digits = "91" + digits
    return digits


def send_whatsapp(to_phone: str, message: str) -> tuple[bool, str]:
    phone_id = _get("WHATSAPP_PHONE_NUMBER_ID")
    token = _get("WHATSAPP_ACCESS_TOKEN")
    version = _get("WHATSAPP_API_VERSION") or "v19.0"
    if not (phone_id and token):
        return False, "PROVIDER_NOT_CONFIGURED"
    to = _normalize_phone(to_phone)
    try:
        r = requests.post(
            f"https://graph.facebook.com/{version}/{phone_id}/messages",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": message}},
            timeout=15,
        )
        if r.ok:
            return True, "OK"
        log.error("WhatsApp send failed %s %s", r.status_code, r.text[:200])
        return False, f"HTTP {r.status_code}: {r.text[:120]}"
    except Exception as e:
        log.exception("WhatsApp exception")
        return False, str(e)[:160]


def send_sms(to_phone: str, message: str) -> tuple[bool, str]:
    sid = _get("TWILIO_ACCOUNT_SID")
    token = _get("TWILIO_AUTH_TOKEN")
    from_num = _get("TWILIO_FROM")
    if not (sid and token and from_num):
        return False, "PROVIDER_NOT_CONFIGURED"
    to = "+" + _normalize_phone(to_phone)
    try:
        r = requests.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
            auth=(sid, token),
            data={"From": from_num, "To": to, "Body": message},
            timeout=15,
        )
        if r.ok:
            return True, "OK"
        log.error("Twilio send failed %s %s", r.status_code, r.text[:200])
        return False, f"HTTP {r.status_code}: {r.text[:120]}"
    except Exception as e:
        log.exception("Twilio exception")
        return False, str(e)[:160]


def provider_status() -> dict:
    return {
        "whatsapp": bool(_get("WHATSAPP_PHONE_NUMBER_ID") and _get("WHATSAPP_ACCESS_TOKEN")),
        "sms": bool(_get("TWILIO_ACCOUNT_SID") and _get("TWILIO_AUTH_TOKEN") and _get("TWILIO_FROM")),
    }


def provider_source() -> dict:
    """Tell admins where each provider's creds come from for the settings UI."""
    def src(*keys: str) -> str:
        if all(_cache.get(k) for k in keys):
            return "db"
        if all(os.environ.get(k) for k in keys):
            return "env"
        if any(_cache.get(k) or os.environ.get(k) for k in keys):
            return "partial"
        return "none"
    return {
        "whatsapp": src("WHATSAPP_PHONE_NUMBER_ID", "WHATSAPP_ACCESS_TOKEN"),
        "sms": src("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM"),
    }
