
# Copilot Instructions for Sparsa Homeoclinic

## Quick Start: Build, Test, Lint

### Backend (FastAPI + MongoDB)

```bash
# Setup (run once)
cd /app
python3 -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r backend/requirements.txt

# Run backend dev server
cd backend && python -m uvicorn server:app --reload

# Run all tests
cd backend && pytest

# Run single test file
cd backend && pytest tests/test_auth.py

# Run tests matching a pattern
cd backend && pytest -k "test_login"

# Lint & format
cd backend
black .                           # Auto-format
isort .                           # Sort imports
flake8 .                          # Check style
mypy .                            # Type check
```

### Frontend (React with Tailwind)

```bash
# Setup & run (in frontend/ directory)
cd /app/frontend
yarn install  # Note: uses Yarn 1.22.22, not npm
yarn start    # Dev server on port 3000

# Test
yarn test

# Build for production
yarn build

# Linting
npm run lint  # via eslint
```

### Database

```bash
# MongoDB must be running (local or MongoDB Atlas)
# Connection: MONGO_URL env var in backend/.env

# Seed demo data
cd backend && python seed.py

# Backup/restore
/app/scripts/backup.sh              # Daily backup script (cron/Task Scheduler)
/app/scripts/restore.sh <backup.tar.gz>  # Restore from backup
```

## Architecture Overview

### Project Structure

```
/app
├── backend/                  # FastAPI app
│   ├── server.py            # Entry point (minimal, delegates to routers)
│   ├── core.py              # Shared: db, auth, roles, audit, constants
│   ├── models.py            # Pydantic schemas for all endpoints
│   ├── seed.py              # Demo data (6 test users, doctors, patient templates)
│   ├── storage.py           # Emergent Object Storage integration
│   ├── messaging.py         # Twilio + WhatsApp Cloud API client
│   ├── routers/             # Domain-driven endpoint modules
│   │   ├── auth.py          # Login, logout, token refresh
│   │   ├── patients.py      # Patient CRUD, doctors list, visit timeline
│   │   ├── cases.py         # Case workflow (reception → doctor → pharmacy)
│   │   ├── pharmacy.py      # Dispense workflow
│   │   ├── payments.py      # Payment tracking
│   │   ├── ai.py            # AI summarization & advice (per-case)
│   │   ├── attachments.py   # File upload/download (Object Storage)
│   │   ├── reminders.py     # SMS/WhatsApp reminders + scheduler
│   │   ├── exports.py       # CSV exports (5 types)
│   │   └── admin.py         # User management, audit log, stats
│   ├── tests/               # pytest test suite (71 tests)
│   └── requirements.txt      # Dependencies: FastAPI, Motor, Pydantic, etc.
│
├── frontend/                # React app
│   ├── src/
│   │   ├── App.js          # Root component, routing
│   │   ├── components/     # Reusable UI (forms, tables, buttons, etc.)
│   │   ├── contexts/       # React Context (auth, user state)
│   │   ├── pages/          # Page-level components (Dashboard, PatientList, etc.)
│   │   ├── hooks/          # Custom React hooks
│   │   ├── lib/            # Utilities (API client, helpers)
│   │   └── index.css       # Global styles (Tailwind)
│   └── package.json        # Scripts: start, build, test
│
├── scripts/                 # Utility scripts
│   ├── backup.sh           # mongodump → tar.gz (cron-safe)
│   └── restore.sh          # tar.gz → mongorestore
│
├── memory/                 # Docs (not code)
│   └── PRD.md             # Feature history, roadmap
│
└── design_guidelines.json  # UI/UX specs: colors, typography, spacing
```

### Workflow & User Roles

```
Reception → Doctor → Pharmacy → PRO/Billing → Closed

Roles (core.py):
  ADMIN           → Users, audit, stats
  OWNER_DOCTOR    → All cases (Jyothi)
  DOCTOR          → Own cases only (Hemanth) [enforced in case_filter_for_role()]
  RECEPTION       → Create patients, open cases, search
  PHARMACY        → Dispense, track inventory
  PRO             → Billing, payments, exports
```

### Status Flow

Cases progress through these statuses (core.py `STATUS_*` constants):

```
WAITING_FOR_DOCTOR
  ↓
IN_CONSULTATION (doctor adds clinical notes)
  ↓
SENT_TO_PHARMACY
  ↓
IN_PHARMACY (pharmacy dispenses)
  ↓
READY_FOR_BILLING
  ↓
PAYMENT_PENDING → PARTIALLY_PAID / CLOSED (paid in full)
```

### Database Schema (MongoDB)

