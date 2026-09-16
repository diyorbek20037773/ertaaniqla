#!/usr/bin/env bash
# Weekly automated restore test (spec §11.4): restore the latest dump into a scratch database
# on the same Postgres server (`ertaaniqla_restore_test`), count pages, drop it, alert on
# failure. Runs from backup_cron.sh (Sundays 03:30) and from `make restore-test`.
set -euo pipefail
# shellcheck source=/dev/null
source "$(dirname "$0")/notify.sh"

[[ -n "${DATABASE_URL:-}" ]] || { echo "restore_test: DATABASE_URL not set" >&2; exit 2; }
SCRATCH_URL="${DATABASE_URL%/*}/ertaaniqla_restore_test"
MIN_PAGES="${RESTORE_TEST_MIN_PAGES:-10}"

if OUT="$("$(dirname "$0")/restore.sh" latest "${SCRATCH_URL}" 2>&1)"; then
  PAGES="$(echo "${OUT}" | sed -n 's/.*wagtailcore_page rows: \([0-9]*\).*/\1/p' | tail -1)"
  psql "${DATABASE_URL%/*}/postgres" -q -c 'DROP DATABASE IF EXISTS ertaaniqla_restore_test;' || true
  if [[ "${PAGES:-0}" -ge "${MIN_PAGES}" ]]; then
    echo "restore_test: OK (${PAGES} pages)"
    if [[ -d "${BACKUP_DIR:-/backups}/metrics" ]]; then
      printf '# TYPE ertaaniqla_restore_test_last_success_timestamp gauge\nertaaniqla_restore_test_last_success_timestamp %s\n' "$(date +%s)" \
        > "${BACKUP_DIR:-/backups}/metrics/restore_test.prom"
    fi
    exit 0
  fi
  notify_telegram "❌ Restore test on $(hostname): only ${PAGES:-0} pages restored (< ${MIN_PAGES})"
  echo "restore_test: FAILED — ${PAGES:-0} pages" >&2
  exit 1
fi
echo "${OUT}" >&2
notify_telegram "❌ Restore test FAILED on $(hostname): $(echo "${OUT}" | tail -3)"
exit 1
