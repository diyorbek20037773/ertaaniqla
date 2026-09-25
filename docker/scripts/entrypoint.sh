#!/usr/bin/env bash
# Container entrypoint. One image, several roles: web | worker | beat | migrate | runserver | backup-cron
set -euo pipefail

ROLE="${1:-web}"
shift || true

wait_for_deps() {
  /scripts/wait-for.sh "${DATABASE_URL:-}" "${REDIS_URL:-}"
}

case "$ROLE" in
  web)
    wait_for_deps
    exec gunicorn config.wsgi:application \
      --bind "0.0.0.0:${PORT:-8000}" \
      --workers "${GUNICORN_WORKERS:-5}" \
      --timeout "${GUNICORN_TIMEOUT:-60}" \
      --graceful-timeout 30 \
      --max-requests 1000 --max-requests-jitter 100 \
      --access-logfile - --error-logfile - \
      --access-logformat '{"remote":"%(h)s","time":"%(t)s","request":"%(r)s","status":%(s)s,"bytes":%(b)s,"referer":"%(f)s","ua":"%(a)s","ms":%(M)s}' \
      "$@"
    ;;
  runserver)
    wait_for_deps
    exec python manage.py runserver 0.0.0.0:8000
    ;;
  worker)
    wait_for_deps
    exec celery -A config worker --loglevel="${LOG_LEVEL:-INFO}" --concurrency "${CELERY_CONCURRENCY:-2}" -Q default,media "$@"
    ;;
  beat)
    wait_for_deps
    exec celery -A config beat --loglevel="${LOG_LEVEL:-INFO}" --schedule /tmp/celerybeat-schedule "$@"
    ;;
  migrate)
    wait_for_deps
    python manage.py migrate --noinput
    python manage.py createcachetable || true
    exec python manage.py check --deploy --fail-level ERROR
    ;;
  backup-cron)
    exec /scripts/backup_cron.sh
    ;;
  *)
    exec "$ROLE" "$@"
    ;;
esac
