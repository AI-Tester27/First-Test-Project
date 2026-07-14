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

install_apt() {
  $SUDO apt-get update
  $SUDO apt-get install -y --no-install-recommends \
    curl ca-certificates git python3 python3-venv python3-pip build-essential \
    libssl-dev libffi-dev libbz2-dev libreadline-dev libsqlite3-dev zlib1g-dev \
    jq nodejs npm
}

install_dnf() {
  $SUDO dnf install -y curl ca-certificates git python3 python3-virtualenv python3-pip gcc gcc-c++ make \
    openssl-devel libffi-devel bzip2-devel readline-devel sqlite-devel zlib-devel jq nodejs npm
}

install_pacman() {
  $SUDO pacman -Sy --noconfirm curl git python python-virtualenv python-pip base-devel \
    openssl libffi jq nodejs npm
}

install_zypper() {
  $SUDO zypper refresh
  $SUDO zypper install -yn curl git python3 python3-virtualenv python3-pip gcc gcc-c++ make \
    libopenssl-devel libffi-devel bzip2-devel readline-devel sqlite3-devel zlib-devel jq nodejs npm
}

install_system_dependencies() {
  if command -v apt-get >/dev/null 2>&1; then
    install_apt
  elif command -v dnf >/dev/null 2>&1; then
    install_dnf
  elif command -v pacman >/dev/null 2>&1; then
    install_pacman
  elif command -v zypper >/dev/null 2>&1; then
    install_zypper
  else
    echo "Error: unsupported package manager. Install python3, pip, nodejs, npm, git, curl, jq, and build tools manually."
    exit 1
  fi
}

check_mongo_or_docker() {
  if command -v mongod >/dev/null 2>&1 || command -v mongo >/dev/null 2>&1; then
    echo "MongoDB client/server is already installed."
  elif command -v docker >/dev/null 2>&1; then
    echo "MongoDB not found. Starting MongoDB in Docker container..."
    if docker ps --format '{{.Names}}' | grep -q '^sparsa-mongo$'; then
      echo "Docker container sparsa-mongo already running."
    else
      docker run -d --name sparsa-mongo -p 27017:27017 mongo:7
      echo "Started MongoDB container sparsa-mongo on port 27017."
    fi
  else
    echo "Warning: MongoDB is not installed and Docker is not available. Please install one of them before running the app."
  fi
}

ensure_node_and_yarn() {
  if ! command -v node >/dev/null 2>&1; then
    echo "Error: node is not installed."
    exit 1
  fi
  if ! command -v npm >/dev/null 2>&1; then
    echo "Error: npm is not installed."
    exit 1
  fi
  if ! command -v yarn >/dev/null 2>&1; then
    echo "Yarn not found. Installing Yarn globally using npm..."
    $SUDO npm install -g yarn@1.22.22
  fi
}

create_backend_env() {
  local env_file="$ROOT_DIR/backend/.env"
  if [ -f "$env_file" ]; then
    echo "backend/.env already exists, leaving unchanged."
    return
  fi

  local jwt_secret
  jwt_secret=$(python3 - <<'PY'
import secrets
print(secrets.token_hex(32))
PY
)

  cat > "$env_file" <<EOF
MONGO_URL="mongodb://localhost:27017"
DB_NAME="sparsa_homeoclinic"
JWT_SECRET="$jwt_secret"
CORS_ORIGINS="*"
EMERGENT_LLM_KEY=""
EOF
  echo "Created backend/.env with local defaults. Update EMERGENT_LLM_KEY or messaging keys if needed."
}

create_frontend_env() {
  local env_file="$ROOT_DIR/frontend/.env"
  if [ -f "$env_file" ]; then
    echo "frontend/.env already exists, leaving unchanged."
    return
  fi

  cat > "$env_file" <<EOF
REACT_APP_BACKEND_URL="http://localhost:8000"
EOF
  echo "Created frontend/.env pointing to local backend."
}

install_python_backend() {
  echo "Setting up Python backend..."
  if [ ! -d "$ROOT_DIR/backend/.venv" ]; then
    python3 -m venv "$ROOT_DIR/backend/.venv"
  fi
  source "$ROOT_DIR/backend/.venv/bin/activate"
  pip install --upgrade pip setuptools wheel
  pip install -r "$ROOT_DIR/backend/requirements.txt"
  deactivate
}

install_frontend() {
  echo "Setting up frontend..."
  cd "$ROOT_DIR/frontend"
  yarn install
  cd "$ROOT_DIR"
}

print_next_steps() {
  cat <<EOF

Setup finished.

Next steps:
  1) Start MongoDB if you are not already running it.
     - If you used Docker:
         docker start sparsa-mongo

  2) Start the backend:
         source "$ROOT_DIR/backend/.venv/bin/activate"
         uvicorn backend.server:app --reload --host 0.0.0.0 --port 8000

  3) Start the frontend:
         cd "$ROOT_DIR/frontend"
         yarn start

  4) Open the app in your browser:
         http://localhost:3000

If the frontend cannot connect, confirm REACT_APP_BACKEND_URL in "$ROOT_DIR/frontend/.env"
and that the backend is running at http://localhost:8000.
EOF
}

main() {
  echo "=== Sparsa Homeoclinic Linux Setup ==="
  install_system_dependencies
  check_mongo_or_docker
  ensure_node_and_yarn
  create_backend_env
  create_frontend_env
  install_python_backend
  install_frontend
  print_next_steps
}

main "$@"
