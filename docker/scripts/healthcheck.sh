#!/usr/bin/env bash
# Docker HEALTHCHECK for the web role: process answers /healthz/ (no DB/Redis involved).
set -euo pipefail
curl -fsS --max-time 4 -H "Host: ${HEALTHCHECK_HOST:-localhost}" http://127.0.0.1:8000/healthz/ >/dev/null
