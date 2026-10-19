#!/usr/bin/env bash
# The production nginx config with a stub of Django's HTML cache policy (D-093,
# `make nginx-cache-test`): micro-cache hits, 304s without a CSP header, the language cookie in
# the cache key. Needs Docker; about 20 s. The checks live in docker/nginx/test/cache_check.py.
set -euo pipefail
cd "$(dirname "$0")/../.."
DOMAIN="${DOMAIN:-ertaaniqla.uz}"
IMAGE="${NGINX_IMAGE:-nginx:1.27-alpine}"
PYTHON_IMAGE="${PYTHON_IMAGE:-python:3.12-alpine}"
HERE="$(pwd -W 2>/dev/null || pwd)"
NET="ea-nginx-cache-$$"
export MSYS_NO_PATHCONV=1  # Git Bash on Windows: container paths stay as written

cleanup() {
  docker rm -f "${NET}-web" "${NET}-nginx" >/dev/null 2>&1 || true
  docker network rm "${NET}" >/dev/null 2>&1 || true
}
trap cleanup EXIT
docker network create "${NET}" >/dev/null

docker run -d --name "${NET}-web" --network "${NET}" --network-alias web \
  -v "${HERE}/docker/nginx/test:/t:ro" "${PYTHON_IMAGE}" python /t/cache_check.py origin >/dev/null

docker run -d --name "${NET}-nginx" --network "${NET}" --network-alias "${DOMAIN}" \
  -e DOMAIN="${DOMAIN}" -e DOMAIN_ALT="www.${DOMAIN}" \
  -e STAGING_DOMAIN="staging.${DOMAIN}" -e STAGING_UPSTREAM="staging-web:8000" \
  -e DEV_DOMAIN="dev.${DOMAIN}" -e DEV_UPSTREAM="dev-web:8000" \
  -e SONAR_DOMAIN="sonar.${DOMAIN}" -e SONAR_UPSTREAM="sonarqube:9000" \
  -v "${HERE}/docker/nginx/staging.htpasswd.example:/etc/nginx/staging.htpasswd:ro" \
  -v "${HERE}/docker/nginx/nginx.conf:/etc/nginx/nginx.conf:ro" \
  -v "${HERE}/docker/nginx/snippets:/etc/nginx/snippets:ro" \
  -v "${HERE}/docker/nginx/templates:/etc/nginx/templates:ro" \
  --entrypoint sh "${IMAGE}" -c '
    set -e
    apk add --no-cache --quiet openssl >/dev/null
    LIVE=/etc/letsencrypt/live/$DOMAIN
    mkdir -p $LIVE /srv/static /srv/media /srv/maintenance /var/www/certbot /var/cache/nginx
    openssl req -x509 -nodes -newkey rsa:2048 -days 1 -subj "/CN=$DOMAIN" \
      -keyout $LIVE/privkey.pem -out $LIVE/fullchain.pem >/dev/null 2>&1
    cp $LIVE/fullchain.pem $LIVE/chain.pem
    envsubst "\$DOMAIN \$DOMAIN_ALT \$STAGING_DOMAIN \$STAGING_UPSTREAM \$DEV_DOMAIN \$DEV_UPSTREAM \$SONAR_DOMAIN \$SONAR_UPSTREAM" < /etc/nginx/templates/ertaaniqla.conf.template > /etc/nginx/conf.d/ertaaniqla.conf
    exec nginx -g "daemon off;"
  ' >/dev/null

docker run --rm --network "${NET}" -v "${HERE}/docker/nginx/test:/t:ro" "${PYTHON_IMAGE}" \
  python /t/cache_check.py client "${DOMAIN}" || {  # by name: TLS SNI must match
  docker logs --tail 30 "${NET}-nginx" >&2
  exit 1
}
