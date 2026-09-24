# RUNBOOK — Erta aniqla operations

Audience: the one developer/SRE. Every procedure here has been run at least once (M6 gate).
Spec references: `docs/ENGINEERING_SPEC.md` §11. Threat model: `docs/SECURITY.md`.

| Item | Value |
|---|---|
| Hosts | `ertaaniqla.uz` (canonical), `www.ertaaniqla.uz`, `oncoportal.uz`, `www.oncoportal.uz` → 301 to canonical; staging `staging.ertaaniqla.uz` |
| Server | 1 VPS in Uzbekistan (8 vCPU / 16 GB / 1 TB NVMe), Ubuntu 22.04/24.04, Docker + Compose |
| Layout | `/srv/ertaaniqla/prod` and `/srv/ertaaniqla/staging` = git checkouts; each has its own `.env` (chmod 600) and compose project (`ertaaniqla-prod`, `ertaaniqla-staging`) |
| Compose | `docker compose -p ertaaniqla-<env> -f compose.yml -f compose.prod.yml [--profile monitoring]` — alias below as `dc` |
| Images | `ghcr.io/<org>/ertaaniqla/web:<12-char sha>` built by CI; `:latest` = last green main |
| Data | volumes `pgdata`, `redisdata`, `media`, `static`, `letsencrypt`, `backups`, `nginx-cache`, `prometheus-data`, `grafana-data` |
| RPO / RTO | 24 h / 2 h (nightly dump + restic; restore procedure below) |
| Data residency | VPS and the restic bucket **must** be inside Uzbekistan (ЗРУ-547, `docs/SECURITY.md`) |

```bash
# on the server, as the deploy user
cd /srv/ertaaniqla/prod
alias dc='docker compose -p ertaaniqla-prod -f compose.yml -f compose.prod.yml'
```

## 1. Deploy

### 1.1 Normal (CI/CD)

1. Merge to `main` → CI: quality → frontend → a11y-perf → build (trivy, SBOM, `nginx -t`, compose config) → **deploy-staging** (automatic) → **deploy-prod** (waits for approval on the GitHub `prod` environment).
2. Deploy = `docker/scripts/deploy.sh <env> <tag>` over SSH: `pull` → `run --rm migrate` (migrations + `check --deploy`) → `up -d --no-deps --wait web` (new container must pass `/healthz/` before nginx routes to it) → `up -d worker beat backup nginx` → smoke test (`/readyz/` + 5 pages) → Telegram message.
3. Migrations must be **expand/contract** (spec §11.3): the previous image must still work with the new schema, so a rollback never needs a DB restore.

GitHub configuration (Settings → Environments `staging`, `prod`):
`vars.DEPLOY_HOST`, `vars.DEPLOY_USER` (=`deploy`), `vars.STAGING_DOMAIN`, `vars.PROD_DOMAIN`;
secrets `DEPLOY_SSH_KEY` (private key of the deploy user), `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALERT_CHAT_ID`.
`prod` environment: required reviewers = you.

### 1.2 Manual deploy from a laptop

```bash
DEPLOY_HOST=vps.example.uz IMAGE_BASE=ghcr.io/<org>/ertaaniqla/web SMOKE_URL=https://ertaaniqla.uz \
  make deploy ENV=prod TAG=<12-char sha>
```

### 1.3 Deploy from scratch (new VPS, ≤ 1 h)

```bash
# as root on the fresh VPS
curl -fsSL https://raw.githubusercontent.com/<org>/ertaaniqla/main/scripts/bootstrap_vps.sh | \
  REPO=https://github.com/<org>/ertaaniqla.git ENV_NAME=prod SSH_PUBKEY="ssh-ed25519 AAAA… you" \
  SSH_ALLOW_FROM="<your ip>/32" bash
```
The script installs Docker, creates `deploy`, hardens sshd, ufw (22 restricted / 80 / 443), fail2ban, unattended-upgrades, 4 GB swap, sysctl, clones the repo and prints the remaining steps:

