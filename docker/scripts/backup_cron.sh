#!/usr/bin/env bash
# Scheduler for the `backup` container: nightly backup at 02:00 UTC+5 (Tashkent = 21:00 UTC),
# weekly restore test on Sunday 03:30 local. Plain loop — no cron daemon in the image, PID 1
# friendly (tini), logs to stdout.
set -euo pipefail
export TZ="${TZ:-Asia/Tashkent}"
BACKUP_AT="${BACKUP_AT:-02:00}"
RESTORE_TEST_AT="${RESTORE_TEST_AT:-03:30}"
RESTORE_TEST_DOW="${RESTORE_TEST_DOW:-7}"   # 1 = Monday … 7 = Sunday
mkdir -p "${BACKUP_DIR:-/backups}/metrics"

echo "backup-cron: backup daily at ${BACKUP_AT}, restore test weekly (dow ${RESTORE_TEST_DOW}) at ${RESTORE_TEST_AT} (${TZ})"
if [[ "${BACKUP_ON_START:-0}" == "1" ]]; then /scripts/backup.sh || true; fi
LAST_BACKUP_DAY=""; LAST_TEST_DAY=""
while :; do
  NOW="$(date +%H:%M)"; TODAY="$(date +%F)"; DOW="$(date +%u)"
  if [[ "${NOW}" == "${BACKUP_AT}" && "${LAST_BACKUP_DAY}" != "${TODAY}" ]]; then
    LAST_BACKUP_DAY="${TODAY}"
    /scripts/backup.sh || echo "backup-cron: backup failed (see above)" >&2
  fi
  if [[ "${DOW}" == "${RESTORE_TEST_DOW}" && "${NOW}" == "${RESTORE_TEST_AT}" && "${LAST_TEST_DAY}" != "${TODAY}" ]]; then
    LAST_TEST_DAY="${TODAY}"
    /scripts/restore_test.sh || echo "backup-cron: restore test failed (see above)" >&2
  fi
  sleep 30
done
