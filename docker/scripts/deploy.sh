#!/usr/bin/env bash
# Deploy one environment over SSH (spec §11.3, D-088, RUNBOOK «CI/CD and environments»).
# Used by the GitHub Actions deploy workflow and by `make deploy ENV=dev|staging|prod`.
#
#   deploy.sh dev|staging|prod [IMAGE_TAG]
#
# Zero-downtime order: remember the running image → (optionally) move the server checkout to the
# deployed commit → pull → migrate (one-shot) → `up --wait` web (health-checked before nginx
# routes to it) → worker / beat / backup → smoke test. With AUTO_ROLLBACK=1 a failed smoke test
# redeploys the previous image and the script exits 1.
#
# Env (local or CI):
#   DEPLOY_HOST (required), DEPLOY_USER (default deploy), DEPLOY_PATH (default
#   /srv/ertaaniqla/<env>), IMAGE_BASE (required, e.g. ghcr.io/org/ertaaniqla/web),
#   GIT_SHA (commit to check out on the server, optional), SMOKE_URL / SMOKE_AUTH (user:password
#   for the basic-auth dev / staging hosts), AUTO_ROLLBACK (1 = roll back on a failed smoke test),
#   TELEGRAM_BOT_TOKEN / TELEGRAM_ALERT_CHAT_ID (notifications).
# Compose files: the environment's own `.env` may set COMPOSE_FILE (e.g. adding
# compose.small.yml on the small VPS); otherwise prod uses compose.yml + compose.prod.yml and
# dev / staging add compose.staging.yml (no public ports, behind the prod nginx).
set -euo pipefail

TARGET="${1:?dev|staging|prod}"
TAG="${2:-latest}"
case "${TARGET}" in
  dev | staging) DEFAULT_FILES="compose.yml:compose.prod.yml:compose.staging.yml" ;;
  prod) DEFAULT_FILES="compose.yml:compose.prod.yml" ;;
  *) echo "unknown environment: ${TARGET} (dev|staging|prod)" >&2; exit 2 ;;
esac
DEPLOY_USER="${DEPLOY_USER:-deploy}"
DEPLOY_HOST="${DEPLOY_HOST:?DEPLOY_HOST is required}"
DEPLOY_PATH="${DEPLOY_PATH:-/srv/ertaaniqla/${TARGET}}"
IMAGE_BASE="${IMAGE_BASE:?IMAGE_BASE is required (e.g. ghcr.io/org/ertaaniqla/web)}"
GIT_SHA="${GIT_SHA:-}"
PROJECT="ertaaniqla-${TARGET}"
SCRIPTS="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
[[ -f "${SCRIPTS}/notify.sh" ]] && source "${SCRIPTS}/notify.sh"

# remote_deploy IMAGE — prints the image that ran before on the last line ("none" the first time)
remote_deploy() {
  local image="$1"
  ssh -o StrictHostKeyChecking=accept-new "${DEPLOY_USER}@${DEPLOY_HOST}" bash -s <<REMOTE
set -euo pipefail
cd "${DEPLOY_PATH}"
if [[ -n "${GIT_SHA}" && -d .git ]]; then
  # compose files and nginx config of the same commit as the image
  git fetch --quiet origin && git checkout --quiet --detach "${GIT_SHA}"
fi
# the environment's .env may choose its compose files (COMPOSE_FILE); otherwise the defaults
if ! grep -q '^COMPOSE_FILE=' .env 2>/dev/null; then export COMPOSE_FILE="${DEFAULT_FILES}"; fi
COMPOSE="docker compose -p ${PROJECT}"
previous="\$(sed -n 's/^WEB_IMAGE=//p' .deploy.env 2>/dev/null || true)"
export WEB_IMAGE="${image}"
\${COMPOSE} pull --quiet web
\${COMPOSE} run --rm --no-deps migrate
\${COMPOSE} up -d --no-deps --wait --wait-timeout 120 web
\${COMPOSE} up -d --no-deps worker beat backup
if [[ "${TARGET}" == "prod" ]]; then \${COMPOSE} up -d nginx; fi
if [[ "\${previous}" != "\${WEB_IMAGE}" ]]; then
  echo "WEB_IMAGE=\${previous:-none}" > .deploy.prev.env
fi
echo "WEB_IMAGE=\${WEB_IMAGE}" > .deploy.env
docker image prune -f --filter "until=168h" >/dev/null || true
echo "deployed \${WEB_IMAGE} (previous: \${previous:-none})"
echo "\${previous:-none}"
REMOTE
}

IMAGE="${IMAGE_BASE}:${TAG}"
echo "== deploy ${IMAGE} → ${TARGET} (${DEPLOY_USER}@${DEPLOY_HOST}:${DEPLOY_PATH})"
PREVIOUS="$(remote_deploy "${IMAGE}" | tee /dev/stderr | tail -n 1)"

if [[ -z "${SMOKE_URL:-}" ]]; then
  echo "no SMOKE_URL — smoke test skipped"
  exit 0
fi
if DEPLOY_ENV="${TARGET}" bash "${SCRIPTS}/smoke.sh" "${SMOKE_URL}"; then
  exit 0
fi

if [[ "${AUTO_ROLLBACK:-0}" == "1" && "${PREVIOUS}" != "none" && "${PREVIOUS}" != "${IMAGE}" ]]; then
  echo "== smoke test failed: rolling ${TARGET} back to ${PREVIOUS}"
  type notify_telegram >/dev/null 2>&1 &&
    notify_telegram "↩️ ${TARGET}: smoke test failed for ${IMAGE}, rolling back to ${PREVIOUS}"
  GIT_SHA="" remote_deploy "${PREVIOUS}" >/dev/null
  DEPLOY_ENV="${TARGET}" bash "${SCRIPTS}/smoke.sh" "${SMOKE_URL}" || true
fi
exit 1
