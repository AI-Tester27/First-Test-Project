#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

SUDO=""
if [ "$EUID" -ne 0 ]; then
  if command -v sudo >/dev/null 2>&1; then
    SUDO="sudo"
  else
    echo "Error: this script requires root privileges or sudo."
    exit 1
  fi
fi

install_packages_apt() {
  $SUDO apt-get update
  $SUDO apt-get install -y --no-install-recommends \
    curl ca-certificates git python3 python3-venv python3-pip python3-dev build-essential \
    libssl-dev libffi-dev libbz2-dev libreadline-dev libsqlite3-dev zlib1g-dev jq libjq-dev npm
}

install_packages_dnf() {
  $SUDO dnf install -y curl ca-certificates git python3 python3-virtualenv python3-pip gcc gcc-c++ make \
    openssl-devel libffi-devel bzip2-devel readline-devel sqlite-devel zlib-devel jq nodejs npm
}

install_packages_pacman() {
  $SUDO pacman -Sy --noconfirm curl git python python-virtualenv python-pip base-devel openssl libffi jq nodejs npm
}

install_packages_zypper() {
  $SUDO zypper refresh
  $SUDO zypper install -yn curl git python3 python3-virtualenv python3-pip gcc gcc-c++ make \
    libopenssl-devel libffi-devel bzip2-devel readline-devel sqlite3-devel zlib-devel jq nodejs npm
}

if command -v apt-get >/dev/null 2>&1; then
  install_packages_apt
elif command -v dnf >/dev/null 2>&1; then
  install_packages_dnf
elif command -v pacman >/dev/null 2>&1; then
  install_packages_pacman
elif command -v zypper >/dev/null 2>&1; then
  install_packages_zypper
else
  echo "Error: unsupported package manager. Install python3, pip, nodejs, npm, curl, build tools, and jq manually."
  exit 1
fi

if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
  echo "Error: node/npm installation failed or is missing."
  exit 1
fi

if command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
else
  echo "Error: python3 is not installed."
  exit 1
fi

if [ ! -d "$ROOT_DIR/.venv" ]; then
  $PYTHON -m venv "$ROOT_DIR/.venv"
fi

"$ROOT_DIR/.venv/bin/python" -m pip install --upgrade pip setuptools wheel
"$ROOT_DIR/.venv/bin/pip" install -r "$ROOT_DIR/backend/requirements.txt"

cd "$ROOT_DIR/frontend"
npm install
cd "$ROOT_DIR"

if [ ! -f "$ROOT_DIR/backend/.env" ]; then
  cat > "$ROOT_DIR/backend/.env" <<'EOF'
MONGO_URL="mongodb://localhost:27017"
DB_NAME="sparsa_homeoclinic"
CORS_ORIGINS="*"
JWT_SECRET="$(python3 - <<'PY'
import secrets
print(secrets.token_hex(32))
PY
)"
EMERGENT_LLM_KEY=""
EOF
  echo "Created backend/.env with local defaults. Update EMERGENT_LLM_KEY and other values as needed."
else
  echo "backend/.env already exists, leaving it unchanged."
fi

cat <<'EOF'
Setup complete.

Next steps:
  1) Start the backend:
       source .venv/bin/activate
       uvicorn backend.server:app --reload --host 0.0.0.0 --port 8000

  2) Start the frontend:
       cd frontend
       npm start

If you want to run the backend directly without activation:
  .venv/bin/uvicorn backend.server:app --reload --host 0.0.0.0 --port 8000
EOF