1. Fill `/srv/ertaaniqla/prod/.env` (every variable is documented in `.env.example`; generate `DJANGO_SECRET_KEY`, `PII_ENCRYPTION_KEYS`, `POSTGRES_PASSWORD`, `METRICS_BASIC_AUTH`, `GRAFANA_ADMIN_PASSWORD`; paste Turnstile, Sentry, restic, Telegram values from the password manager).
2. `export WEB_IMAGE=ghcr.io/<org>/ertaaniqla/web:<tag>; dc pull; dc up -d db redis`.
3. Data: `make restore DATE=latest` (see §3) **or** first install: `dc run --rm web python manage.py seed_content --lang uz,ru && dc run --rm web python manage.py import_institutions data/institutions.csv && dc run --rm web python manage.py createsuperuser`.
4. TLS: `DOMAIN=ertaaniqla.uz DOMAIN_ALT="www.ertaaniqla.uz oncoportal.uz www.oncoportal.uz" LETSENCRYPT_EMAIL=… make tls-init` (placeholder cert → nginx up → real cert → reload; renewal is automatic, `nginx-reloader` reloads nginx after each renewal).
5. `make prod-up` (adds the monitoring profile). `bash docker/scripts/smoke.sh https://ertaaniqla.uz`.
6. Point DNS (A/AAAA for all four hosts + staging) at the VPS. Optional Cloudflare in front (DNS + DDoS only, "Full (strict)" TLS mode) — the origin works without it.

Timing on a clean VPS: bootstrap 10 min, image pull 3 min, restore 5 min, TLS 2 min, monitoring 3 min.

## 2. Rollback

* GitHub → Actions → **Rollback** → environment + previous image tag (12-char sha from the CI run or `dc images web`). Same zero-downtime path, then smoke test.
* Manual: `make deploy ENV=prod TAG=<previous sha>`.
* Rollback never reverts migrations. If a migration itself is the problem, restore the DB (§3) **and** roll back the image, then fix forward.

## 3. Backups & restore

* `backup` container (same image as web) runs `docker/scripts/backup_cron.sh`: **02:00 Asia/Tashkent** `backup.sh` → `pg_dump -Fc` into the `backups` volume (`/backups/ertaaniqla-<UTC stamp>.dump`, `latest.dump` symlink, 7 local copies) → `restic backup` of dump + `/srv/media` (raw video uploads excluded) to `RESTIC_REPOSITORY` → `restic forget --keep-daily 7 --keep-weekly 4 --keep-monthly 6 --prune` → `restic check` (5 % data). Success writes `backup.prom` for the `BackupTooOld` alert (> 26 h). Failure → Telegram.
* **Weekly restore test** Sunday 03:30: `restore_test.sh` restores `latest.dump` into a scratch database `ertaaniqla_restore_test` on the same server, counts `wagtailcore_page` (≥ 10), drops it, writes `restore_test.prom`; failure → Telegram + `RestoreTestTooOld` alert after 8 days.
* Run now: `make backup` · `make restore-test`.

### 3.1 Restore (disaster)

```bash
make maintenance-on                                  # nginx serves the maintenance page
dc stop web worker beat
make restore DATE=2026-09-14                         # newest local dump of that day; "latest"; or a path
#   no local dump → fetched from the newest restic snapshot of that day (needs RESTIC_* in .env)
#   the target DB is dropped and recreated, then pg_restore --jobs=2; prints the page count
dc run --rm backup restic restore latest --target / --include /srv/media   # media, if lost
dc up -d web worker beat
make maintenance-off
bash docker/scripts/smoke.sh https://ertaaniqla.uz
```
Restore into a scratch container (what the M6 gate ran):
`docker run -d --name scratch --network ertaaniqla-prod_default -e POSTGRES_PASSWORD=x postgres:16-alpine` then
`dc run --rm -e PGPASSWORD=x backup /scripts/restore.sh latest postgres://postgres:x@scratch:5432/check`.

### 3.2 Media

Media lives in the `media` volume (`/srv/media` in containers) and in every restic snapshot. Raw video uploads (`videos/source/`) are excluded — only transcoded renditions matter; editors can re-upload.

## 4. Incident response

