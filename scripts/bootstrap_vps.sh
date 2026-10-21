#!/usr/bin/env bash
# Rebuild the VPS from scratch in ≤ 1 h (spec §11.4, RUNBOOK §rebuild). Ubuntu 22.04/24.04,
# run as root once:
#   curl -fsSL https://raw.githubusercontent.com/<org>/ertaaniqla/master/scripts/bootstrap_vps.sh | \
#     REPO=https://github.com/<org>/ertaaniqla.git ENV_NAME=prod bash   (then staging, dev — D-088)
# What it does: docker + compose, `deploy` user, ufw (22 restricted, 80, 443), fail2ban,
# unattended-upgrades, 4 GB swap, sysctl, clone repo into /srv/ertaaniqla/<env>, and prints
# the remaining manual steps (.env, TLS bootstrap, restore).
set -euo pipefail

REPO="${REPO:?REPO (git url) is required}"
ENV_NAME="${ENV_NAME:-prod}"
BRANCH="${BRANCH:-master}"
DEPLOY_USER="${DEPLOY_USER:-deploy}"
SSH_ALLOW_FROM="${SSH_ALLOW_FROM:-}"          # e.g. "213.230.0.0/16 10.8.0.0/24"; empty = any
SSH_PUBKEY="${SSH_PUBKEY:-}"                  # public key for the deploy user (CI + you)
BASE="/srv/ertaaniqla"
APP_DIR="${BASE}/${ENV_NAME}"
SWAP_GB="${SWAP_GB:-4}"

log() { echo "== $*"; }
[[ "$(id -u)" == "0" ]] || { echo "run as root" >&2; exit 1; }
export DEBIAN_FRONTEND=noninteractive

log "1/9 packages"
apt-get update -q
apt-get install -y -q --no-install-recommends \
  ca-certificates curl git gnupg ufw fail2ban unattended-upgrades apt-listchanges \
  htop ncdu jq python3 chrony

log "2/9 docker engine + compose plugin"
if ! command -v docker >/dev/null; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  # shellcheck source=/dev/null
  . /etc/os-release
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -q
  apt-get install -y -q docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi
cat > /etc/docker/daemon.json <<'JSON'
{
  "log-driver": "json-file",
  "log-opts": { "max-size": "50m", "max-file": "5" },
  "live-restore": true
}
JSON
systemctl enable --now docker
systemctl restart docker

log "3/9 deploy user"
if ! id "${DEPLOY_USER}" >/dev/null 2>&1; then
  useradd --create-home --shell /bin/bash --groups docker "${DEPLOY_USER}"
fi
usermod -aG docker "${DEPLOY_USER}"
mkdir -p "/home/${DEPLOY_USER}/.ssh"
if [[ -n "${SSH_PUBKEY}" ]]; then
  grep -qF "${SSH_PUBKEY}" "/home/${DEPLOY_USER}/.ssh/authorized_keys" 2>/dev/null || \
    echo "${SSH_PUBKEY}" >> "/home/${DEPLOY_USER}/.ssh/authorized_keys"
fi
chmod 700 "/home/${DEPLOY_USER}/.ssh"; touch "/home/${DEPLOY_USER}/.ssh/authorized_keys"
chmod 600 "/home/${DEPLOY_USER}/.ssh/authorized_keys"
chown -R "${DEPLOY_USER}:${DEPLOY_USER}" "/home/${DEPLOY_USER}/.ssh"

log "4/9 sshd hardening"
mkdir -p /etc/ssh/sshd_config.d
# sshd keeps the FIRST value it reads and reads the drop-ins in name order: the provider's
# 50-cloud-init.conf (PasswordAuthentication yes) would win over a 90- file (D-099)
rm -f /etc/ssh/sshd_config.d/90-ertaaniqla.conf
cat > /etc/ssh/sshd_config.d/00-ertaaniqla.conf <<'SSHD'
PasswordAuthentication no
PermitRootLogin prohibit-password
KbdInteractiveAuthentication no
PermitEmptyPasswords no
X11Forwarding no
AllowTcpForwarding no
AllowAgentForwarding no
PermitTunnel no
LoginGraceTime 30
MaxAuthTries 3
MaxSessions 4
ClientAliveInterval 300
ClientAliveCountMax 2
SSHD
echo "AllowUsers root ${DEPLOY_USER}" >> /etc/ssh/sshd_config.d/00-ertaaniqla.conf
sshd -t
systemctl reload ssh || systemctl reload sshd || true
sshd -T | grep -qx "passwordauthentication no" || { echo "sshd still accepts passwords" >&2; exit 1; }

log "5/9 firewall (ufw): 22 restricted, 80, 443"
ufw --force reset >/dev/null
ufw default deny incoming
ufw default allow outgoing
if [[ -n "${SSH_ALLOW_FROM}" ]]; then
  for cidr in ${SSH_ALLOW_FROM}; do ufw allow from "${cidr}" to any port 22 proto tcp; done
else
  ufw limit 22/tcp
fi
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

log "6/9 fail2ban + unattended-upgrades"
cat > /etc/fail2ban/jail.d/ertaaniqla.conf <<'JAIL'
[DEFAULT]
bantime  = 1d
findtime = 10m
maxretry = 4
backend  = systemd

[sshd]
enabled = true