Collections:
- `patients` — patient_uid (auto `SPARSA-XXXXXX`), demographics, allergies
- `doctor_profiles` — Doctor name, license, department
- `cases` — Workflow object linking patient + case status + prescriptions
- `clinical_notes` — Versioned notes per case (doctor can edit in current case only)
- `prescriptions` — Versioned per case (full history retained)
- `pharmacy_dispense` — What pharmacy actually gave
- `payments` — Payment records (can be partial)
- `reminders` — Scheduled SMS/WhatsApp tasks + delivery status
- `attachments` — File metadata (id, url, size, mime type) — content in Object Storage
- `audit_log` — Every mutation (user, action, before/after)
- `counters` — Incremental counters for patient_uid, case_uid, etc.
- `users` — Auth user accounts (hashed password, role, created_at)

## Key Conventions

### Backend Code Style & Patterns

**1. Async-only FastAPI**
- Every endpoint is `async def`
- Every DB call uses `await` with Motor (async MongoDB driver)
- No blocking I/O in handlers

**2. Role-based Access Control (RBAC)**
```python
from core import get_current_user, require_roles, case_filter_for_role

# Dependency-injected user + role checking
@router.get("/patients")
async def list_patients(user: dict = Depends(get_current_user)):
    # user is {"id": "...", "role": "...", ...}
    if user["role"] not in (ROLE_RECEPTION, ROLE_ADMIN):
        raise HTTPException(status_code=403, detail="Not allowed")

# Stricter check
@router.post("/cases")
async def create_case(
    payload: CaseIn,
    user: dict = Depends(require_roles(ROLE_RECEPTION, ROLE_ADMIN))
):
    # Only allowed roles reach here
```

**3. Doctor Scope Filtering**
```python
from core import case_filter_for_role

# In cases.py or patients.py:
case_filter = case_filter_for_role(user)  # {"doctor_id": user["id"]} if DOCTOR
# Then query: db.cases.find(case_filter)
```

**4. Audit Every Mutation**
```python
from core import audit

# Before INSERT/UPDATE/DELETE:
await audit(db, user, "patient_created", {"patient_uid": "SPARSA-000001"})
# After the mutation
```

**5. Error Handling**
```python
from fastapi import HTTPException

# Prefer explicit 4xx status codes for client errors
raise HTTPException(status_code=400, detail="Age must be positive")
raise HTTPException(status_code=409, detail="Patient already exists")

# Let uncaught exceptions (500) bubble up for logging
```

**6. Pydantic Validation in models.py**
```python
from pydantic import BaseModel, Field, EmailStr, field_validator

class PatientIn(BaseModel):
    first_name: str = Field(..., min_length=1)
    age: int = Field(..., ge=0, le=150)
    email: EmailStr

    @field_validator('first_name')
    @classmethod
    def name_upper(cls, v):
        return v.strip().title()
```

**7. Routers as Modules**
- One router = one domain (patients, cases, pharmacy, etc.)
- Each has its own file in `routers/`
- Each exports a `router: APIRouter` at module level
- server.py includes all routers in one loop (keeps it DRY)

### Frontend Code Style & Patterns

**1. Component Structure**
```javascript
// components/PatientCard.jsx (functional, React 19)
import { useContext } from 'react';
import { AuthContext } from '../contexts/AuthContext';

export default function PatientCard({ patient }) {
  const { user } = useContext(AuthContext);
  // role-based rendering
  return (
    <div className="border rounded-md p-4">
      <h3 className="text-lg font-semibold">{patient.first_name}</h3>
    </div>
  );
}
```

**2. API Calls (lib/api.js or similar)**
```javascript
// lib/api.js - centralized HTTP client
import axios from 'axios';

const client = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000/api',
  withCredentials: true,  // httpOnly cookies
});

export const getPatients = (search = '') => 
  client.get('/patients', { params: { search } });

export const createCase = (payload) => 
  client.post('/cases', payload);
```

**3. Context for Auth & User State**
```javascript
// contexts/AuthContext.js
import { createContext, useState, useEffect } from 'react';

export const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check logged-in status on mount
    fetch('/api/auth/me', { credentials: 'include' })
      .then(res => res.json())
      .then(data => setUser(data.user))
      .finally(() => setLoading(false));
  }, []);

  return (
    <AuthContext.Provider value={{ user, setUser, loading }}>
      {children}
    </AuthContext.Provider>
  );
}
```

**4. Data-testid Attributes (Required for QA)**
```javascript
// Per design_guidelines.json, ALL interactive + key informational elements MUST have data-testid
<button 
  data-testid="patient-search-button"
  onClick={handleSearch}
>
  Search
</button>

<input 
  data-testid="patient-name-input"
  placeholder="First name"
  onChange={e => setFirstName(e.target.value)}
/>
```

**5. Styling: Tailwind + design_guidelines.json**
- Typography: Work Sans (headings), IBM Plex Sans (body)
- Colors: Teal primary (`#0F766E`), light backgrounds
- Layout: desktop-first, 5-PC LAN assumption, dense grids
- Cards: flat (`bg-white`), 1px border (`border-gray-200`), NO shadows
- Status badges: pill-shaped (`rounded-full`) with status colors from guidelines
- No dark mode; light theme always

### Environment Variables

