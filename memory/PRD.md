# Sparsa Homeoclinic — PRD

## Original Problem Statement
Internal clinic management web app for **Sparsa Homeoclinic** (homeopathy clinic, 5 PCs on LAN).
Workflow: **Reception → Doctor → Pharmacy → PRO/Billing**.
Roles: ADMIN, OWNER_DOCTOR (Jyothi — all cases), DOCTOR (Hemanth — own only), RECEPTION, PHARMACY, PRO.

## Stack (adapted)
React + FastAPI + MongoDB (original spec was Laravel + MySQL).

## What's Implemented

### v1 — 2026-02-21
- JWT (httpOnly cookie) auth + bcrypt; 6 seeded users.
- Patients (auto `SPARSA-XXXXXX` uid), cases workflow, clinical notes, versioned prescriptions, pharmacy dispense → auto-billing, payments, EN+Telugu printable receipt, on-screen reminders, per-case AI assist (summarize/advice/instructions), admin (users + audit + stats).
- ✅ 33/33 backend tests.

### v2 — 2026-02-21
- File attachments via Emergent Object Storage (jpg/png/pdf, 10MB).
- Patient visit timeline.
- 5 CSV exports.
- Twilio + WhatsApp Cloud API with graceful `PROVIDER_NOT_CONFIGURED` fallback + background scheduler.
- Daily `mongodump` backup + restore scripts.
- ✅ 53/53 backend tests.

### v3 — 2026-02-21 (refactor + AI recap)
- **Refactor:** server.py 1154 lines → 64-line shell + `core.py` + `models.py` + `seed.py` + `routers/` (auth, patients, cases, pharmacy, payments, attachments, reminders, ai, exports, admin). Every endpoint path preserved; zero behavioral change for clients.
- **AI Visit Recap:** `POST /api/patients/{id}/ai/recap` produces a 5-line briefing from full visit history (pattern · what helped · red flags · allergies · today's focus). Respects doctor scope (Hemanth sees only own cases). Button surfaces on Patient Timeline page.
- **Backup walkthrough:** `/app/scripts/README.md` now includes step-by-step cron (Linux) + Task Scheduler (Windows) instructions, off-site sync recommendations, restore verification procedure, and troubleshooting table.
- ✅ 71/71 backend tests pass (33 iter1 + 20 iter2 + 18 iter3).

## How to enable WhatsApp + SMS reminders
Add to `/app/backend/.env` and restart backend:
```
WHATSAPP_PHONE_NUMBER_ID=...
WHATSAPP_ACCESS_TOKEN=...
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_FROM=+1...
```

## Schedule the daily backup
Linux: `crontab -e` then `0 23 * * * /app/scripts/backup.sh >> /var/log/sparsa-backup.log 2>&1`
Windows: Task Scheduler → Daily 23:00 → run `bash.exe -c "/c/app/scripts/backup.sh"`
Full walkthrough in `/app/scripts/README.md`.

## Backlog
### P1
- Switch `requests` → `httpx.AsyncClient` in messaging.py (once real Twilio/WA keys configured).
- Streaming CSV cursor for very large exports.
- Hard-delete reaper for orphaned object storage files.
- Brute-force lockout on `/api/auth/login`.

### P2
- N+1 query optimization in patient timeline (replace with `$lookup` aggregate).
- Configurable reminder templates in admin UI.
- AI Recap: truncation flag when patient has >200 cases.
- Multi-visit timeline filtering & analytics charts.

## Next Action Items
- Paste Twilio + WhatsApp keys into backend/.env when ready.
- Schedule `/app/scripts/backup.sh` on the clinic server PC (cron / Task Scheduler).
