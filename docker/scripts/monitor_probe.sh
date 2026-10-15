#!/usr/bin/env bash
# External production probe (D-088, monitor.yml): health endpoints, the main pages of every
# language, response time and TLS certificate expiry. Prints a Markdown report; exit 1 = incident.
# A failing check is retried once after RETRY_SECONDS so one slow response is not an incident.
#   monitor_probe.sh https://ertaaniqla.uz
set -euo pipefail
BASE="${1:?base URL}"
SLOW_SECONDS="${SLOW_SECONDS:-5}"
RETRY_SECONDS="${RETRY_SECONDS:-30}"
CERT_FAIL_DAYS="${CERT_FAIL_DAYS:-7}"
CERT_WARN_DAYS="${CERT_WARN_DAYS:-21}"
PATHS=(/healthz/ /readyz/ /uz/ /ru/ /oz/ /uz/yangiliklar/ /uz/ayollar/qayerga-murojaat/)

check() {  # check PATH → "code seconds"
  curl -sS -o /dev/null -L --max-time 20 -w '%{http_code} %{time_total}' "${BASE}$1" 2>/dev/null || echo "000 20"
}

FAILED=0
echo "| check | result |"
echo "|---|---|"
for path in "${PATHS[@]}"; do
  read -r code seconds <<<"$(check "${path}")"
  if [[ "${code}" != "200" ]]; then
    sleep "${RETRY_SECONDS}"
    read -r code seconds <<<"$(check "${path}")"
  fi
  slow="$(awk -v s="${seconds}" -v max="${SLOW_SECONDS}" 'BEGIN { print (s > max) ? 1 : 0 }')"
  if [[ "${code}" != "200" ]]; then
    echo "| \`${path}\` | ❌ HTTP ${code} |"; FAILED=1
  elif [[ "${slow}" == "1" ]]; then
    echo "| \`${path}\` | ⚠️ slow: ${seconds} s |"
  else
    echo "| \`${path}\` | ✅ ${seconds} s |"
  fi
done

if ! curl -sS --max-time 20 "${BASE}/readyz/" 2>/dev/null | grep -q '"ok"'; then
  echo "| readyz body | ❌ not ok (database / cache / storage) |"; FAILED=1
fi

host="${BASE#https://}"; host="${host%%/*}"
if [[ "${BASE}" == https://* ]]; then
  end="$(echo | openssl s_client -servername "${host}" -connect "${host}:443" 2>/dev/null \
    | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2 || true)"
  if [[ -z "${end}" ]]; then
    echo "| TLS certificate | ❌ unreadable |"; FAILED=1
  else
    days=$(( ($(date -d "${end}" +%s) - $(date +%s)) / 86400 ))
    if (( days < CERT_FAIL_DAYS )); then
      echo "| TLS certificate | ❌ expires in ${days} days (renewal is failing) |"; FAILED=1
    elif (( days < CERT_WARN_DAYS )); then
      echo "| TLS certificate | ⚠️ expires in ${days} days |"
    else
      echo "| TLS certificate | ✅ ${days} days left |"
    fi
  fi
fi
exit "${FAILED}"
