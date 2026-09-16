#!/usr/bin/env bash
# Post-deploy smoke test (spec §11.3): /readyz/ + 3 public pages must answer 200 over HTTPS.
#   smoke.sh https://ertaaniqla.uz
set -euo pipefail
BASE="${1:?base URL}"
# shellcheck source=/dev/null
[[ -f "$(dirname "$0")/notify.sh" ]] && source "$(dirname "$0")/notify.sh"
FAILED=0
for path in /readyz/ /uz/ /ru/ /uz/ayollar/ /uz/bolalar/ /sitemap.xml; do
  code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 20 -L "${BASE}${path}" || echo 000)"
  if [[ "${code}" == "200" ]]; then
    echo "OK   ${code} ${path}"
  else
    echo "FAIL ${code} ${path}"; FAILED=1
  fi
done
if ! curl -sS --max-time 20 "${BASE}/readyz/" | grep -q '"ok"'; then
  echo "FAIL readyz body"; FAILED=1
fi
if [[ "${FAILED}" == "1" ]]; then
  type notify_telegram >/dev/null 2>&1 && notify_telegram "❌ Smoke test failed for ${BASE}"
  exit 1
fi
type notify_telegram >/dev/null 2>&1 && notify_telegram "✅ Deployed and smoke-tested: ${BASE} (${APP_RELEASE:-unknown})"
echo "smoke: all good"
