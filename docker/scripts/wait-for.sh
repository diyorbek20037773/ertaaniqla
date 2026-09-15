#!/usr/bin/env bash
# Wait for Postgres and Redis to accept connections (max ~60 s each). Usage: wait-for.sh DATABASE_URL REDIS_URL
set -euo pipefail

DATABASE_URL="${1:-}"
REDIS_URL="${2:-}"

wait_tcp() {
  local host="$1" port="$2" name="$3" i
  for i in $(seq 1 60); do
    if (exec 3<>"/dev/tcp/${host}/${port}") 2>/dev/null; then
      exec 3>&- 3<&-
      echo "wait-for: ${name} is up (${host}:${port})"
      return 0
    fi
    sleep 1
  done
  echo "wait-for: ${name} at ${host}:${port} did not come up in 60 s" >&2
  return 1
}

host_port() {
  # postgres://user:pass@host:port/db  |  redis://host:port/0
  local url="$1" hp
  hp="${url#*://}"
  hp="${hp##*@}"
  hp="${hp%%/*}"
  hp="${hp%%\?*}"
  local host="${hp%%:*}" port=""
  [[ "$hp" == *:* ]] && port="${hp##*:}"
  echo "${host} ${port}"
}

if [[ -n "$DATABASE_URL" ]]; then
  read -r h p <<<"$(host_port "$DATABASE_URL")"
  wait_tcp "$h" "${p:-5432}" "postgres"
fi
if [[ -n "$REDIS_URL" ]]; then
  read -r h p <<<"$(host_port "$REDIS_URL")"
  wait_tcp "$h" "${p:-6379}" "redis"
fi
