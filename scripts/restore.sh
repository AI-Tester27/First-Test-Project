#!/usr/bin/env bash
# Sparsa Homeoclinic — restore from a backup tar.gz produced by backup.sh
# Usage: ./restore.sh /var/backups/sparsa/sparsa_homeoclinic-20260221-230000.tar.gz
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <backup.tar.gz>"
  exit 1
fi

ARCHIVE="$1"
MONGO_URL="${MONGO_URL:-mongodb://localhost:27017}"
DB_NAME="${DB_NAME:-sparsa_homeoclinic}"
TMP_DIR="$(mktemp -d)"

echo "[$(date -Iseconds)] Extracting ${ARCHIVE}"
tar -xzf "${ARCHIVE}" -C "${TMP_DIR}"

INNER="$(find "${TMP_DIR}" -mindepth 1 -maxdepth 1 -type d | head -n1)"
echo "[$(date -Iseconds)] Restoring → ${DB_NAME} (DROP existing collections)"
mongorestore --uri="${MONGO_URL}" --drop --nsInclude="${DB_NAME}.*" "${INNER}"

rm -rf "${TMP_DIR}"
echo "[$(date -Iseconds)] Restore complete."
