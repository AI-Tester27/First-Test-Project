#!/usr/bin/env bash
# Sparsa Homeoclinic — daily MongoDB backup script
# Usage:   ./backup.sh
# Cron:    0 23 * * * /app/scripts/backup.sh >> /var/log/sparsa-backup.log 2>&1
# Windows: schedule via Task Scheduler running this in Git Bash / WSL.
set -euo pipefail

BACKUP_DIR="${SPARSA_BACKUP_DIR:-/var/backups/sparsa}"
KEEP_DAYS="${SPARSA_BACKUP_KEEP_DAYS:-14}"
MONGO_URL="${MONGO_URL:-mongodb://localhost:27017}"
DB_NAME="${DB_NAME:-sparsa_homeoclinic}"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="${BACKUP_DIR}/${DB_NAME}-${STAMP}"

mkdir -p "${OUT}"
echo "[$(date -Iseconds)] Backing up ${DB_NAME} → ${OUT}"

mongodump --uri="${MONGO_URL}" --db="${DB_NAME}" --out="${OUT}" --quiet

# tar + gzip
tar -C "${BACKUP_DIR}" -czf "${OUT}.tar.gz" "${DB_NAME}-${STAMP}"
rm -rf "${OUT}"
echo "[$(date -Iseconds)] Wrote ${OUT}.tar.gz ($(du -h "${OUT}.tar.gz" | cut -f1))"

# Retention
find "${BACKUP_DIR}" -name "${DB_NAME}-*.tar.gz" -type f -mtime "+${KEEP_DAYS}" -print -delete
echo "[$(date -Iseconds)] Retention applied (>${KEEP_DAYS} days removed)"
