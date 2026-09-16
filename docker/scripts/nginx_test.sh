#!/usr/bin/env bash
# `nginx -t` for the production config inside the real image (M6 gate, `make nginx-test`).
# Renders the template with envsubst exactly like the image entrypoint, mounts the snippets and
# a throw-away self-signed certificate, then runs nginx -t.
set -euo pipefail
cd "$(dirname "$0")/../.."
DOMAIN="${DOMAIN:-ertaaniqla.uz}"
DOMAIN_ALT="${DOMAIN_ALT:-www.ertaaniqla.uz oncoportal.uz www.oncoportal.uz}"
IMAGE="${NGINX_IMAGE:-nginx:1.27-alpine}"

docker run --rm --add-host web:127.0.0.1 \
  -e DOMAIN="${DOMAIN}" -e DOMAIN_ALT="${DOMAIN_ALT}" \
  -e STAGING_DOMAIN="staging.${DOMAIN}" -e STAGING_UPSTREAM="ertaaniqla-staging-web-1:8000" \
  -v "$(pwd -W 2>/dev/null || pwd)/docker/nginx/staging.htpasswd.example:/etc/nginx/staging.htpasswd:ro" \
  -v "$(pwd -W 2>/dev/null || pwd)/docker/nginx/nginx.conf:/etc/nginx/nginx.conf:ro" \
  -v "$(pwd -W 2>/dev/null || pwd)/docker/nginx/snippets:/etc/nginx/snippets:ro" \
  -v "$(pwd -W 2>/dev/null || pwd)/docker/nginx/templates:/etc/nginx/templates:ro" \
  --entrypoint sh "${IMAGE}" -c '
    set -e
    apk add --no-cache --quiet openssl >/dev/null
    LIVE=/etc/letsencrypt/live/$DOMAIN
    mkdir -p $LIVE /srv/static /srv/media /srv/maintenance /var/www/certbot /var/cache/nginx
    openssl req -x509 -nodes -newkey rsa:2048 -days 1 -subj "/CN=$DOMAIN" \
      -keyout $LIVE/privkey.pem -out $LIVE/fullchain.pem >/dev/null 2>&1
    cp $LIVE/fullchain.pem $LIVE/chain.pem
    envsubst "\$DOMAIN \$DOMAIN_ALT \$STAGING_DOMAIN \$STAGING_UPSTREAM" < /etc/nginx/templates/ertaaniqla.conf.template > /etc/nginx/conf.d/ertaaniqla.conf
    nginx -t
  '