| Symptom | First look | Action |
|---|---|---|
| Telegram: `SiteDown` / smoke failed | `dc ps`, `dc logs --tail 200 nginx web`, `curl -sI https://ertaaniqla.uz/healthz/` | `dc up -d --wait web`; if the image is bad → Rollback (§2) |
| `High5xxRate` | Sentry (release = git sha), `dc logs web` (JSON, `request_id`) | roll back if it started with a deploy; otherwise fix forward |
| `HighLatencyP95` | Grafana overview (DB connections, cache hit ratio, CPU) | check slow queries (`log_min_duration_statement=500` → `dc logs db`), Redis up?, page cache enabled (`PAGE_CACHE_SECONDS`) |
| `PostgresDown` / `RedisDown` | `dc logs db redis`, disk space | `dc up -d db redis`; if disk full → §5 |
| `DiskAlmostFull` | `df -h`, `docker system df`, `/backups`, media size | `docker system prune -f`, lower `BACKUP_RETENTION_DAILY`, move media to S3 (`MEDIA_STORAGE=s3`) |
| `BackupTooOld` | `dc logs backup` | fix credentials / bucket, `make backup` |
| `CertificateExpiringSoon` | `dc logs certbot nginx-reloader` | `dc run --rm certbot renew --force-renewal && dc exec nginx nginx -s reload` |
| `CeleryQueueBacklog` | `dc logs worker`, ffmpeg errors | `dc restart worker`; stuck video → set status `failed` in CMS and re-upload |
| CMS lockout (axes) | `dc run --rm web python manage.py axes_reset` | rotate the password if brute force is suspected |
| Defacement / suspicious edit | Wagtail revision history (`/cms/pages/<id>/history/`) | revert revision, disable the user, rotate secrets (§6) |
| Telegram: `CmsAccountLockout` / `CmsLoginFailuresSpike` | Grafana → *logs & audit* (failed logins, `ip` prefix, `username_hash`) | same prefix repeatedly → block it in nginx; a real editor → `axes_reset_username`; if a known account is targeted, rotate its password and check its 2FA devices |
| Telegram: `PrivilegeChange` | Grafana → *logs & audit*, CMS → Reports → Site history (actor) | unexpected → disable the actor and the target (§6 "CMS user compromise") |
| Slow page, cause unknown | Jaeger UI (`ssh -L 16686:127.0.0.1:16686`), service `ertaaniqla-web`, sort by duration; or click `trace_id` in a Loki line | N+1 → fix the query; slow external call → add a timeout |
| Spam through forms | `dc logs web \| grep ratelimited`, Turnstile dashboard | lower `FORM_RATE`, block IPs in nginx `cms_allowlist`-style snippet, temporary `waffle` flag off |

Maintenance page: `make maintenance-on` / `make maintenance-off` (nginx checks the flag on every request; 503 + `Retry-After`).

Logs: JSON on stdout for every container (`dc logs -f --tail 200 web`), request id in `X-Request-Id` (nginx) = `request_id` (Django), `trace_id` = Jaeger trace. nginx access log anonymises the last IPv4 octet. Searchable history (30 days): Grafana → Explore → Loki or the *logs & audit* dashboard (§9.3).

## 5. Routine operations

| When | What |
|---|---|
| Daily (automatic) | backup 02:00; certbot renew check every 12 h; Dependabot PRs Monday |
| Weekly (automatic) | restore test Sunday 03:30; base image rebuild + trivy (GitHub `Weekly rebuild`, Monday 02:00 UTC) |
| Weekly (you, 10 min) | Grafana overview; Sentry new issues; merge Dependabot PRs after CI green |
| Monthly | `docker system prune -f`; check disk (`df -h`, `docker system df`); review `pip-audit` output in CI |
| Quarterly | full restore drill into a scratch container (§3.1) and a **timed** rebuild on a throw-away VPS (§1.3); rotate `METRICS_BASIC_AUTH` and Grafana password |
| Before launch | `docs/LAUNCH_CHECKLIST.md` (M7) |

Useful commands:
```bash
dc ps; dc top web                              # state
dc exec web python manage.py shell             # Django shell
dc run --rm web python manage.py rebuild_search
dc run --rm web python manage.py purge_pii     # manual retention run (beat does it nightly)
dc exec redis redis-cli info memory
docker exec ertaaniqla-prod-db-1 psql -U ertaaniqla -c 'select count(*) from wagtailcore_page'
ssh -L 3000:127.0.0.1:3000 -L 16686:127.0.0.1:16686 deploy@vps   # Grafana :3000, Jaeger :16686
dc run --rm web python manage.py find_placeholders --fail   # launch gate: no [[TODO]]/[[VERIFY]] live
```

