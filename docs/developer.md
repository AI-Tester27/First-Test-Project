# Developer Guide

This developer guide describes how to set up, run, test, and contribute to Sparsa Homeoclinic locally and in CI/CD. It's written for engineers who will work on the FastAPI backend (Python) and the React frontend (JavaScript).

## Table of contents
- Overview
- Prerequisites
- Repository layout
- Local development
  - Clone
  - Environment
  - Backend
  - Frontend
- Database
  - Local MongoDB
  - Seeding data
  - Backup & restore
- Testing
- Linting, formatting & typing
- Environment variables & secrets
- Branching, commits & PRs
- CI / CD
- Releases & deployment notes
- Debugging & troubleshooting
- Useful commands
- Contact / support

---

## Overview
Sparsa Homeoclinic is a clinic management system with a FastAPI backend (Python) and a React frontend. The backend uses MongoDB and provides REST endpoints and Swagger UI (/docs) for API exploration. The repo includes scripts for backup/restore, seed data, and developer utilities.

## Prerequisites
- git (2.25+)
- Python 3.8+
- Node.js (16+ recommended) and Yarn 1.22.x (or npm if you prefer)
- MongoDB (local or Atlas)
- Optional: Docker (for local MongoDB or test environments)

## Repository layout
(Top-level paths - refer to root README for a printable tree)
- backend/ — FastAPI service, Pydantic models, routers, tests
- frontend/ — React app (Tailwind), components and pages
- scripts/ — backup and restore utilities
- memory/ — PRD, roadmap and domain notes
- design_guidelines.json — UI/UX tokens and conventions

---

## Local development

### Clone
```bash
git clone https://github.com/AI-Tester27/First-Test-Project.git
cd First-Test-Project
# Work on a feature branch
git checkout -b feature/your-feature
```

### Environment
Copy the example env (if present) and fill secrets:
```bash
cp backend/.env.example backend/.env
# Edit backend/.env with MONGO_URL, SECRET_KEY, TWILIO_*, etc.
```
If no .env.example exists, create backend/.env with at least MONGO_URL and SECRET_KEY.

### Backend (FastAPI)
Create and activate a virtual environment, install dependencies, and run the server.

```bash
# from repo root
cd backend
python3 -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# start dev server (auto-reload)
python -m uvicorn server:app --reload --port 8000
# API docs: http://localhost:8000/docs
```

Notes:
- server:app is the expected entrypoint; adjust if your code uses a different module or app variable.
- If you prefer Docker, a docker-compose file can be added to spin up backend + MongoDB.

### Frontend (React)
Install dependencies and start the dev server.

```bash
cd frontend
yarn install   # or npm install
yarn start     # runs on http://localhost:3000
```

The frontend expects the backend API base URL to be set via environment or a runtime config. Check frontend/.env or frontend/src/lib/apiClient.js (or similar) for the BASE_URL variable.

---

## Database

### Local MongoDB
You can run MongoDB locally or use a managed Atlas cluster. For local quick start using Docker:

```bash
docker run --rm -d -p 27017:27017 --name sparsa-mongo mongo:7
export MONGO_URL="mongodb://localhost:27017/sparsa_homeoclinic"
```

Set MONGO_URL in backend/.env accordingly.

### Seeding data
If repository includes a seed script:

```bash
cd backend
python seed.py
```

This will insert demo users, doctors, sample patients, and sample cases needed for local development.

### Backup & restore
Scripts exist at /app/scripts/backup.sh and restore.sh — see scripts/README.md for full instructions. Use these before performing destructive testing.

---

## Testing

Backend tests use pytest and live in backend/tests/.

```bash
cd backend
# run all tests
pytest
# run a specific test file
yt pytest tests/test_auth.py
# run tests by pattern
pytest -k "login"
```

Frontend tests use the React test runner (Jest):

```bash
cd frontend
yarn test
```

CI: Ensure tests run in PR pipelines and fail fast on errors.

---

## Linting, formatting & typing

Python:
- black (format)
- isort (imports)
- flake8 (style)
- mypy (type checking)

Run:
```bash
cd backend
black .
isort .
flake8
mypy
```

JavaScript/TypeScript:
- ESLint (linting)
- Prettier (formatting)

Run:
```bash
cd frontend
yarn lint
yarn format  # if configured
```

CI pipelines should run linters and fail PRs that do not meet style or typing requirements.

---

## Environment variables & secrets
Never commit secrets to source control. Use the following patterns:
- backend/.env (local development; not checked in)
- CI secrets (GitHub Actions secrets) for production keys
- For hosted deployments use a secrets manager (AWS Secrets Manager, GCP Secret Manager, or platform-specific env vars)

Minimum backend vars:
- MONGO_URL
- SECRET_KEY
- TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN (if using Twilio)
- WHATSAPP_API_KEY (if applicable)

---

## Branching, commits & PRs
Branch naming:
- feature/<short-description>
- fix/<short-description>
- chore/<short-description>

Commit messages:
- Use imperative style: "Add login endpoint"
- Include a short summary (50 chars) and an optional body if needed.

Pull request process:
1. Open a PR against the main integration branch (e.g., test-branch or main depending on workflow).
2. Include a clear description, screenshots (if UI), and testing steps.
3. Make sure CI passes (tests/lint/build).
4. Assign reviewers and address review comments.
5. Squash-merge or use a merge commit according to repo policy.

Code review checklist:
- Tests added for new logic
- Lint and format pass
- API changes documented (update README or API docs)
- Security review for any secrets or data exposure

---

## CI / CD
The repo should have a GitHub Actions workflow (or similar) that:
- Installs dependencies
- Lints and formats
- Runs unit tests (backend & frontend)
- Builds the frontend
- Optionally runs integration tests against a MongoDB test instance

Add badges to README after the workflow URL becomes stable.

---

## Releases & deployment notes
- Backend: containerize the FastAPI app (Dockerfile) and push images to container registry. Use environment variables to configure MongoDB and external services.
- Frontend: build with `yarn build` and deploy the static build to Vercel/Netlify or as a static site on S3 + CloudFront.
- Database: use MongoDB Atlas for production. Configure backup policies and monitoring.

---

## Debugging & troubleshooting
- Backend logs: configure logging in server to output to stdout/stderr. Use an APM (Sentry, Datadog) for errors in production.
- Common issues:
  - MONGO connection errors → verify MONGO_URL and network access
  - Missing env vars → check backend/.env or platform env

Local debugging tips:
- Use a test MongoDB container to isolate dev data
- Run the backend with `--reload` and enable debug-level logs when developing

---

## Useful commands
```bash
# git
git checkout -b feature/your-feature

# backend
cd backend
source .venv/bin/activate
python -m uvicorn server:app --reload
pytest -q
black . && isort .

# frontend
cd frontend
yarn install
yarn start
yarn test
```

---

## Contact / support
If you have questions about architecture, domain logic, or deployment, open a GitHub issue and tag @AI-Tester27. For urgent issues, include logs and reproduction steps.

---

If you'd like, I can:
- Add a Docker Compose file to run backend + MongoDB + frontend for development
- Add GitHub Actions workflows for testing & linting
- Split this developer guide into smaller docs under /docs/ (API, deployment, architecture)

Tell me which of these you want next and I'll create the files and CI workflows for you.