# repeat offenders (banned 3 times in a day) are kept out for a week (D-104)
[recidive]
enabled  = true
backend  = auto
logpath  = /var/log/fail2ban.log
bantime  = 7d
findtime = 1d
maxretry = 3
JAIL
systemctl enable --now fail2ban
cat > /etc/apt/apt.conf.d/20auto-upgrades <<'APT'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
APT
sed -i 's|^//\s*"${distro_id}:${distro_codename}-updates";|        "${distro_id}:${distro_codename}-updates";|' /etc/apt/apt.conf.d/50unattended-upgrades || true
sed -i 's|^//Unattended-Upgrade::Automatic-Reboot "false";|Unattended-Upgrade::Automatic-Reboot "false";|' /etc/apt/apt.conf.d/50unattended-upgrades || true

log "7/9 swap ${SWAP_GB} GB + sysctl"
# a provider image may already have a small /swapfile (512 MB on dicloud): replace it
current_mb=$(swapon --show=NAME,SIZE --bytes --noheadings 2>/dev/null | awk '$1=="/swapfile"{print int($2/1048576)}')
if [[ -n "${current_mb}" && "${current_mb}" -lt $((SWAP_GB * 1024 - 64)) ]]; then
  swapoff /swapfile && rm -f /swapfile
fi
if ! swapon --show | grep -q /swapfile; then
  fallocate -l "${SWAP_GB}G" /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=$((SWAP_GB * 1024))
  chmod 600 /swapfile && mkswap /swapfile >/dev/null && swapon /swapfile
  grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi
cat > /etc/sysctl.d/90-ertaaniqla.conf <<'SYSCTL'
vm.swappiness = 10
vm.overcommit_memory = 1
net.core.somaxconn = 4096
net.ipv4.tcp_max_syn_backlog = 4096
net.ipv4.ip_local_port_range = 10240 65535
net.ipv4.tcp_fin_timeout = 15
fs.file-max = 2097152
fs.inotify.max_user_watches = 524288
# SonarQube's embedded Elasticsearch (compose.sonarqube.yml, ADR-0005)
vm.max_map_count = 524288
# network hardening (D-104)
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv6.conf.all.accept_redirects = 0
net.ipv6.conf.default.accept_redirects = 0
net.ipv4.conf.all.accept_source_route = 0
net.ipv6.conf.all.accept_source_route = 0
net.ipv4.conf.all.log_martians = 1
net.ipv4.tcp_syncookies = 1
net.ipv4.icmp_echo_ignore_broadcasts = 1
kernel.kptr_restrict = 2
kernel.dmesg_restrict = 1
SYSCTL
sysctl --system >/dev/null
timedatectl set-timezone Asia/Tashkent || true

log "8/9 repository → ${APP_DIR}"
mkdir -p "${BASE}"
# the checkout belongs to the deploy user; root may still read it (git: "dubious ownership")
git config --global --get-all safe.directory | grep -qx "${APP_DIR}" || \
  git config --global --add safe.directory "${APP_DIR}"
if [[ ! -d "${APP_DIR}/.git" ]]; then
  git clone --branch "${BRANCH}" "${REPO}" "${APP_DIR}"
else
  git -C "${APP_DIR}" fetch --quiet && git -C "${APP_DIR}" checkout --quiet "${BRANCH}" && git -C "${APP_DIR}" pull --quiet
fi
chown -R "${DEPLOY_USER}:${DEPLOY_USER}" "${BASE}"
if [[ ! -f "${APP_DIR}/.env" ]]; then
  cp "${APP_DIR}/.env.example" "${APP_DIR}/.env"
  chmod 600 "${APP_DIR}/.env"; chown "${DEPLOY_USER}:${DEPLOY_USER}" "${APP_DIR}/.env"
  ENV_CREATED=1
else
  ENV_CREATED=0
fi

log "9/9 done"
cat <<NEXT

VPS is prepared. Remaining manual steps (RUNBOOK §deploy from scratch):

 1. Edit ${APP_DIR}/.env $( [[ "${ENV_CREATED}" == "1" ]] && echo "(created from .env.example — fill every secret)" )
      DJANGO_SETTINGS_MODULE=config.settings.prod  ENVIRONMENT=${ENV_NAME}
      DJANGO_SECRET_KEY, PII_ENCRYPTION_KEYS, POSTGRES_PASSWORD, TURNSTILE_*, SENTRY_DSN,
      DOMAIN / DOMAIN_ALT, LETSENCRYPT_EMAIL, RESTIC_*, TELEGRAM_*, METRICS_BASIC_AUTH, GRAFANA_ADMIN_PASSWORD
 2. Log in as ${DEPLOY_USER}, cd ${APP_DIR}
      export WEB_IMAGE=ghcr.io/<org>/ertaaniqla/web:<tag>   (or: make build)
      docker compose -p ertaaniqla-${ENV_NAME} -f compose.yml -f compose.prod.yml pull
      docker compose -p ertaaniqla-${ENV_NAME} -f compose.yml -f compose.prod.yml up -d db redis
 3. Restore a backup (optional): make restore DATE=YYYY-MM-DD   — or seed: ... run --rm web python manage.py seed_content --lang uz,ru
 4. TLS: DOMAIN=... DOMAIN_ALT="..." LETSENCRYPT_EMAIL=... COMPOSE="docker compose -p ertaaniqla-${ENV_NAME} -f compose.yml -f compose.prod.yml" bash docker/scripts/init_letsencrypt.sh
 5. docker compose -p ertaaniqla-${ENV_NAME} -f compose.yml -f compose.prod.yml --profile monitoring up -d
 6. bash docker/scripts/smoke.sh https://<DOMAIN>
NEXT