### 5.1 CMS users, roles and 2FA

Roles are the groups **Editor**, **Medical Reviewer**, **Admin** (`apps/users/roles.py`, DECISIONS
D-040/D-041); they and the "Medical review" workflow are re-ensured after every `migrate`
(`manage.py setup_roles` does the same by hand; it never removes permissions).

```bash
dc exec web python manage.py createsuperuser                       # developer account
dc exec web python manage.py shell -c "from apps.users.models import User; from django.contrib.auth.models import Group; u=User.objects.get(username='NAME'); u.groups.set([Group.objects.get(name='Editor')])"
# lost phone: delete the user's TOTP device(s); at the next login they enrol a new one
dc exec web python manage.py shell -c "from django_otp.plugins.otp_totp.models import TOTPDevice; TOTPDevice.objects.filter(user__username='NAME').delete()"
dc run --rm web python manage.py axes_reset_username NAME           # unlock after 5 failed logins
```

- A user is in **one** role. Doctors get *Organisation* filled (shown in the badge).
- `create_demo_staff` is for dev and **staging UAT only** (`--allow-non-debug`); it refuses prod
  settings unless `ENVIRONMENT=staging`. Remove demo users before launch (LAUNCH_CHECKLIST §3).

## 6. Secret rotation

| Secret | How |
|---|---|
| `DJANGO_SECRET_KEY` | new 64-char value in `.env` → `dc up -d web worker beat`. Sessions and password-reset links are invalidated; users log in again. |
| `PII_ENCRYPTION_KEYS` (Fernet) | **prepend** the new key (comma-separated, newest first) → `dc up -d web worker beat` → `dc run --rm web python manage.py rotate_pii_keys` (re-encrypts every row with the newest key) → remove the old key from `.env` → restart. Never remove the old key before the rotation command finished. |
| `POSTGRES_PASSWORD` | `dc exec db psql -U ertaaniqla -c "ALTER USER ertaaniqla PASSWORD 'new'"` → update `.env` → `dc up -d` (web, worker, beat, backup, postgres-exporter read it) |
| `RESTIC_PASSWORD` | `dc run --rm backup restic key add` (enter new) → update `.env` → `restic key remove <old id>` |
| `TURNSTILE_*`, `SENTRY_DSN`, `TELEGRAM_*`, `METRICS_BASIC_AUTH`, `GRAFANA_ADMIN_PASSWORD` | update `.env` → `dc up -d` for the services that use them |
| Deploy SSH key | new key pair → `authorized_keys` of `deploy` → GitHub secret `DEPLOY_SSH_KEY` → remove the old line |
| CMS user compromise | Wagtail → Users → disable; `dc run --rm web python manage.py changepassword <user>`; check revisions; rotate `DJANGO_SECRET_KEY` |

## 7. Staging

Same VPS, second compose project, no public ports. The **production nginx** serves
`https://staging.<DOMAIN>` (certificate includes it — `STAGING_DOMAIN` in `.env`, added by
`init_letsencrypt.sh`), proxies to `ertaaniqla-staging-web-1:8000` on the prod network and
requires HTTP basic auth (`X-Robots-Tag: noindex`).

```bash
# once
sudo -u deploy git clone <repo> /srv/ertaaniqla/staging && cd /srv/ertaaniqla/staging
cp .env.example .env      # ENVIRONMENT=staging, own POSTGRES_PASSWORD/SECRET_KEY/PII keys,
                          # DJANGO_ALLOWED_HOSTS=staging.ertaaniqla.uz, SITE_BASE_URL=https://staging.ertaaniqla.uz,
                          # RESTIC_REPOSITORY empty (local dumps only)
docker run --rm httpd:2.4-alpine htpasswd -nbB editor 's3cret' > /srv/ertaaniqla/staging.htpasswd
# in the PROD .env:  STAGING_DOMAIN=staging.ertaaniqla.uz  STAGING_HTPASSWD=/srv/ertaaniqla/staging.htpasswd
cd /srv/ertaaniqla/prod && dc up -d nginx     # picks up the htpasswd mount + vhost

# run / update (CI does this on every push to main via deploy.sh staging)
cd /srv/ertaaniqla/staging
docker compose -p ertaaniqla-staging -f compose.yml -f compose.prod.yml -f compose.staging.yml up -d
```
`compose.staging.yml` parks nginx/certbot/nginx-reloader in an unused profile, joins the web
container to `ertaaniqla-prod_default`, and keeps backups local. Seed it with
`seed_content` or a copy of prod (`make restore` inside the staging project with a prod dump).

