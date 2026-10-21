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

# Keepalives (D-103): "pull --quiet" prints nothing for minutes on the 10 Mbit/s VPS, and the
# GitHub runner's network drops a silent connection after ~4 min ("client_loop: Broken pipe").
SSH_OPTS=(-o StrictHostKeyChecking=accept-new -o ServerAliveInterval=20 -o ServerAliveCountMax=15)

# remote_deploy IMAGE — prints the image that ran before on the last line ("none" the first time)
remote_deploy() {
  local image="$1"
  ssh "${SSH_OPTS[@]}" "${DEPLOY_USER}@${DEPLOY_HOST}" bash -s <<REMOTE
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
# This script reaches the server on stdin (ssh … bash -s): every compose call reads /dev/null
# instead, or the first one that reads stdin ("run") swallows the rest of the script (D-100).
\${COMPOSE} pull --quiet web < /dev/null
\${COMPOSE} run --rm --no-deps -T migrate < /dev/null
\${COMPOSE} up -d --no-deps --wait --wait-timeout 120 web < /dev/null
running="\$(docker inspect --format '{{.Config.Image}}' "\$(\${COMPOSE} ps -q web < /dev/null)")"
if [[ "\${running}" != "\${WEB_IMAGE}" ]]; then
  echo "web runs \${running}, not \${WEB_IMAGE}" >&2
  exit 1
fi
# only now keep .env in step: a later hand-run "docker compose up" must neither bring the old
# image back nor start one that never came up (D-100)
if grep -q '^WEB_IMAGE=' .env; then sed -i "s|^WEB_IMAGE=.*|WEB_IMAGE=${image}|" .env; fi
if grep -q '^APP_RELEASE=' .env; then sed -i "s|^APP_RELEASE=.*|APP_RELEASE=${image##*:}|" .env; fi
\${COMPOSE} up -d --no-deps worker beat backup < /dev/null
if [[ "${TARGET}" == "prod" ]]; then \${COMPOSE} up -d nginx < /dev/null; fi
if [[ "\${previous}" != "\${WEB_IMAGE}" ]]; then
  echo "WEB_IMAGE=\${previous:-none}" > .deploy.prev.env
fi
echo "WEB_IMAGE=\${WEB_IMAGE}" > .deploy.env
docker image prune -f --filter "until=168h" >/dev/null || true
echo "deployed \${WEB_IMAGE} (previous: \${previous:-none})"
REMOTE
}

IMAGE="${IMAGE_BASE}:${TAG}"
echo "== deploy ${IMAGE} → ${TARGET} (${DEPLOY_USER}@${DEPLOY_HOST}:${DEPLOY_PATH})"
# the image to roll back to, read before anything changes (a failed server step prints nothing)
PREVIOUS="$(ssh "${SSH_OPTS[@]}" "${DEPLOY_USER}@${DEPLOY_HOST}" \
  "sed -n 's/^WEB_IMAGE=//p' '${DEPLOY_PATH}/.deploy.env' 2>/dev/null" < /dev/null || true)"
PREVIOUS="${PREVIOUS:-none}"

if remote_deploy "${IMAGE}"; then
  if [[ -z "${SMOKE_URL:-}" ]]; then
    echo "no SMOKE_URL — smoke test skipped"
    exit 0
  fi
  if DEPLOY_ENV="${TARGET}" bash "${SCRIPTS}/smoke.sh" "${SMOKE_URL}"; then
    exit 0
  fi
  REASON="smoke test failed"
else
  REASON="the server step failed"
fi

if [[ "${AUTO_ROLLBACK:-0}" == "1" && "${PREVIOUS}" != "none" && "${PREVIOUS}" != "${IMAGE}" ]]; then
  echo "== ${REASON}: rolling ${TARGET} back to ${PREVIOUS}"
  type notify_telegram >/dev/null 2>&1 &&
    notify_telegram "↩️ ${TARGET}: ${REASON} for ${IMAGE}, rolling back to ${PREVIOUS}"
  GIT_SHA="" remote_deploy "${PREVIOUS}" || true
  if [[ -n "${SMOKE_URL:-}" ]]; then DEPLOY_ENV="${TARGET}" bash "${SCRIPTS}/smoke.sh" "${SMOKE_URL}" || true; fi
else
  echo "== ${REASON} (no automatic rollback)"
fi
exit 1
