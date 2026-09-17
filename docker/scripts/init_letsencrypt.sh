#!/usr/bin/env bash
# First-time TLS bootstrap (spec §11.2, RUNBOOK §TLS). Run once on the VPS from the repo root:
#   DOMAIN=ertaaniqla.uz DOMAIN_ALT="www.ertaaniqla.uz oncoportal.uz www.oncoportal.uz" \
#   LETSENCRYPT_EMAIL=admin@ertaaniqla.uz bash docker/scripts/init_letsencrypt.sh
# 1) writes a self-signed placeholder into the `letsencrypt` volume so nginx can start,
# 2) starts nginx, 3) requests the real certificate over the webroot challenge, 4) reloads.
# Afterwards the `certbot` service renews automatically every 12 h.
set -euo pipefail

: "${DOMAIN:?DOMAIN is required}"
DOMAIN_ALT="${DOMAIN_ALT:-}"
STAGING_DOMAIN="${STAGING_DOMAIN:-}"      # included in the certificate when set
SONAR_DOMAIN="${SONAR_DOMAIN:-}"          # included in the certificate when set (ADR-0005)
LETSENCRYPT_EMAIL="${LETSENCRYPT_EMAIL:?LETSENCRYPT_EMAIL is required}"
STAGING="${LETSENCRYPT_STAGING:-0}"     # 1 = Let's Encrypt staging CA (no rate limits)
COMPOSE="${COMPOSE:-docker compose -f compose.yml -f compose.prod.yml}"
LIVE="/etc/letsencrypt/live/${DOMAIN}"

echo "== 1/4 placeholder certificate for ${DOMAIN}"
${COMPOSE} run --rm --entrypoint sh certbot -c "
  set -e
  if [ -f ${LIVE}/fullchain.pem ] && ! grep -q 'placeholder' ${LIVE}/README 2>/dev/null; then
    echo 'real certificate already present — nothing to do'; exit 0
  fi
  mkdir -p ${LIVE}
  openssl req -x509 -nodes -newkey rsa:2048 -days 2 -subj '/CN=${DOMAIN}' \
    -keyout ${LIVE}/privkey.pem -out ${LIVE}/fullchain.pem >/dev/null 2>&1
  cp ${LIVE}/fullchain.pem ${LIVE}/chain.pem
  echo placeholder > ${LIVE}/README
"

echo "== 2/4 starting nginx"
${COMPOSE} up -d nginx
sleep 3

echo "== 3/4 requesting the certificate"
DOMAIN_ARGS="-d ${DOMAIN}"
for alt in ${DOMAIN_ALT} ${STAGING_DOMAIN} ${SONAR_DOMAIN}; do DOMAIN_ARGS="${DOMAIN_ARGS} -d ${alt}"; done
STAGING_ARG=""; [[ "${STAGING}" == "1" ]] && STAGING_ARG="--staging"
${COMPOSE} run --rm --entrypoint sh certbot -c "
  set -e
  rm -rf ${LIVE} /etc/letsencrypt/archive/${DOMAIN} /etc/letsencrypt/renewal/${DOMAIN}.conf
  certbot certonly --webroot -w /var/www/certbot ${DOMAIN_ARGS} \
    --email ${LETSENCRYPT_EMAIL} --agree-tos --no-eff-email --non-interactive \
    --rsa-key-size 4096 ${STAGING_ARG}
"

echo "== 4/4 reloading nginx"
${COMPOSE} exec nginx nginx -s reload
echo "done: https://${DOMAIN}"
