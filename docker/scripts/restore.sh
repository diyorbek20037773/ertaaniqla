#!/usr/bin/env bash
# Restore a Postgres dump (spec §11.4 / RUNBOOK §restore).
#   restore.sh [DATE|latest|/path/to.dump] [TARGET_DATABASE_URL]
# DATE = YYYY-MM-DD picks the newest local dump of that day; when no local dump matches and
# RESTIC_REPOSITORY is set, the dump is fetched from the newest restic snapshot of that day.
# TARGET defaults to DATABASE_URL. The target database is dropped and recreated (all
# connections terminated) — for production this is the documented disaster path only.
set -euo pipefail

WHAT="${1:-latest}"
TARGET="${2:-${DATABASE_URL:-}}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
[[ -n "${TARGET}" ]] || { echo "restore: no target DATABASE_URL" >&2; exit 2; }

pick_dump() {
  local what="$1"
  if [[ -f "$what" ]]; then echo "$what"; return; fi
  if [[ "$what" == "latest" ]]; then
    ls -1t "${BACKUP_DIR}"/ertaaniqla-*.dump 2>/dev/null | head -1; return
  fi
  ls -1t "${BACKUP_DIR}"/ertaaniqla-"${what}"T*.dump 2>/dev/null | head -1
}

DUMP="$(pick_dump "${WHAT}")"
if [[ -z "${DUMP}" && -n "${RESTIC_REPOSITORY:-}" ]]; then
  echo "restore: no local dump for ${WHAT}; fetching from restic"
  export RESTIC_REPOSITORY RESTIC_PASSWORD
  SNAP="$(restic snapshots --tag ertaaniqla --json | python3 -c '
import json, sys
what = sys.argv[1]
snaps = [s for s in json.load(sys.stdin) if what == "latest" or s["time"].startswith(what)]
print(snaps[-1]["short_id"] if snaps else "")' "${WHAT}")"
  [[ -n "${SNAP}" ]] || { echo "restore: no restic snapshot for ${WHAT}" >&2; exit 3; }
  mkdir -p "${BACKUP_DIR}/restored"
  restic restore "${SNAP}" --target "${BACKUP_DIR}/restored" --include "${BACKUP_DIR}/*.dump"
  DUMP="$(ls -1t "${BACKUP_DIR}/restored${BACKUP_DIR}"/ertaaniqla-*.dump | head -1)"
fi
[[ -n "${DUMP}" && -f "${DUMP}" ]] || { echo "restore: dump not found for ${WHAT}" >&2; exit 3; }
echo "restore: ${DUMP} → ${TARGET%%\?*}"

# split the URL: connect to `postgres` maintenance db to drop/create the target
DBNAME="${TARGET##*/}"; DBNAME="${DBNAME%%\?*}"
ADMIN_URL="${TARGET%/*}/postgres"

psql "${ADMIN_URL}" -v ON_ERROR_STOP=1 -q \
  -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${DBNAME}' AND pid <> pg_backend_pid();" \
  -c "DROP DATABASE IF EXISTS \"${DBNAME}\";" \
  -c "CREATE DATABASE \"${DBNAME}\";"
pg_restore --dbname="${TARGET}" --no-owner --no-privileges --jobs=2 --exit-on-error "${DUMP}"
PAGES="$(psql "${TARGET}" -tAc 'SELECT count(*) FROM wagtailcore_page;')"
echo "restore: OK — wagtailcore_page rows: ${PAGES}"
