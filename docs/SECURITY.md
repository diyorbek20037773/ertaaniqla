# SECURITY.md — threat model and controls

Scope: the public portal (anonymous readers, public forms), the CMS (`/cms/`, staff only) and
the single VPS. Legal frame: Law of the Republic of Uzbekistan «On Personal Data» (ЗРУ-547):
personal data of citizens is processed and stored on servers **physically located in
Uzbekistan** — the VPS and the backup bucket must both be in UZ (RUNBOOK §0).

## 1. Assets

| Asset | Sensitivity | Where |
|---|---|---|
| Question / feedback contacts (name, phone/e-mail) | health-adjacent PII | `faq_question.contact`, `feedback_feedbacksubmission.contact` — Fernet-encrypted columns; purged 90 / 180 days |
| Patient consent documents | PII (legal) | private Wagtail documents, served only to CMS users (`serve_view` + hook); never under `/media/documents/` via nginx |
| CMS accounts | credentials | Django users, 2FA secrets |
| Content integrity | public trust | Wagtail revisions (every change is recorded and revertible) |
| Secrets | `.env` on the server (chmod 600), GitHub Environment secrets | never in images, logs or git |
| Analytics | pseudonymous | Yandex.Metrika only after consent, IP anonymisation on; no GA/GTM, no ad trackers |

## 2. Threats and controls

### 2.1 Defacement / unauthorised content change
* CMS at `/cms/` (not `/admin/`), Django admin at `/django-admin/` (superusers only).
* **2FA mandatory** for every staff account (`CMS_2FA_REQUIRED=true`, django-otp + wagtail-2fa); strong password validators; 8 h session timeout; `django-axes` lockout (5 failures → 1 h, username + IP); nginx `cms_login` zone 5 r/m per IP; optional IP allow-list (`docker/nginx/snippets/cms_allowlist.conf`).
* Roles (M7): Editor → Medical reviewer → publish (2-step workflow); editors cannot publish.
* Every publish is a revision; `Revert` in the page history is the first response (RUNBOOK §4).
* Detection: Sentry, access log (`request_id`), Telegram alerts on 5xx spikes.

### 2.2 Spam and abuse of forms
* Honeypot field + Cloudflare Turnstile (server-verified) + `django-ratelimit` 5 POST/min/IP (Redis) + nginx `form_post` zone 10 r/m per IP; general 30 r/s burst 60; 40 connections per IP.
* Server-side validation is the truth; HTMX only mirrors it. Questions are never public before a moderator answers **and** the author consented (`consent_to_publish`).
* Data minimisation: contact optional; purge jobs on Celery beat (`faq.purge_contacts`, `feedback.purge_old_submissions`) with tests.

### 2.3 DDoS / resource exhaustion
* nginx in front of gunicorn: micro-cache 10 s for anonymous HTML (`proxy_cache_use_stale`), Django page cache 300 s (version-bump invalidation), rate zones, `limit_conn`, `client_max_body_size 2m` (512 m only under `/cms/`), `proxy_request_buffering off` for uploads.
* Static assets immutable (1 y), media 30 d, video byte-range with `limit_rate` after 4 MB.
* Cloudflare **optional** in front (DNS + DDoS only); the origin must work without it — nothing depends on CF headers.
* Resource limits per container (web 4 GB, db 4 GB, worker 2 GB, redis 640 MB); `restart: unless-stopped`; json-file logs 50 m × 5.

### 2.4 PII leak
* Encryption in transit: TLS 1.2/1.3 only, HSTS preload, OCSP stapling; HTTP → HTTPS 301; secure/HttpOnly/SameSite cookies; `SECURE_PROXY_SSL_HEADER`.
* Encryption at rest: application-level Fernet (`PII_ENCRYPTION_KEYS`, newest-first key list, `rotate_pii_keys` command — RUNBOOK §6); restic repository encrypted; disk encryption on the VPS if the provider offers it.
* Logs: JSON, no bodies, no PII; nginx anonymises the last IPv4 octet / IPv6 tail; Sentry `send_default_pii=False` + scrubber (`apps/core/sentry.py`).
* Uploads: libmagic MIME sniffing, EXIF/XMP (GPS!) stripped from images, size limits, raw video never served (nginx 404 on `videos/source/`), documents permission-checked by Django, optional ClamAV profile.
* Private documents are never cached (`proxy_cache off` under `/documents/`).
* Backups: `pg_dump` contains encrypted PII columns only; the Fernet key is **not** in the backup — keep it in the password manager (losing it = losing contacts, which is acceptable by design).

### 2.5 Admin / server takeover
* SSH: key-only, no root password login, `MaxAuthTries 4`, fail2ban (sshd jail), ufw default deny (22 restricted to your CIDR when `SSH_ALLOW_FROM` is set, else rate-limited; 80; 443).
* Docker daemon local only; containers run as non-root `app` (uid 1000); `nginx-reloader` is the only container with the docker socket (read-only, exec nginx reload only).
* Unattended security upgrades; weekly base-image rebuild + Trivy (fail on HIGH/CRITICAL); Dependabot; `pip-audit` in CI; SBOM per image.
* Secrets: `.env` chmod 600 owned by `deploy`; GitHub secrets scoped per environment; `prod` deploy needs a reviewer approval.
* Headers: CSP nonce-based (`script-src 'nonce-…'`, `frame-ancestors 'none'`, explicit `frame-src` for YouTube/Telegram/Instagram/TikTok, click-to-load facade for the last two), `X-Content-Type-Options`, `X-Frame-Options DENY`, `Referrer-Policy strict-origin-when-cross-origin`, minimal `Permissions-Policy`. Alpine CSP build → no `unsafe-eval`.
* `django check --deploy` runs at image start (`migrate` role) and in the test suite with prod settings.

### 2.6 Supply chain
* Pinned lockfiles (`uv.lock`, `package-lock.json`); no CDN assets (HTMX/Alpine/Leaflet vendored and bundled); fonts self-hosted; images pinned by tag (Prometheus/Grafana/exporters) — Dependabot proposes updates.
* Only official images: `python:3.12-slim`, `postgres:16-alpine`, `redis:7-alpine`, `nginx:1.27-alpine`, `certbot/certbot`, `prom/*`, `grafana/grafana`.

### 2.7 Availability / data loss
* Nightly `pg_dump` + restic (7 d / 4 w / 6 m) to a bucket in UZ, `restic check` after each run, weekly automated restore test, `BackupTooOld` / `RestoreTestTooOld` alerts. RPO 24 h, RTO 2 h (RUNBOOK §3).
* Rebuild from scratch ≤ 1 h (`scripts/bootstrap_vps.sh`, RUNBOOK §1.3).
* Fail-soft: Redis down → cache falls back to in-memory + Sentry alert; Celery down → forms still save, e-mails retried.

## 3. Reporting a vulnerability

E-mail the project office contact in the footer with subject `[security] ertaaniqla.uz`. Please do not open a public issue. Acknowledgement within 2 working days; fix SLA per severity (critical 48 h, high 7 d, others next release).

## 4. Not in scope / accepted risks

* No WAF beyond nginx rules and optional Cloudflare (TODO_HARDENING).
* Brotli is not enabled (official nginx image has no module; gzip + pre-compressed `.gz` assets only — H-015).
* Prometheus/Grafana are reachable only inside the compose network / SSH tunnel; no public monitoring endpoints.
* ClamAV is wired but optional (profile) — CMS users are trusted staff; enable when the CMS opens to more editors.
