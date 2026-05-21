"""WhatsApp Cloud API + Twilio SMS providers for follow-up reminders.

If credentials are missing the providers return False and the reminder is
marked FAILED with reason PROVIDER_NOT_CONFIGURED, so the app keeps running.
Drop the keys into backend/.env and restart — no code change required.
"""
import os
import logging
import re
import requests

log = logging.getLogger(__name__)


def _normalize_phone(phone: str) -> str:
    digits = re.sub(r"[^0-9]", "", phone or "")
    if len(digits) == 10:  # assume India
        digits = "91" + digits
    return digits


def send_whatsapp(to_phone: str, message: str) -> tuple[bool, str]:
    phone_id = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")
    token = os.environ.get("WHATSAPP_ACCESS_TOKEN")
    version = os.environ.get("WHATSAPP_API_VERSION", "v19.0")
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
    sid = os.environ.get("TWILIO_ACCOUNT_SID")
    token = os.environ.get("TWILIO_AUTH_TOKEN")
    from_num = os.environ.get("TWILIO_FROM")
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
        "whatsapp": bool(os.environ.get("WHATSAPP_PHONE_NUMBER_ID") and os.environ.get("WHATSAPP_ACCESS_TOKEN")),
        "sms": bool(os.environ.get("TWILIO_ACCOUNT_SID") and os.environ.get("TWILIO_AUTH_TOKEN") and os.environ.get("TWILIO_FROM")),
    }
