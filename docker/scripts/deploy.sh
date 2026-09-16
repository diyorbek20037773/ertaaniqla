#!/usr/bin/env bash
# Deploy over SSH (spec §11.3, RUNBOOK §deploy). Used by `make deploy ENV=staging|prod` and by
# the GitHub Actions deploy job. Zero-downtime: pull → migrate (one-shot) → `up --wait` web
# (health-checked before nginx routes to it) → worker/beat → smoke test → Telegram.
#   deploy.sh staging|prod [IMAGE_TAG]
# Env (local or CI): DEPLOY_HOST, DEPLOY_USER (default deploy), DEPLOY_PATH
# (default /srv/ertaaniqla/<env>), WEB_IMAGE base (default ghcr.io/<org>/ertaaniqla/web).
set -euo pipefail

TARGET="${1:?staging|prod}"
TAG="${2:-latest}"
DEPLOY_USER="${DEPLOY_USER:-deploy}"
DEPLOY_HOST="${DEPLOY_HOST:?DEPLOY_HOST is required}"
DEPLOY_PATH="${DEPLOY_PATH:-/srv/ertaaniqla/${TARGET}}"
IMAGE_BASE="${IMAGE_BASE:?IMAGE_BASE is required (e.g. ghcr.io/org/ertaaniqla/web)}"
PROJECT="ertaaniqla-${TARGET}"
COMPOSE="docker compose -p ${PROJECT} -f compose.yml -f compose.prod.yml"

echo "== deploy ${IMAGE_BASE}:${TAG} → ${TARGET} (${DEPLOY_USER}@${DEPLOY_HOST}:${DEPLOY_PATH})"
ssh -o StrictHostKeyChecking=accept-new "${DEPLOY_USER}@${DEPLOY_HOST}" bash -s <<REMOTE
set -euo pipefail
cd "${DEPLOY_PATH}"
export WEB_IMAGE="${IMAGE_BASE}:${TAG}"
echo "WEB_IMAGE=\${WEB_IMAGE}" > .deploy.env
${COMPOSE} pull --quiet web
${COMPOSE} run --rm --no-deps migrate
${COMPOSE} up -d --no-deps --wait --wait-timeout 120 web
${COMPOSE} up -d --no-deps worker beat backup
${COMPOSE} up -d nginx
docker image prune -f --filter "until=168h" >/dev/null || true
echo "deployed \${WEB_IMAGE}"
REMOTE

DOMAIN_FOR_SMOKE="${SMOKE_URL:-}"
if [[ -n "${DOMAIN_FOR_SMOKE}" ]]; then
  bash "$(dirname "$0")/smoke.sh" "${DOMAIN_FOR_SMOKE}"
fi
