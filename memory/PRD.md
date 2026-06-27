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

### v5 (121 tests pass — 2026-06-20)
- **Admin Messaging Settings page** (`/admin/messaging`) — DB-backed runtime Twilio + WhatsApp credentials, no restart required. Masked display, per-field Clear via `__CLEAR__` sentinel, 30s cache refresh in scheduler. Endpoints: `GET/POST /api/admin/messaging-settings`. Provider precedence: DB → env.
- **Admin Analytics → MongoDB aggregations** — replaced 30 sequential `count_documents`+`aggregate` calls with two bucketed aggregations using `$dateAdd` + `$dateToString` (IST). Top complaints now `$split`/`$unwind`/`$group` server-side. Turnaround now a single `$dateFromString` aggregation. <0.5s on current dataset.
- **File-upload size hardening** — `/api/cases/{id}/attachments` streams in 64 KB chunks, aborts at >10 MB without buffering full payload.
- ✅ iteration_6: 23/23 backend + 8/8 frontend tests pass.

### v6 (logo branding — 2026-06-20)
- **Sparsa Homeo Care logo** wired into the sidebar, login hero card + login header, and the printable receipt. Saved at `/app/frontend/public/logo.png`. Also wired as favicon + apple-touch-icon.
- Reusable `<Logo />` component (`/app/frontend/src/components/Logo.jsx`) as single source of truth.
- Brand text harmonised to "Sparsa Homeo Care" in receipts, browser title, page meta, and WhatsApp/SMS reminder body.

### v7 (Phase A — FIR + date-only follow-ups — iteration_7 ✅ 15/15)
- **Patient model expanded**: marital_status, height_cm, weight_kg, **auto-BMI**, consulting_doctor_id, sources (multi-select), referral_name, chief_complaint, visit_type.
- New endpoint `POST /api/patients/fir` creates patient + first case atomically.
- Reception **New Patient** page rewritten as comprehensive FIR form (sectioned UI, conditional referral-name, BMI live-calc, walk-in/appointment radio).
- **Follow-up changed to date-only**: `FollowupIn.next_followup_date: date`; anchored to 09:00 IST UTC for the scheduler. UI uses a `<input type="date">`.
- Test data wiped per user's request; counters reset.

### v8 (Phases B + C + D — iteration_8 ✅ 34/34 pytest)
- **Phase B — Patient search & quick contact**:
  - `GET /api/patients?search=…` now RBAC-scoped: non-owner DOCTOR only sees patients with cases assigned to them (uses `doctor_id`, not `user.id` — fixed).
  - New `/doctor/patients` page (search + tap-to-call/SMS/WhatsApp quick-actions). Reusable `<QuickContact />` exported.
  - Pharmacy + Doctor reminder cards and PRO follow-up widget now show phone number + QuickContact buttons.
- **Phase C — PRO power features**:
  - `GET /api/pro/financial-search?q=…` — global billing search; per-patient summary + per-visit table.
  - `POST /api/cases/{id}/attachments` now accepts `kind=PAYMENT_PROOF`. PRO can upload payment proofs (UPI/PhonePe/GPay screenshots) before closing a bill. `?kind=PAYMENT_PROOF` filter on list endpoint.
  - `GET /api/pro/analytics` — comprehensive business analytics (patient demographics, source acquisition, visits by doctor + type, 30-day revenue trend, mode breakdown, consult vs medicine split, operational turnaround, outstanding).
  - New `/pro/financial-search` and `/pro/analytics` pages with bar charts.
- **Phase D — Admin & AI**:
  - Inline **Reset password** modal on Admin → Users (per-user). Backend enforces `min_length=8` on `UserCreateIn`/`UserUpdateIn`.
  - AI Visit Recap now supports `?mode=detailed` (owner doctor / admin only) → Markdown response with 6 sections: Patient Profile, Clinical Assessment, Possible Diagnostic Directions, **Mother Tincture Suggestions**, Lifestyle Recommendations, Treatment Considerations + a "decision-support only" disclaimer. `mode=brief` (default) keeps the 5-line briefing.
  - Tiny inline Markdown renderer in the timeline UI (avoids new dependency).

## Bring-your-own-key for AI (status)
Currently uses Emergent Universal LLM key (Claude Sonnet 4.5). Provider abstraction is in `routers/ai.py::_call_llm`. To swap to direct OpenAI or Anthropic, set the appropriate env var and switch the model line — full BYOK admin UI is on the P1 backlog.

## How to enable WhatsApp + SMS reminders
**Option A (preferred):** Log in as ADMIN → sidebar → **Messaging** → paste keys → Save. Live immediately, no restart.
**Option B:** Add to `/app/backend/.env` and restart backend:
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
- Replace `/app/frontend/public/logo.png` with a higher-res / SVG version anytime — the `<Logo />` component already loads from `/logo.png`.
- Paste Twilio + WhatsApp keys via **/admin/messaging** (or backend/.env) to activate WhatsApp/SMS.
- Schedule `/app/scripts/backup.sh` on the clinic server PC (cron / Task Scheduler) — see `/app/scripts/README.md`.
