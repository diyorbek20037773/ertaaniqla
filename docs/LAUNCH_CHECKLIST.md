# Launch checklist — «Erta aniqla»

Go-live on `ertaaniqla.uz` (M8). Every line has an owner and a way to verify it. Tick in a copy of
this file per launch (`docs/launch/YYYY-MM-DD.md`) — do not edit the template during a launch.
Owners: **Client** (Project Office / Agency), **Content** (copywriter + doctors), **Dev** (developer).

## 1. Client decisions and legal (block launch)

- [ ] Domain `ertaaniqla.uz` bought, DNS A/AAAA → VPS; `oncoportal.uz` decided (alias → 301 or not used) — Client
- [ ] VPS contract and payer (8 vCPU / 16 GB / 1 TB NVMe); SSH access for Dev — Client
- [ ] **Data localisation (ZRU-547) confirmed by the client's lawyer** for the chosen VPS location (D-044) — Client
- [ ] Privacy policy and terms pages (uz + ru) approved and linked in *Site settings* — Client
- [ ] Patient-story consent form (legal text, uz + ru; guardian version for minors) approved — Client
- [ ] Medical disclaimer final wording (footer + tool pages) — Client / Content
- [ ] Legal basis wording in footer: ПП-402 date (22.11.2024 vs 24.11.2024) and ПП-186 verified — Client
- [ ] Yandex.Metrika counter owner; Turnstile site/secret keys; Sentry project — Client / Dev
- [ ] Logo, final colours / Figma design delivered, M5b design integration done — Client / Dev

## 2. Content (block launch)

- [ ] `docker compose exec web python manage.py find_placeholders --fail` → "no placeholders on live content" (no `[[TODO` / `[[VERIFY` left on live pages or site settings) — Content / Dev
- [ ] Every live page exists in uz **and** ru (language switch lands on the same page) — Content
- [ ] Every medical page approved in the **Medical review** workflow (badge shows doctor + date) — Content
- [ ] Screening facts (mammography 45–65/2 y, ultrasound < 45/2 y, HPV 30–50) and ПП-402 referral deadlines verified by a doctor — Content
- [ ] Institution list from the Ministry imported: `import_institutions … --dry-run` clean, then real import; spot-check 10 rows on the map — Client / Dev
- [ ] Hotline numbers, social links, partner logos in *Site settings* — Content
- [ ] Tools pages reviewed, then flags switched on: `manage.py waffle_flag tools_screening --everyone --create` (same for `tools_selfcheck`) — Content / Dev
- [ ] At least: home hero, both section intros, 6 childhood cancer cards, patient route, self-exam steps, FAQ, glossary ≥ 20 terms, materials page — Content
- [ ] Alt text on all images; video transcripts and uz/ru subtitles for published videos — Content
- [ ] `python manage.py check_links --external` → no broken links — Dev

## 3. People and access

- [ ] Real accounts created, each in exactly one role (Editor / Medical Reviewer / Admin); doctors have *Organisation* filled — Dev
- [ ] Every staff user completed 2FA setup; nobody shares accounts — Dev
- [ ] **No demo accounts** on production: `User.objects.filter(username__startswith="demo-")` is empty — Dev
- [ ] Superuser count ≤ 2 (developer + backup person), strong passwords stored in a password manager — Dev
- [ ] Editors trained with `docs/EDITOR_GUIDE_ru.md` / `_uz.md`; UAT sign-off (section 6) — Content

## 4. Infrastructure (RUNBOOK §1–§3)

- [ ] `scripts/bootstrap_vps.sh` run; ufw 22 (restricted) / 80 / 443; fail2ban; unattended-upgrades; swap — Dev
- [ ] `/srv/ertaaniqla/.env` complete (chmod 600): `DJANGO_SECRET_KEY`, `PII_ENCRYPTION_KEYS`, DB/Redis passwords, `TURNSTILE_*`, `SENTRY_DSN`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `DOMAIN`, `LETSENCRYPT_EMAIL`, restic repo + password, Telegram alert bot — Dev
- [ ] `ENVIRONMENT=production`, `CMS_2FA_REQUIRED=true`, `CMS_IP_ALLOWLIST` decided — Dev
- [ ] `make tls-init` → valid certificate; `curl -I https://ertaaniqla.uz` shows HSTS; SSL Labs grade A — Dev
- [ ] `docker compose run --rm web python manage.py check --deploy` → no issues — Dev
- [ ] `make deploy ENV=prod TAG=<release>` → smoke test green (`/readyz/` + 3 pages) — Dev
- [ ] Staging deployed from the same tag, basic auth on — Dev

