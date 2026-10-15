#!/usr/bin/env bash
# Post-deploy smoke test (spec §11.3, D-088): /readyz/ + the public pages of every language must
# answer 200 over HTTPS. Dev / staging sit behind basic auth: SMOKE_AUTH=user:password.
#   smoke.sh https://ertaaniqla.uz
# Env: SMOKE_AUTH, DEPLOY_ENV (label in messages), APP_RELEASE, TELEGRAM_* (notify.sh).
set -euo pipefail
BASE="${1:?base URL}"
ENV_LABEL="${DEPLOY_ENV:-$BASE}"
# shellcheck source=/dev/null
[[ -f "$(dirname "$0")/notify.sh" ]] && source "$(dirname "$0")/notify.sh"
AUTH=()
[[ -n "${SMOKE_AUTH:-}" ]] && AUTH=(-u "${SMOKE_AUTH}")
# pages that are always public; a section switched off in the CMS (D-087) is never listed here
PATHS=(/readyz/ /uz/ /ru/ /oz/ /uz/ayollar/ /uz/yangiliklar/ /uz/ayollar/qayerga-murojaat/ /sitemap.xml)
FAILED=0
for path in "${PATHS[@]}"; do
  code="$(curl -sS "${AUTH[@]}" -o /dev/null -w '%{http_code}' --max-time 20 -L "${BASE}${path}" || echo 000)"
  if [[ "${code}" == "200" ]]; then
    echo "OK   ${code} ${path}"
  else
    echo "FAIL ${code} ${path}"; FAILED=1
  fi
done
if ! curl -sS "${AUTH[@]}" --max-time 20 "${BASE}/readyz/" | grep -q '"ok"'; then
  echo "FAIL readyz body"; FAILED=1
fi
if [[ "${FAILED}" == "1" ]]; then
  type notify_telegram >/dev/null 2>&1 && notify_telegram "❌ ${ENV_LABEL}: smoke test failed (${BASE}, ${APP_RELEASE:-unknown})"
  exit 1
fi
type notify_telegram >/dev/null 2>&1 && notify_telegram "✅ ${ENV_LABEL}: deployed and smoke-tested ${BASE} (${APP_RELEASE:-unknown})"
echo "smoke: all good"
