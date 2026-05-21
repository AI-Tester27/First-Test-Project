# Sparsa Homeoclinic — PRD

## Original Problem Statement
Internal clinic management web app for **Sparsa Homeoclinic** (homeopathy clinic, 5 PCs on LAN).
Workflow: **Reception → Doctor → Pharmacy → PRO/Billing**.
Roles: ADMIN (full access), OWNER_DOCTOR (Jyothi — all cases), DOCTOR (Hemanth — own only), RECEPTION, PHARMACY, PRO.

## Stack (adapted)
React + FastAPI + MongoDB (original spec was Laravel + MySQL).

## What's Implemented

### v1 — 2026-02-21
- JWT (httpOnly cookie) auth + bcrypt; 6 seeded users.
- Patients: auto-generated `SPARSA-XXXXXX` uid, search.
- Cases: full workflow status engine.
- Clinical notes + versioned prescriptions (pharmacy can edit → new version).
- Pharmacy dispense → auto READY_FOR_BILLING.
- Billing + bilingual EN+Telugu printable receipt (`SPH-RC-XXXXXX`).
- On-screen follow-up reminders.
- AI assist (3 actions, Claude Sonnet 4.5 via Emergent LLM key).
- Admin: user mgmt, audit log, stats.
- ✅ 33/33 backend tests pass.

### v2 — 2026-02-21 (same day, extended)
- **File attachments** via Emergent Object Storage — jpg/png/pdf, max 10MB. Soft-delete pattern, RBAC-gated download. New "Attachments" tab in Doctor case detail.
- **Patient visit timeline** — full history (cases + notes + prescriptions + payments + attachments count). New page at `/reception/patients/:id/timeline`.
- **5 CSV exports** for admin — patients, cases, payments, prescriptions, audit log. New Admin Exports page.
- **WhatsApp + SMS reminders** — full Twilio + Meta WhatsApp Cloud API integration with graceful `PROVIDER_NOT_CONFIGURED` fallback. Background scheduler runs every 60s. Bilingual EN/Telugu reminder body. *(keys to be added in backend/.env when ready — see env keys below)*
- **Daily mongodump backup script** at `/app/scripts/backup.sh` (+ restore.sh + README).
- ✅ 53/53 backend tests pass (20 new + 33 regression).

## How to enable WhatsApp + SMS reminders
Add to `/app/backend/.env` and restart backend:
```
WHATSAPP_PHONE_NUMBER_ID=...
WHATSAPP_ACCESS_TOKEN=...
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_FROM=+1...
```
- Get WhatsApp keys: https://developers.facebook.com/apps → WhatsApp → API Setup
- Get Twilio keys: https://console.twilio.com

When configured, the scheduler will try WhatsApp first, fall back to SMS, and mark reminders SENT/FAILED.

## Endpoints (new in v2)
- `POST /api/cases/{id}/attachments` (multipart)
- `GET  /api/cases/{id}/attachments`
- `GET  /api/attachments/{id}/download`
- `DELETE /api/attachments/{id}`
- `GET  /api/patients/{id}/timeline`
- `GET  /api/admin/export/{patients|cases|payments|prescriptions|audit}.csv`
- `POST /api/reminders/{id}/send-now`
- `GET  /api/health` now includes provider status

## Backlog
### P1
- Brute-force lockout on `/api/auth/login` (5 failed = 15min).
- Split server.py into routers (auth/patients/cases/pharmacy/payments/ai/admin/attachments/exports) — currently 1154 lines.
- Switch `requests` to `httpx.AsyncClient` in messaging.py to avoid blocking the event loop once real keys are configured.
- Patient timeline: replace N+1 reads with `$lookup` aggregation.

### P2
- Hard-delete reaper for orphaned object storage files (currently soft-delete only).
- Streaming CSV cursor for very large exports (currently loads up to 100k rows in memory).
- Configurable reminder templates (admin UI) + bilingual variants.
- Multi-visit timeline filtering & analytics.

## Next Action Items
- Add Twilio + WhatsApp Cloud API keys to backend/.env when ready.
- Test the daily backup script with cron / Task Scheduler on the actual clinic PC.
- Consider splitting server.py into routers before further growth.
