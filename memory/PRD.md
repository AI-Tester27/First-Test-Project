# Sparsa Homeoclinic — PRD

## Original Problem Statement
Internal clinic management web app for **Sparsa Homeoclinic** (homeopathy clinic, 5 PCs on LAN).
Workflow: **Reception → Doctor → Pharmacy → PRO/Billing**.
- Reception creates patient + case, assigns to Dr. Jyothi Vani or Dr. Hemanth.
- Doctor adds diagnosis, sensitivity, prescription (medicine, potency, dosage, frequency, duration), suggestions, follow-up.
- Pharmacy can **edit** prescriptions (versioned) and record dispense.
- PRO/Billing collects payment (full/half/custom; cash/PhonePe/card/other) and prints **EN + Telugu** receipt.
- **Dr. Jyothi Vani** (Owner/Lead) sees ALL cases incl. Dr. Hemanth's; **Dr. Hemanth** sees only his own.
- New **ADMIN** role with complete access (users, data, audit, stats).
- AI assist for doctors (summarize complaint, draft advice, prescription instructions) using **Claude Sonnet 4.5** via Emergent LLM key.

## Stack (adapted)
React + FastAPI + MongoDB (original spec was Laravel + MySQL).

## User Personas / Roles
| Role | User | Access |
|---|---|---|
| ADMIN | admin1 | Full read across data; exclusive: user CRUD, audit log, stats |
| OWNER_DOCTOR | jyothi | All cases including Hemanth's, all doctor actions |
| DOCTOR | hemanth | Only his own assigned cases |
| RECEPTION | reception1 | Create/search patients + cases, view limited fields |
| PHARMACY | pharmacy1 | Dispense + edit prescriptions (creates new version) |
| PRO | pro1 | Billing, payments, print receipt |

## What's Implemented (v1 — 2026-02-21)
- JWT (httpOnly cookie) auth + bcrypt; 6 seeded users.
- Patients: auto-generated `SPARSA-XXXXXX` uid, search by name/phone/uid.
- Cases: workflow status engine (WAITING_FOR_DOCTOR → IN_CONSULTATION → SENT_TO_PHARMACY → IN_PHARMACY → READY_FOR_BILLING → PAYMENT_PENDING/PARTIALLY_PAID → CLOSED).
- Clinical notes (one per case, upsert).
- Prescription versioning — pharmacy edits create a new version with `edited_by_pharmacy=true`.
- Pharmacy dispense → auto-moves case to READY_FOR_BILLING.
- Billing — total = consultation + medicine; PAID/PARTIAL/UNPAID; receipt `SPH-RC-XXXXXX`.
- Follow-up + on-screen reminders.
- AI assist (3 actions) via Claude Sonnet 4.5 / Emergent Universal Key.
- Admin: user management, audit log viewer, stats (by status, by doctor, revenue).
- Bilingual EN+Telugu printable receipt (uses `window.print()`).
- 33/33 backend tests pass (auth, RBAC, full workflow, AI, admin).

## Tech Notes
- Backend: `/app/backend/server.py` (single file ~830 lines; routers split candidate for future).
- Frontend: `/app/frontend/src/{App.js, pages/{reception,doctor,pharmacy,pro,admin}, contexts/AuthContext.jsx, components/{AppLayout,StatusBadge,RequireAuth}.jsx}`.
- Design: teal accent, Work Sans + IBM Plex Sans, flat 1px borders, status pills.
- Audit log entries written on every CREATE / UPDATE / STATUS_CHANGE / PAYMENT_UPDATE / LOGIN / AI_USED / PRESCRIPTION_EDIT.

## Backlog (P0 / P1 / P2)
### P1 — Useful but deferred
- File attachments (jpg/png/pdf, 10MB) via Emergent object storage.
- WhatsApp/SMS reminders (Twilio + WhatsApp Cloud API) — currently on-screen only.
- Brute-force lockout on /api/auth/login (5 failed = 15min lockout).
- Split server.py into routers (auth/patients/cases/pharmacy/payments/ai/admin) + seed.py.

### P2 — Nice to have
- CSV export of patients / cases / payments.
- Patient visit timeline (multi-visit history with old prescriptions).
- Editable message templates (admin UI) for reminder text.
- Multi-version prescription comparison view for doctor approval after pharmacy edit.
- Daily backup script (mongodump) + restore docs for clinic IT.

## Next Action Items
- Confirm receipt language quality with native Telugu speaker before clinic rollout.
- Wire Twilio + WhatsApp Cloud API keys when clinic is ready for SMS reminders.
- Add file attachments (Emergent object storage) if lab reports/images are needed.