## 5. Operations

- [ ] Backups: first nightly `backup.sh` ran; `restic snapshots` lists it; **restore test OK** (`make restore-test`) — Dev
- [ ] Monitoring profile up; Grafana reachable via SSH tunnel; test alert reaches Telegram — Dev
- [ ] Loki receives logs (`{project="ertaaniqla-prod"}` in Grafana Explore); *logs & audit* dashboard shows a test failed login; Loki rule `CmsAccountLockout` reaches Telegram once (RUNBOOK §9.3) — Dev
- [ ] `OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4318` set; a trace of `/uz/` visible in Jaeger with no query string / IP in its tags (RUNBOOK §9.4) — Dev
- [ ] SonarQube at `sonar.<DOMAIN>`: admin password changed, *Force user authentication* on, `SONAR_HOST_URL` + `SONAR_TOKEN` in GitHub; first `sonarqube` job green (RUNBOOK §9.2) — Dev
- [ ] Every developer clone: `uv run pre-commit install` (pre-commit + pre-push hooks) — Dev
- [ ] External uptime monitor on `https://ertaaniqla.uz/healthz/` (H-016) — Dev
- [ ] Sentry receives a test event with release = git SHA; PII scrubbed — Dev
- [ ] Celery worker/beat running: `purge_pii --dry-run` prints counts; transcoding of a sample video works — Dev
- [ ] Log rotation (json-file 50m × 5) active; disk usage alert < 80 % — Dev

## 6. Quality gates (paste real output into the launch copy)

- [ ] `make check` green (ruff, mypy, pytest ≥ 85 % coverage, translations uz+ru) — Dev
- [ ] `make e2e` against staging, including `tests/e2e/test_cms_workflow.py` (needs `create_demo_staff --allow-non-debug` on **staging only**) — Dev
- [ ] `make pa11y` (8 URLs, WCAG 2.1 AA, 0 errors) and `make lighthouse` (LCP < 2.5 s, CLS < 0.1, TBT < 200 ms) against staging — Dev
- [ ] **Load test** against staging (not production) — Dev:

      uv run locust -f tests/perf/locustfile.py --host https://staging.ertaaniqla.uz \
          --headless -u 200 -r 20 -t 5m --csv .locust/run --html .locust/report.html

      Budget: 0 failures, page p95 < 300 ms (the locustfile exits 1 otherwise).
      Staging sits behind nginx basic auth: for the test window allow the load-generator IP in the
      staging vhost (or run locust on the VPS against the staging container). Local reference run: see
      PROGRESS.md (M7).
- [ ] `pip-audit` clean, trivy image scan no HIGH/CRITICAL — Dev
- [ ] UAT on real phones (cheap Android + iPhone, 3G throttling): home → section → article → share,
      language switch, directory filter, question form, self-check — Content / Client

## 7. Go-live day

1. Freeze content edits for 1 hour; announce in the team chat.
2. `make backup` on the old/staging data if migrating content; note the snapshot id.
3. Deploy the release tag (`make deploy ENV=prod TAG=…`), wait for the smoke test.
4. `make maintenance-off` (if it was on); purge nginx micro-cache (`docker compose exec nginx sh -c 'rm -rf /var/cache/nginx/*'`).
5. Check manually: `/uz/`, `/ru/`, one article per section, directory map, search «saraton» / «рак»,
   question form (Turnstile visible), `/sitemap.xml`, `/robots.txt`, OG preview in Telegram.
6. Submit sitemaps in Yandex.Webmaster and Google Search Console.
7. Watch Sentry, Grafana (5xx, p95) and Telegram alerts for 2 hours.

## 8. After launch

- [ ] +24 h: no new Sentry errors; backup + restore test of the night OK — Dev
- [ ] +7 d: Metrika traffic review with the client; search queries without results → glossary/synonyms — Client / Content
- [ ] Monthly: dependency updates (Dependabot PRs), `pip-audit`; quarterly restore drill (RUNBOOK) — Dev
- [ ] Support until **31.12.2026**: bug-fix SLA 48 h, hand-over document for the support programmer — Dev