## 8. Scaling notes

* `docker compose up -d --scale web=2` works (stateless web; sessions in Redis; nginx upstream resolves both).
* PgBouncer only when connections exceed ~200 (TODO_HARDENING H-004).
* Media to S3-compatible storage inside Uzbekistan: set `MEDIA_STORAGE=s3` + `S3_*`, run `dc run --rm web python manage.py migrate_media_to_s3` (M8 if needed) — `django-storages` is already wired.

## 9. Delivery pipeline, code analysis, traces, logs, audit (ADR-0005)

```
local:  git commit (pre-commit: ruff, format, secrets) → git push (pre-push: ruff, mypy, pytest -x)
        full local gate before a risky push: make ci-local  (check + tailwind + docker image)
CI:     quality (ruff, mypy, pytest ≥85 %, pip-audit, translations, check --deploy)
        → sonarqube (scan + quality gate)  ┐
        → frontend → a11y-perf             ┴→ build (buildx, trivy, SBOM, push ghcr.io, nginx -t, compose/promtool)
CD:     deploy-staging (auto) → deploy-prod (approval) → smoke → Telegram;  rollback.yml = any tag
ops:    Prometheus+Alertmanager (metrics) · Loki+Alloy (logs, audit) · Jaeger (traces) · Grafana · Sentry
```

### 9.1 Local hooks (once per clone)

```bash
uv run pre-commit install        # installs pre-commit AND pre-push hooks
make ci-local                    # optional full gate (needs Docker)
```

### 9.2 SonarQube (self-hosted)

```bash
# on the VPS, once (vm.max_map_count is set by bootstrap_vps.sh; check: sysctl vm.max_map_count)
sudo -u deploy git clone <repo> /srv/ertaaniqla/sonarqube && cd /srv/ertaaniqla/sonarqube
cp .env.example .env && sed -i "s/^SONAR_DB_PASSWORD=.*/SONAR_DB_PASSWORD=$(openssl rand -hex 24)/" .env
make sonar-up                     # compose project ertaaniqla-sonarqube, joins the prod network
```
DNS: `sonar.<DOMAIN>` → the VPS. Certificate: set `SONAR_DOMAIN` in the **prod** `.env` and add the
name to the existing certificate:
`dc run --rm certbot certonly --webroot -w /var/www/certbot --expand -d <every existing name> -d sonar.<DOMAIN> && dc exec nginx nginx -s reload`
(on a fresh VPS `make tls-init` includes `SONAR_DOMAIN` automatically).

First login `https://sonar.<DOMAIN>` as `admin` / `admin` → change the password immediately →
*Administration → Security*: **Force user authentication = on** → *Projects → Create* `ertaaniqla`
(main branch `master`) → *My Account → Security*: generate a **project analysis token**.
GitHub → Settings → Secrets and variables → Actions: variable `SONAR_HOST_URL=https://sonar.<DOMAIN>`,
secret `SONAR_TOKEN`. From the next push the `sonarqube` job runs; a failed quality gate stops
the image build. Local scan: `make test && SONAR_HOST_URL=… SONAR_TOKEN=… make sonar`.
Upgrade: bump the image tag in `compose.sonarqube.yml`, `make sonar-up`, open
`https://sonar.<DOMAIN>/setup` if it asks for a database migration. No backup needed: every
result is rebuilt by the next scan.

### 9.3 Logs (Loki + Alloy) and audit

Part of `make prod-up` (profile `monitoring`). Alloy reads every container's stdout through the
docker socket (read-only) and ships it to Loki (30 days). Labels: `project`, `service`,
`container`, `stream`, `level`; everything else via `| json`.

