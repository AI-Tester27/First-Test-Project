# Sparsa Homeoclinic — PRD

## Original Problem Statement
Internal clinic management for **Sparsa Homeoclinic** (homeopathy clinic, 5 PCs on LAN).
Workflow: **Reception → Doctor → Pharmacy → PRO/Billing**.
Roles: ADMIN, OWNER_DOCTOR (Jyothi — all cases), DOCTOR (Hemanth — own only), RECEPTION, PHARMACY, PRO.

## Stack
React + FastAPI + MongoDB (original spec was Laravel + MySQL).

## What's Implemented

### v1 (33 tests pass)
JWT auth · roles · patient UIDs · case workflow · clinical notes · versioned prescriptions · pharmacy dispense · billing · bilingual EN/Telugu receipt · on-screen reminders · per-case AI assist · admin (users/audit/stats).

### v2 (53 tests pass)
File attachments (Emergent Object Storage, 10MB jpg/png/pdf) · patient timeline · 5 CSV exports · Twilio + WhatsApp Cloud API (graceful PROVIDER_NOT_CONFIGURED fallback + background scheduler) · mongodump backup/restore scripts.

### v3 (71 tests pass)
Refactored 1154-line server.py into modular routers (core.py + models.py + 10 routers + seed.py + 64-line server.py) · AI Visit Recap (5-line briefing from full patient history) · full step-by-step cron/Task Scheduler walkthrough in scripts/README.md.

### v4 (97 tests pass — current build, 2026-06-20)
- **Past Visit migration** — `POST /api/patients/{id}/past-visit` creates backdated CLOSED cases. UI form on patient timeline.
- **Google Docs paste import** — `POST /api/ai/parse-visit-notes` uses Claude Sonnet 4.5 to extract structured visit data from free-form notes; pre-fills the past-visit form.
- **Billing closure UX** — green success card after PAID, with Print Receipt / Patient Timeline / Back to Queue actions; payment form goes read-only.
- **Branding cleanup** — browser title "Sparsa Homeoclinic", removed demo-creds block from login.
- **Admin user CRUD** — `DELETE /api/admin/users/{id}` (self-delete blocked, OWNER_DOCTOR soft-deactivated).
- **Patient edit/delete** — reception/owner can edit; reception can delete cases-free patients; admin can hard-delete with cascade (clinical_notes, prescriptions, pharmacy_dispense, payments, reminders, attachments soft-deleted).
- **Admin Analytics dashboard** — 30-day cases+revenue chart, logins-by-role, top complaints, average turnaround time.
- **Pharmacy Dashboard** — KPIs (pending dispense, today's dispensed count, medicine revenue today, active reminders) + reminders side panel.
- **PRO Dashboard** — today/total revenue, outstanding, pending bills, 7-day revenue trend chart, mode breakdown, follow-ups due today.
- **Pharmacy Reminders module** — doctor's followups with `notify_pharmacy=true` appear on pharmacy dashboard + dedicated `/pharmacy/reminders` page with PENDING/COMPLETED/SENT tabs and Mark Complete action.
- **Doctor Reminders enhanced** — tabs (PENDING/SENT/COMPLETED/FAILED), search, mark complete, snooze (datetime picker), send now, delete.
- **IST everywhere** — all reminder/timeline/dashboard times shown in Asia/Kolkata. New `fmtIST` + `istLocalToUtcISO` helpers; backend day-bounds calculated in IST.
- **PRO privacy fix** — clinician-written reminder notes hidden from PRO followups feed.
- ✅ 98/98 backend tests pass with iteration_5 fixes verified.

## Bring-your-own-key for AI (status)
Currently uses Emergent Universal LLM key (Claude Sonnet 4.5). Provider abstraction is in `routers/ai.py::_call_llm`. To swap to direct OpenAI or Anthropic, set the appropriate env var and switch the model line — full BYOK admin UI is on the P1 backlog.

## How to enable WhatsApp + SMS reminders
Add to `/app/backend/.env` and restart backend:
```
WHATSAPP_PHONE_NUMBER_ID=...
WHATSAPP_ACCESS_TOKEN=...
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_FROM=+1...
```

## "Made with Emergent" badge
Per Emergent support: appears only in the preview environment. Auto-removed on deployment / paid plans.

## Backlog
### P1
- BYOK admin UI for AI provider (OpenAI/Anthropic direct keys vs Emergent universal).
- Async HTTP for messaging.py (replace `requests` with `httpx.AsyncClient`).
- Streaming CSV cursor for very large exports.
- Allow RECEPTION to create call-back reminders (if needed).

### P2
- N+1 query optimization (use `$lookup` aggregation in patient timeline + dashboards).
- Configurable reminder templates in admin UI.
- Richer top_complaints (medical term filter / TF-IDF).
- Brute-force lockout on `/api/auth/login`.

## Next Action Items
- Add custom Sparsa Homeoclinic logo file (PNG/SVG) — current build uses a tasteful leaf monogram.
- Paste Twilio + WhatsApp keys into backend/.env to activate WhatsApp/SMS.
- Schedule `/app/scripts/backup.sh` on the clinic server PC (cron / Task Scheduler).
