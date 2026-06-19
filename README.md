# Sparsa Homeoclinic

An AI-integrated healthcare management system combining a FastAPI backend with MongoDB and a React frontend, designed to streamline clinic workflows from patient reception through billing.

**Language Composition:** JavaScript (64.5%) | Python (28.3%) | Shell (3.9%) | HTML (2.4%) | CSS (0.9%)

---

## 🎯 Quick Start

### Prerequisites
- Python 3.8+
- Node.js & Yarn 1.22.22
- MongoDB (local or Atlas)

### Backend Setup (FastAPI + MongoDB)

```bash
# Initialize virtual environment
cd /app
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r backend/requirements.txt

# Run development server
cd backend && python -m uvicorn server:app --reload

# Run tests
cd backend && pytest

# Lint & format
cd backend
black .        # Auto-format code
isort .        # Sort imports
flake8 .       # Style check
mypy .         # Type check
```

### Frontend Setup (React + Tailwind)

```bash
cd /app/frontend
yarn install   # Uses Yarn 1.22.22, not npm
yarn start     # Dev server on http://localhost:3000

# Testing & building
yarn test
yarn build
npm run lint   # ESLint check
```

### Database

```bash
# Configure MongoDB connection via MONGO_URL in backend/.env
# Seed demo data
cd backend && python seed.py

# Backup & restore
/app/scripts/backup.sh                    # Create daily backup
/app/scripts/restore.sh <backup.tar.gz>   # Restore from backup
```

---

## 📁 Project Structure

```
/app
├── backend/                      # FastAPI application
│   ├── server.py                # Entry point
│   ├── core.py                  # DB, auth, roles, audit, constants
│   ├── models.py                # Pydantic schemas
│   ├── seed.py                  # Demo data seeding
│   ├── storage.py               # Object Storage integration
│   ├── messaging.py             # Twilio + WhatsApp Cloud API
│   ├── routers/
│   │   ├── auth.py              # Login, logout, token refresh
│   │   ├── patients.py          # Patient CRUD, visits
│   │   ├── cases.py             # Case workflow management
│   │   ├── pharmacy.py          # Dispensing workflow
│   │   ├── payments.py          # Payment tracking
│   │   ├── ai.py                # AI summarization & advice
│   │   ├── attachments.py       # File upload/download
│   │   ├── reminders.py         # SMS/WhatsApp scheduling
│   │   ├── exports.py           # CSV exports (5 types)
│   │   └── admin.py             # User mgmt, audit, stats
│   ├── tests/                   # 71 pytest test cases
│   └── requirements.txt          # Python dependencies
│
├── frontend/                    # React application
│   ├── src/
│   │   ├── App.js              # Root component & routing
│   │   ├── components/         # Reusable UI components
│   │   ├── contexts/           # React Context (auth, user state)
│   │   ├── pages/              # Page-level components
│   │   ├── hooks/              # Custom React hooks
│   │   ├── lib/                # Utilities & API client
│   │   └── index.css           # Global Tailwind styles
│   └── package.json            # Scripts & dependencies
│
├── scripts/
│   ├── backup.sh               # MongoDB backup utility
│   └── restore.sh              # MongoDB restore utility
│
├── memory/
│   └── PRD.md                  # Feature history & roadmap
│
└── design_guidelines.json      # UI/UX specs
```

---

## 🏥 Workflow & User Roles

### Case Status Flow

```
WAITING_FOR_DOCTOR
         ↓
    IN_CONSULTATION (doctor adds notes)
         ↓
    SENT_TO_PHARMACY
         ↓
    IN_PHARMACY (dispensing)
         ↓
    READY_FOR_BILLING
         ↓
    PAYMENT_PENDING → PARTIALLY_PAID / CLOSED
```

### User Roles

| Role | Permissions |
|------|-------------|
| **ADMIN** | User management, audit logs, system stats |
| **OWNER_DOCTOR** | All cases (e.g., Jyothi) |
| **DOCTOR** | Own cases only (e.g., Hemanth) |
| **RECEPTION** | Create patients, open cases, search |
| **PHARMACY** | Dispense medications, track inventory |
| **PRO** | Billing, payments, data exports |

---

## 📊 Database Schema (MongoDB)

- **patients** — Demographics, allergies, unique `patient_uid` (auto: `SPARSA-XXXXXX`)
- **doctor_profiles** — Doctor credentials & department info
- **cases** — Workflow objects linking patient, status, prescriptions
- **clinical_notes** — Versioned notes per case (edit allowed in current case only)
- **prescriptions** — Versioned history per case
- **payments** — Transaction records
- **audit_logs** — System activity tracking

---

## 🤖 Key Features

### Backend (FastAPI)
- **Authentication** — JWT-based login with role-based access control
- **Case Management** — Multi-stage workflow from reception to billing
- **Clinical Notes** — Version control for doctor documentation
- **Prescription Tracking** — Full history with pharmacy dispense tracking
- **AI Integration** — Automated summarization and clinical advice (per-case)
- **Messaging** — SMS/WhatsApp reminders via Twilio & Cloud API
- **File Storage** — Attachment management with Object Storage
- **Exports** — 5 CSV export types for reporting
- **Audit Logging** — Complete activity tracking
- **Test Coverage** — 71 comprehensive test cases

### Frontend (React)
- **Dashboard** — Overview of cases and patient flow
- **Patient Management** — Create, search, view patient history
- **Case Workflow** — Track cases through all stages
- **Role-Based UI** — Views tailored to user permissions
- **Responsive Design** — Tailwind CSS for modern styling
- **Real-Time Updates** — WebSocket support (optional)

---

## 🧪 Testing

```bash
# Run all tests
cd backend && pytest

# Run specific test file
cd backend && pytest tests/test_auth.py

# Run tests matching pattern
cd backend && pytest -k "test_login"

# Run frontend tests
cd frontend && yarn test
```

---

## 📝 Environment Configuration

Create a `.env` file in the `backend/` directory:

```env
MONGO_URL=mongodb+srv://user:password@cluster.mongodb.net/sparsa_clinic
SECRET_KEY=your-secret-key-here
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-token
WHATSAPP_API_KEY=your-whatsapp-api-key
```

---

## 🚀 Deployment

- **Backend**: Deploy FastAPI app to cloud (AWS, GCP, Heroku, etc.)
- **Frontend**: Build with `yarn build` and host on static host (Vercel, Netlify, etc.)
- **Database**: Use MongoDB Atlas for managed MongoDB
- **Backups**: Run `/app/scripts/backup.sh` via cron/Task Scheduler daily

---

## 📚 Documentation

- **Architecture**: See `/app/memory/PRD.md` for feature history and roadmap
- **Design System**: Reference `/app/design_guidelines.json` for UI/UX specifications
- **API Endpoints**: Documentation available at `/docs` when backend is running (Swagger UI)

---

## 💡 Contributing

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Follow the code style (black, isort, flake8, mypy for Python)
3. Write tests for new functionality
4. Submit a pull request with a clear description

---

## 📧 Support

For questions or issues, please open a GitHub issue or contact the development team.

---

**Last Updated:** June 2026  
**License:** [Add your license here]