```logql
{project="ertaaniqla-prod", service="web"} | json | levelname="ERROR"
{project="ertaaniqla-prod", service="web"} |= "ertaaniqla.audit" | json | event="auth.login_failed"
{project="ertaaniqla-prod", service="nginx"} | json | status >= 500
{project="ertaaniqla-prod"} |= "<request_id or trace_id>"
```
Dashboard *Erta aniqla — logs & audit*: failed logins, lockouts, privilege changes, error volume,
audit trail, error stream (click `trace_id` → Jaeger). Audit alerts live in
`docker/monitoring/loki-rules/fake/audit.yml` (Loki ruler → Alertmanager → Telegram).

The same audit events (except unknown usernames and deleted users) are visible without Grafana
in **CMS → Reports → Site history** ("Login", "Failed login", "Roles", "Personal data viewed", …)
and in each user's / question's history.

Audit events: `auth.login`, `auth.logout`, `auth.login_failed`, `auth.lockout`,
`auth.password_changed`, `user.created`, `user.deleted`, `user.superuser_changed`,
`user.staff_changed`, `user.active_changed`, `user.groups_changed`, `role.permissions_changed`,
`2fa.device_added`, `2fa.device_removed`, `pii.viewed`, `cms.<wagtail action>`.

### 9.4 Traces (OpenTelemetry → Jaeger)

Enable in the prod `.env`: `OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4318` → `dc up -d web worker beat`.
Sampling 10 % (`OTEL_TRACES_SAMPLER_ARG`); switch off instantly with `OTEL_SDK_DISABLED=true`.
UI: `ssh -L 16686:127.0.0.1:16686 deploy@vps` → http://localhost:16686 (services `ertaaniqla-web`,
`ertaaniqla-worker`, `ertaaniqla-beat`). Spans: request → SQL statements (no parameters) → Celery
publish → task. `/healthz/`, `/readyz/`, `/metrics` and static files are not traced. Staging has
no Jaeger: leave the endpoint empty there.

## 10. Local production rehearsal (laptop)

Runs the **production image** with nginx (TLS), worker, beat, backup and the whole `monitoring`
profile on a developer machine, as compose project `ertaaniqla-local` (the dev stack is untouched).
The first run (2026-09-24) found five production bugs that unit tests could not see: healthcheck
`Host: localhost` rejected by `ALLOWED_HOSTS`, Prometheus scrape redirected to https, nginx
keeping the old `web` IP after a recreate (502), worker/beat/backup inheriting the web
healthcheck, and the Celery queue metric never being exported.

1. `.env.localprod` (gitignored): copy `.env.example`, then set `DJANGO_SETTINGS_MODULE=config.settings.prod`,
   `DOMAIN=ertaaniqla.localhost`, `DJANGO_ALLOWED_HOSTS=ertaaniqla.localhost`,
   `DJANGO_CSRF_TRUSTED_ORIGINS=https://ertaaniqla.localhost`, `WEB_IMAGE=ertaaniqla/web:prod`,
   `OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4318`, fresh `DJANGO_SECRET_KEY`, `PII_ENCRYPTION_KEYS`,
   `POSTGRES_PASSWORD`, `METRICS_BASIC_AUTH`, `GRAFANA_ADMIN_PASSWORD`, `TURNSTILE_SECRET_KEY=local-dummy`,
   `TELEGRAM_BOT_TOKEN=000000:dummy`, `TELEGRAM_ALERT_CHAT_ID=-1` (alertmanager refuses to start without them).
   **Never `DOMAIN=localhost`**: prod sends HSTS with `includeSubDomains` for a year and the
   browser would force https on every other local project.
2. Self-signed certificate into the `ertaaniqla-local_letsencrypt` volume (step 1 of
   `docker/scripts/init_letsencrypt.sh`, with `-p ertaaniqla-local` and the local compose files).
3. `make local-prod-up`, then seed:
   `docker exec ertaaniqla-local-web-1 sh -c "python manage.py seed_content --lang uz,ru && python manage.py import_institutions data/institutions.sample.csv && python manage.py rebuild_search"`
   and `createsuperuser` (2FA enrolment happens on first CMS login).
4. Site `https://ertaaniqla.localhost/` (accept the certificate), CMS `/cms/`,
   Grafana `http://127.0.0.1:3000`, Jaeger `http://127.0.0.1:16686`.
   Differences from a server: node-exporter sees the Docker VM (no disk panel), blackbox skips
   certificate verification. `make local-prod-down` stops it; volumes are kept.
