#!/usr/bin/env bash
# Nightly backup (spec §11.4): pg_dump -Fc + restic snapshot of {dump, media} to an S3-compatible
# bucket in Uzbekistan (or SFTP / local path — anything restic supports). Retention
# 7 daily / 4 weekly / 6 monthly. Runs inside the `backup` container (same image as web).
#
# Env: DATABASE_URL, PGPASSWORD, RESTIC_REPOSITORY, RESTIC_PASSWORD, AWS_* (for s3:),
#      BACKUP_RETENTION_{DAILY,WEEKLY,MONTHLY}, BACKUP_DIR (default /backups),
#      MEDIA_ROOT (default /srv/media), TELEGRAM_BOT_TOKEN/TELEGRAM_ALERT_CHAT_ID (alerts)
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/backups}"
MEDIA_ROOT="${MEDIA_ROOT:-/srv/media}"
STAMP="$(date -u +%Y-%m-%dT%H%M%SZ)"
DUMP="${BACKUP_DIR}/ertaaniqla-${STAMP}.dump"
LOG_PREFIX="backup[${STAMP}]"
# shellcheck source=/dev/null
source "$(dirname "$0")/notify.sh"

log() { echo "${LOG_PREFIX} $*"; }

fail() {
  log "FAILED: $*" >&2
  notify_telegram "❌ Backup FAILED on $(hostname): $*"
  exit 1
}

[[ -n "${DATABASE_URL:-}" ]] || fail "DATABASE_URL is not set"
mkdir -p "${BACKUP_DIR}"

# 1. Postgres logical dump (custom format → parallel restore, compression built in)
log "pg_dump → ${DUMP}"
pg_dump --dbname="${DATABASE_URL}" --format=custom --compress=6 --no-owner --no-privileges \
  --file="${DUMP}.part" || fail "pg_dump failed"
mv "${DUMP}.part" "${DUMP}"
pg_restore --list "${DUMP}" >/dev/null || fail "dump is not readable"
ln -sf "$(basename "${DUMP}")" "${BACKUP_DIR}/latest.dump"
log "dump size: $(du -h "${DUMP}" | cut -f1)"

# 2. Off-site snapshot with restic (dump + media). Skipped when no repository is configured
#    (local dumps are still kept — never silently lose the nightly copy).
if [[ -n "${RESTIC_REPOSITORY:-}" ]]; then
  export RESTIC_REPOSITORY RESTIC_PASSWORD
  if ! restic snapshots --quiet >/dev/null 2>&1; then
    log "initialising restic repository ${RESTIC_REPOSITORY}"
    restic init || fail "restic init failed"
  fi
  log "restic backup dump + media"
  restic backup --quiet --tag ertaaniqla --tag "db=$(basename "${DUMP}")" \
    "${DUMP}" "${MEDIA_ROOT}" \
    --exclude "${MEDIA_ROOT}/videos/source" \
    --exclude-caches || fail "restic backup failed"
  log "restic forget (keep ${BACKUP_RETENTION_DAILY:-7}d/${BACKUP_RETENTION_WEEKLY:-4}w/${BACKUP_RETENTION_MONTHLY:-6}m)"
  restic forget --quiet --prune --tag ertaaniqla \
    --keep-daily "${BACKUP_RETENTION_DAILY:-7}" \
    --keep-weekly "${BACKUP_RETENTION_WEEKLY:-4}" \
    --keep-monthly "${BACKUP_RETENTION_MONTHLY:-6}" || fail "restic forget failed"
  restic check --quiet --read-data-subset=5% || fail "restic check failed"
else
  log "RESTIC_REPOSITORY not set — off-site copy skipped (local dumps only)"
fi

# 3. Local retention: keep the last N daily dumps on disk (fast restores)
find "${BACKUP_DIR}" -name 'ertaaniqla-*.dump' -type f -mtime +"${BACKUP_RETENTION_DAILY:-7}" -delete
# 4. Prometheus textfile for the "backup age > 26 h" alert (node_exporter textfile collector)
if [[ -d "${BACKUP_DIR}/metrics" ]]; then
  {
    echo "# HELP ertaaniqla_backup_last_success_timestamp Unix time of the last successful backup"
    echo "# TYPE ertaaniqla_backup_last_success_timestamp gauge"
    echo "ertaaniqla_backup_last_success_timestamp $(date +%s)"
    echo "# HELP ertaaniqla_backup_dump_bytes Size of the last dump"
    echo "# TYPE ertaaniqla_backup_dump_bytes gauge"
    echo "ertaaniqla_backup_dump_bytes $(stat -c %s "${DUMP}")"
  } > "${BACKUP_DIR}/metrics/backup.prom.tmp"
  mv "${BACKUP_DIR}/metrics/backup.prom.tmp" "${BACKUP_DIR}/metrics/backup.prom"
fi
log "OK"