**Backend (.env)**
```bash
# Required
MONGO_URL="mongodb://localhost:27017"
DB_NAME="sparsa_homeoclinic"
JWT_SECRET="<generate-a-secure-random-string>"

# Optional (gracefully skip if missing)
WHATSAPP_PHONE_NUMBER_ID="..."
WHATSAPP_ACCESS_TOKEN="..."
TWILIO_ACCOUNT_SID="..."
TWILIO_AUTH_TOKEN="..."
TWILIO_FROM="+1..."

# Object Storage (Emergent)
EMERGENT_API_KEY="..."
EMERGENT_BUCKET="..."
```

**Frontend (create-react-app)**
```bash
# .env (in frontend/ root)
REACT_APP_API_URL="http://localhost:8000/api"
```

## Testing Guidelines

### Backend Tests (pytest)

```bash
cd backend && pytest -v

# Test file location: tests/test_<router-name>.py
# Test convention: test_<endpoint_method>_<scenario>
```

**Key test patterns:**
- Use FastAPI TestClient for integration tests
- Mock MongoDB with pytest fixtures if needed
- Mock external APIs (Twilio, Object Storage) with `@patch`
- Every endpoint should have: happy path + at least 1 error case (auth, validation, not found)

**Example:**
```python
# tests/test_patients.py
from fastapi.testclient import TestClient
from backend.server import app

client = TestClient(app)

def test_list_patients_success(auth_header):
    response = client.get("/api/patients", headers=auth_header)
    assert response.status_code == 200
    assert "patients" in response.json()

def test_list_patients_unauthorized():
    response = client.get("/api/patients")
    assert response.status_code == 401
```

### Frontend Tests (yarn test)

Using React Testing Library + Jest (via craco).

```bash
cd frontend && yarn test

# Test file location: src/__tests__/<component>.test.js
# Test convention: test('<component> renders correctly')
```

**Key test patterns:**
- Render with AuthProvider context
- Mock API calls with `jest.mock()`
- Query by `data-testid` (not by role or text labels — they change)
- Test user interactions + side effects (navigation, form submission)

## Common Tasks

### Add a New Endpoint

1. **Create Pydantic schema in models.py**
   ```python
   class MyNewIn(BaseModel):
       field1: str
       field2: int = Field(..., gt=0)
   ```

2. **Add to routers/my_domain.py (or new file)**
   ```python
   @router.post("/my-endpoint")
   async def my_new_endpoint(
       payload: MyNewIn,
       user: dict = Depends(get_current_user)
   ):
       # Validate roles
       # Query/insert
       await audit(db, user, "my_action", {...})
       return {"status": "ok", "id": "..."}
   ```

3. **Register router in server.py** (already done in loop)

4. **Write test in tests/**

5. **Update frontend lib/api.js and call from component**

### Add a New Role

1. **Add constant to core.py** — `ROLE_NEWROLE = "NEWROLE"`
2. **Add to `require_roles()` calls** where that role should access
3. **Add role-based filtering** in `case_filter_for_role()` if needed (for DOCTOR scope)
4. **Seed a test user with that role** in seed.py
5. **Test access control** in backend tests

### Schedule a Recurring Task (like reminders)

1. **Define task in routers/reminders.py** (or new module)
2. **Use `APScheduler` or FastAPI's background tasks**
   ```python
   from apscheduler.schedulers.asyncio import AsyncIOScheduler
   scheduler = AsyncIOScheduler()
   scheduler.start()  # Start in server.py
   ```
3. **Schedule the job:**
   ```python
   scheduler.add_job(send_reminders, 'interval', minutes=5)
   ```

### Add/Modify File Attachments

- Uploads → Emergent Object Storage (configured in storage.py)
- Metadata stored in MongoDB (`attachments` collection)
- Download links are signed & temporary
- See routers/attachments.py for full flow

## Debugging Tips

1. **Backend logs:** `python -m uvicorn server:app --reload` outputs to console
2. **MongoDB queries:** Add `print()` statements or use MongoDB Compass to inspect
3. **Frontend network:** Browser DevTools → Network tab, check request/response
4. **CORS issues:** Already configured in server.py to allow `*` origins (adjust for production)
5. **Auth issues:** Check httpOnly cookie in browser DevTools → Application → Cookies

## Deployment Notes

- **Backend:** Run uvicorn behind a production ASGI server (Gunicorn, etc.)
- **Frontend:** Build with `yarn build`, serve static files from frontend/build/
- **Database:** Use MongoDB Atlas or hosted MongoDB service (not localhost)
- **File storage:** Configure Emergent Object Storage credentials in backend/.env
- **WhatsApp/SMS:** Add Twilio + WhatsApp API keys to backend/.env
- **Backups:** Schedule `/app/scripts/backup.sh` with cron (Linux) or Task Scheduler (Windows)

## Useful References

- **Project docs:** /app/memory/PRD.md, /app/scripts/README.md
- **Design specs:** /app/design_guidelines.json
- **Test credentials:** /app/memory/test_credentials.md
