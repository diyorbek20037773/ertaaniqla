# PROGRESS.md — autopilot state (read this first after a context reset)

> Written as instructions to a future me who remembers nothing.
> Rules: AUTOPILOT_PROMPT.md. Constitution: docs/ENGINEERING_SPEC.md. Spec: docs/TZ_concept_ru.md (wins).
> Narrate in Uzbek; code/commits/dev docs in English.

## Environment facts (verified 2026-09-15)

- Windows 11, Git Bash + PowerShell. Python 3.12.0 at `C:/Users/diyor/AppData/Local/Programs/Python/Python312/python.exe`; `uv 0.12.9` manages the venv (`.venv`, Python 3.12).
- Docker Desktop 29.x installed; daemon must be started manually (`Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"`).
- Local PostgreSQL 18 service running on 5432 (used only as fallback; compose runs postgres:16-alpine on **5433** to avoid the clash).
- gettext at `C:/Users/diyor/AppData/Local/Programs/gettext-iconv/bin` (prepend to PATH before `makemessages` / `compilemessages`).
- `winget` is not on PATH inside the PowerShell tool: call `$env:LOCALAPPDATA\Microsoft\WindowsApps\winget.exe`. GNU make / ffmpeg winget installs were re-run 2026-09-15 (verify with `Get-Command make, ffmpeg` after refreshing PATH).
- Node 22 available; `npm run build` → `static/dist/` (CSS 2.6 KB gz, JS 37.7 KB gz; budgets 40/50 KB).
- Host port 8000 is taken by another compose project (`uvaleniya`); `.env` sets `WEB_PORT=8001` and `INSTALL_DEV=1` (dev image with debug toolbar).
- Docker on Windows/Git Bash: prefix `MSYS_NO_PATHCONV=1` when passing `-e VAR=/path` or `-v` (otherwise `/tmp/...` becomes `C:/Users/...` **inside the container/bind mount** — this once created a `C:` directory in the repo that broke the image build context).
- Tools without make: `.venv/Scripts/ruff`, `.venv/Scripts/mypy`, `.venv/Scripts/python -m pytest --cov`, `.venv/Scripts/python scripts/check_translations.py`.

## DESIGN RULE (developer instruction, 2026-09-15 — applies to every milestone)

The UI design is made by a separate designer and arrives later (Figma). Until then:

- Build everything **design-independent at full quality**: models, blocks, i18n, seed tree, search,
  media, directory, tools, forms, security, DevOps, tests.
- Visual layer = **clean WIREFRAME level only**: semantic HTML, correct component structure in
  `templates/components/`, tokens in `static/src/tokens.css`, neutral grey palette, system font,
  simple spacing. **No** visual polish, illustrations, animations, custom icons, hero art,
  pixel-level styling.
- Every visual decision lives in exactly two places: `static/src/tokens.css` and
  `templates/components/`. Designer's work must be applicable later **without touching Python**.
- M2 and M5: skip the "beautiful design" parts; keep accessibility, performance budgets, print CSS,
  structure.
- New milestone **M5b — Design integration** (run when Figma arrives).
- Deliver `docs/COMPONENT_INVENTORY.md` (ru + uz): every UI component and page template with
  purpose, fields, states (mobile/desktop, empty/error) — hand-off document for the designer.
  Created in M1 once the component set exists; kept current in every later milestone.

## Decisions taken so far (details in docs/DECISIONS.md)

- D-001 Django **5.2 LTS** + Wagtail **7.0 LTS** instead of 5.1/6.x (EOL; wagtail-localize needs ≥5.2/≥7.0). ADR-0001.
- D-002 Compose Postgres published on host port 5433.
- D-003 Wireframe-only UI until Figma arrives (see DESIGN RULE).
- D-004 In-house `EncryptedTextField` (Fernet). D-005 custom User/Image/Document models in M0.
- D-006 static Celery beat schedule. D-007 CMS at `/cms/`. D-008 Turnstile. D-009 FTS config `ertaaniqla`.
- D-010 DirectoryPage inside women section + short-URL redirects. D-011 provider iframes, no oEmbed. D-012 two banners (site + home). D-013 women care/after `show_in_menus=False`. D-014 `<details>` nav/accordions. D-015 regions/services/locales via data migrations.
- D-016…D-026 (M2–M4): bilingual search, OG task, video pipeline, consent in `clean()`, upload hardening, Leaflet bundle, tool texts in CMS, no separate route page, anti-spam stack, retention jobs, glossary tooltips.
- D-027 Alpine CSP build. D-028 page cache = version-bump middleware. D-029 Metrika only after consent. D-030 share bar order + story image. D-031 `MaterialsPage` in media_library. D-032 pa11y/Lighthouse CI job.
- D-033 nginx official image + envsubst templates, gzip only. D-034 pg_dump + restic, weekly restore test into scratch DB. D-035 bash-loop scheduler. D-036 monitoring compose profile. D-037 staging = 2nd compose project behind prod nginx. D-038 PG client 16 pinned. D-039 TLS placeholder bootstrap.

## Milestones

- [x] Read ENGINEERING_SPEC, TZ, AUTOPILOT_PROMPT fully.
- [x] **M0 — Scaffold** — DONE, tagged `m0` (commit d87c7b2)
  - [x] PROGRESS.md (this file)
  - [x] pyproject.toml + uv.lock, .python-version (Django 5.2.17, Wagtail 7.0.x, 136 packages)
  - [x] config/ (settings base/dev/prod/test/build, urls, wsgi, asgi, celery)
  - [x] apps/: all 14 apps registered; `core` (healthz/readyz/robots/sitemaps/metrics, request-id middleware, JSON logging, Sentry scrub, `EncryptedTextField`, FTS migration), `users.User`, `media_library.PortalImage/PortalDocument`
  - [x] templates/base.html + components (header, nav, lang_switch, footer), 404/429/500/lockout; static/src (tokens.css, input.css, main.js); package.json; tailwind.config.js; `npm run build` OK
  - [x] Makefile (all §15 targets), compose.yml/.dev/.prod, docker/web/Dockerfile (multi-stage, `INSTALL_DEV` arg), docker/scripts (entrypoint, wait-for, healthcheck). docker/nginx + backup scripts → M6
  - [x] .env.example (every variable), .gitignore, .dockerignore, .editorconfig, .pre-commit-config.yaml
  - [x] .github/workflows/ci.yml (quality · frontend budgets · build + trivy)
  - [x] docs/TZ_TRACE.md, docs/DECISIONS.md, docs/ADR/0001-stack.md, 0002-dmed.md, 0003-i18n.md, docs/TODO_HARDENING.md
  - [x] tests: 36 tests (infra, fields, sentry, degraded paths, prod settings + `check --deploy`), coverage 94.9 %
  - [x] locale/uz + ru `django.po` filled (46 strings, real Uzbek Latin + Russian) and compiled; translation check green
  - [x] ruff clean · mypy clean (50 files) · pip-audit clean · prod image builds
  - [x] Gate: compose web on :8001 → healthz 200, readyz {db ok, cache ok}, / → /uz/, /uz/ 200, /cms/login/ 200, 404 page OK; tagged `m0`
- [x] **M1 — Content model + i18n + seeded tree** — DONE, tagged `m1`
  - [x] `BasePage` (og_image, noindex, reviewed_by/at, medically_verified, `get_section`, `reading_time`, `verified_badge`) — `apps/core/models.py`
  - [x] `HomePage` (hero, section cards, stats ≤3, featured articles ≤6 / videos ≤3, home banner), `SectionIndexPage` (section_key, tagline, colours, icon, intro, `get_menu_items`), `TopicIndexPage`, `ArticlePage`, `DirectoryPage` (list + GET filters; map/HTMX/CSV in M4), `Video` snippet (fields per spec; transcoding M3), `Term`, `Institution/Region/Service` (+ data migration: 14 regions, 8 services)
  - [x] all 18 blocks of spec §4.3 in `apps/articles/blocks.py` + `templates/blocks/*.html` + clean/render tests; embeds parsed offline (`apps/articles/embeds.py`, D-011)
  - [x] `SiteSettings` (hotline, socials, footer/disclaimer/legal uz+ru, emergency banner, partner logos, Metrika)
  - [x] Locales uz/ru via core migration 0002; hreflang + x-default; canonical = Wagtail Site hostname; language switcher → translated counterpart → section → root; `uz_Cyrl` .po stub
  - [x] `seed_content --lang uz,ru` — full TZ tree (2 sections, 4 topics, 17 articles, 1 directory, home) ×2 locales, glossary terms, redirects `/uz/qayerga-murojaat/`, idempotent (2nd run: created=0 updated=0, ~2.5 s)
  - [x] base layout, `data-section` theming + CMS colour override (nonce'd style), mega-menu (`<details>`, 5 items/section, cached 1 h + signal invalidation), breadcrumbs, footer (disclaimer, hotline, socials, partners), `print.css` skeleton, `components.css`
  - [x] `docs/COMPONENT_INVENTORY.md` (ru+uz), `docs/CONTENT_MODEL.md`, DECISIONS D-010…D-015, TZ_TRACE rows updated
  - [x] 238 new UI strings translated uz+ru (`scripts/translations_m1.py`), check green
  - [x] Gate: `test_every_live_page_returns_200_in_both_languages` (54 pages), `assertNumQueries` ≤ 40 on section index, translations complete, Playwright 390 px screenshots (10) in `tests/e2e/screenshots/`, menu + language-switch e2e green; coverage 94.65 %; ruff/mypy clean; `check --deploy` OK
- [x] **M2 — Components, home, search** — DONE, tagged `m2` (structure + a11y only, D-003)
  - [x] every block rendered with structure/a11y in both locales (`test_every_block_renders_in_both_locales`); steps, columns, cards, symptom urgency (colour + icon + text), stat, callouts, table, faq `<details>`, quote, cta, embed click-to-load — all from M1
  - [x] home: section cards, stats strip, featured articles/videos, settings banner (M1) — verified by `tests/home`
  - [x] search: `apps/search` — Postgres FTS (`ertaaniqla` = simple + unaccent) over both locales, uz/ru synonym groups, Latin↔Cyrillic transliteration, apostrophe normalisation, FTS + title autocomplete merge, visitor language first; view at `/uz/qidiruv/?q=` / `/ru/poisk/?q=` (translated URL segment), HTMX search-as-you-type + plain GET fallback; `rebuild_search` command
  - [x] axe-core (Playwright init script, CSP-safe) on 6 pages: 0 serious/critical (children brand darkened to #8a5a00 for 4.5:1)
  - [x] Gate: search tests (uz "saraton" → ru «рак» pages; «скрининг» → `/uz/ayollar/skrining/`), block render both locales, a11y e2e green, coverage 95 %
- [x] **M3 — Media & stories** — DONE, tagged `m3`
  - [x] `media_library.services`: ffmpeg/ffprobe pipeline (720p/480p H.264 + poster → default storage, status machine uploaded→processing→ready/failed with error text), Celery task `media_library.transcode_video` (queue `media`, enqueued on upload via post_save + on_commit); MIME sniffing (libmagic) for videos/documents/VTT, WebVTT check, EXIF/XMP strip (+ orientation) on image upload
  - [x] private documents: `before_serve_document` hook → 404 for anonymous / users without `choose_document`
  - [x] OG image per page: `apps/core/og.py` (Pillow, bundled DejaVu, section colour, 1200×630), task `core.generate_og_image` on `page_published` → `BasePage.og_image_generated`; `base.html` `og:image` fallback + width/height
  - [x] `stories`: `StoryIndexPage` (`/uz/hikoyalar/` `/ru/istorii/`, section filter tabs) + `PatientStoryPage` (person_display_name, section, diagnosis_short, summary, hero, body, is_anonymised, consent_obtained, consent_guardian, private consent_document); `clean()` blocks publishing without consent (guardian for children); seeded in both languages
  - [x] Gate: container integration test transcodes a generated 2 s 1280×720 sample → 720p + 480p + poster (`docker exec ertaaniqla-web-1 … pytest -m integration`); publishing a story without consent raises ValidationError; OG task produces a 1200×630 PNG; 31 new UI strings uz+ru; coverage 94 %
- [x] **M4 — Directory, tools, FAQ, feedback, glossary** — DONE, tagged `m4`
  - [x] directory: `import_institutions` CSV (upsert by external_id, dry-run, row validation) + `data/institutions.sample.csv` (12 fake rows), HTMX filters (`_results.html` partial), Leaflet map bundle `static/dist/map.js` (D-021) with JSON data island, list fallback
  - [x] tools: `screening.py` rules (mammography 45–65/2y, ultrasound ≤44/2y, HPV 30–50), `selfcheck.py` scoring; `ToolsIndexPage`, `ScreeningToolPage`, `SelfCheckPage` (women + children) with CMS texts, waffle flags, disclaimer, HTMX results, nothing stored
  - [x] faq: `Question` (encrypted contact, consent-gated publication, snippet moderation), `FAQPage` form (honeypot, Turnstile, 5/min rate limit, HTMX), moderator e-mail via Celery, `faq.purge_contacts` beat job
  - [x] feedback: `FeedbackSubmission` + `FeedbackPage`, `feedback.purge_old_submissions` beat job (180 d)
  - [x] glossary: `GlossaryPage` (letters, section, search) + `glossary_wrap` filter on rich_text blocks (cached, invalidated on Term save)
  - [x] shared: `apps/core/antispam.py`, `apps/core/forms.py` (AntiSpamFormMixin, aria error attrs), `apps/core/mail.py` (templated Celery e-mail), footer site links (cached), form components
  - [x] seed: tools index + 3 tool pages, FAQ, feedback, glossary pages in uz+ru (placeholders only); 111 new UI strings uz+ru
  - [x] Gate: screening boundary tests, self-check scoring, purge jobs (freezegun), rate limit (6th POST → 429), CSV import (idempotent, dry-run, invalid rows), HTMX directory filter + map data, e2e a11y on 10 pages, coverage 93 %
- [x] **M5 — SEO, a11y, perf, print, blogger kit** — DONE, tagged `m5` (structure only, D-003)
  - [x] JSON-LD `@graph` per page (`apps/core/seo.py`, `BasePage.get_jsonld`): Organization (+ContactPoint), BreadcrumbList, MedicalWebPage/Article with reviewedBy + lastReviewed, FAQPage, VideoObject (video blocks), MedicalClinic (directory ≤ 50); `{% jsonld %}` on every page incl. search view
  - [x] sitemaps per language: `/sitemap.xml` index → `/uz/sitemap.xml`, `/ru/sitemap.xml` (`apps/core/sitemaps.py`, skips noindex + flag-off tools); robots.txt; canonical; OG/Twitter; Yandex/Google site verification via env; favicon.svg (+ lazy `/favicon.ico` redirect)
  - [x] share bar `{% share_bar %}` (Telegram, WhatsApp, Facebook, copy link, story image 1080×1920 generated on publish → `BasePage.story_image_generated`; migrations `*_story_image_and_privacy`)
  - [x] `MaterialsPage` (blogger kit) `/uz/materiallar/` `/ru/materialy/` — `apps/media_library/materials.py`, audience filter, copy caption/hashtags, seeded uz+ru
  - [x] Yandex.Metrika behind consent banner (`components/consent_banner.html`, `static/src/analytics.js`, `SiteSettings.metrika_id` + `privacy_page`); no GA/GTM
  - [x] accessibility toolbar (`components/a11y_toolbar.html`, `static/src/a11y.js`, tokens react to `html[data-font-scale|data-contrast|data-reduce-motion]`, early nonce'd apply in `base.html`)
  - [x] full `print.css` (article, patient route, self-exam steps, checklists, tools, glossary; chrome hidden, accordions expanded, site-name footer)
  - [x] images: Wagtail `{% picture %}` WebP + JPEG `srcset` in cards/hero; `core.prefetch_renditions` task on publish
  - [x] anonymous page cache `apps/core/cache.PageCacheMiddleware` (version bump on publish/unpublish/move/delete/settings; nonce swap; `PAGE_CACHE_SECONDS` 0 dev/test, 300 prod), nav/footer/glossary fragment caches
  - [x] Alpine switched to CSP build (D-027): `copyButton`, `embedFacade`, `selfCheck` in `main.js`; htmx indicator CSS in components.css; e2e asserts zero CSP console errors
  - [x] CI job `a11y-perf`: seeded preview server → `pa11y-ci` (8 URLs, WCAG2AA) + Lighthouse CI (3 URLs, LCP < 2.5 s, CLS < 0.1, TBT < 200 ms); `make pa11y`, `make lighthouse`; `tests/perf/test_budgets.py` (CSS ≤ 40 KB gz, JS ≤ 50 KB gz, HTML ≤ 60 KB gz)
  - [x] docs: TZ_TRACE (F6, F7, F9, F13, F15, W-05, W-13, C-12, A5–A8 → done), DECISIONS D-027…D-032, TODO_HARDENING H-011…H-014, CONTENT_MODEL (MaterialsPage, SEO), COMPONENT_INVENTORY (share, toolbar, consent, materials, picture)
  - [x] Gate: `tests/core/test_seo.py` (JSON-LD structure per type, sitemaps, share, story image, WebP), `tests/core/test_page_cache.py` (publish → next request MISS with new content), `tests/perf/test_budgets.py`, `tests/media_library/test_materials.py`, `tests/e2e/test_print.py` (print media + toolbar persistence), `tests/e2e/test_csp_alpine.py`; pa11y-ci 8/8 · Lighthouse local: perf 0.98/0.99/0.98, a11y 1.00, LCP 2.1/2.0/2.1 s, CLS 0, TBT 130/48/86 ms
- [ ] M5b — Design integration (blocked until Figma arrives)
  - [ ] map Figma tokens → `static/src/tokens.css`
  - [ ] restyle each partial in `templates/components/` (no Python changes)
  - [ ] screenshot-compare (Playwright, 390 px + 1280 px) against Figma exports
  - [ ] re-run pa11y/axe + Lighthouse budgets; update COMPONENT_INVENTORY.md
- [x] **M6 — Production DevOps** — DONE, tagged `m6`
  - [x] `compose.prod.yml`: nginx (templates + envsubst, `DOMAIN`/`DOMAIN_ALT`/`STAGING_*`), certbot + `nginx-reloader`, limits (web 4g, db 4g + tuned postgres flags, worker 2g, redis 640m, backup 1g), json-file 50m×5, `backup` container, `clamav` profile, **`monitoring` profile** (prometheus, alertmanager→Telegram, grafana on 127.0.0.1:3000, nginx/postgres/redis/node/blackbox exporters); `compose.staging.yml` (no ports, joins prod network)
  - [x] `docker/nginx/`: `nginx.conf` (JSON anonymised log, rate zones general 30r/s · cms_login 5r/m · form_post 10r/m POST-only, micro-cache, 444 default vhost, stub_status :8080), `templates/ertaaniqla.conf.template` (80→443, alt hosts→canonical, TLS 1.2/1.3 + OCSP, maintenance flag → 503 page, `/healthz/` `/readyz/` `/metrics` (internal), `/cms/` 512m + allow-list, forms zone, micro-cache 10 s, staging vhost with basic auth + lazy upstream), snippets (security headers, cache: static 1y immutable / media 30d / mp4 byte-range + throttle / **404 for `/media/documents/` and `/media/videos/source/`**, gzip + gzip_static, proxy, tls, cms_allowlist), `maintenance/maintenance.html` (uz+ru)
  - [x] scripts: `backup.sh` (pg_dump -Fc + restic 7d/4w/6m + check + textfile metrics), `restore.sh` (local dump / restic snapshot → drop+create → pg_restore, page count), `restore_test.sh` (weekly, scratch DB), `backup_cron.sh` (loop scheduler, Asia/Tashkent), `notify.sh` (Telegram), `init_letsencrypt.sh` (placeholder cert → real cert), `nginx_test.sh` (`nginx -t` in the image), `deploy.sh` (ssh: pull → migrate → `up --wait web` → worker/beat/backup/nginx → smoke), `smoke.sh`, `scripts/bootstrap_vps.sh` (docker, deploy user, sshd, ufw, fail2ban, unattended-upgrades, swap, sysctl, clone)
  - [x] monitoring: `prometheus.yml` (placeholders filled by sed at start), `alert_rules.yml` (12 rules: TargetDown, SiteDown, High5xxRate >1 %, HighLatencyP95 >1 s, DiskAlmostFull >80 %, BackupTooOld >26 h, RestoreTestTooOld, CertificateExpiringSoon <14 d, CeleryQueueBacklog >100, PostgresDown, RedisDown, HostMemoryPressure), `alertmanager.yml` (Telegram), `blackbox.yml`, Grafana provisioning + `ertaaniqla-overview.json` (18 panels)
  - [x] CI: `build` job + SBOM (syft) + `nginx -t` + compose config + promtool/amtool; `deploy-staging` (auto on main) → `deploy-prod` (environment approval); `rollback.yml` (workflow_dispatch env + tag); `weekly-rebuild.yml` (base image + trivy → :latest); `.github/dependabot.yml`
  - [x] image: Postgres client pinned to **16** (PGDG; Debian trixie ships 17 → dumps unrestorable on PG16, found by the gate); `collectstatic --ignore=src` (manifest storage choked on `static/src/map.css` `@import`)
  - [x] commands (spec §6/§8, were missing): `purge_pii` (+ `--dry-run`), `rotate_pii_keys`, `check_links` (+ `--external`) with tests
  - [x] `.env.example`: DOMAIN/DOMAIN_ALT/STAGING_*/LETSENCRYPT_EMAIL/WEB_IMAGE/GRAFANA_*/BACKUP_AT…, plus previously undocumented MEDIA_ROOT, DJANGO_EMAIL_BACKEND, DEV_LOCMEM_CACHE, TEST_DATABASE_URL (now enforced by `tests/ops/test_ops_config.py::test_env_example_documents_every_setting`)
  - [x] Makefile: `restore-test`, `nginx-test`, `compose-check`, `ops-check`, `prod-up/down`, `tls-init`, `maintenance-on/off`; `deploy` takes `TAG`
  - [x] docs: `docs/RUNBOOK.md` (deploy, rollback, backup/restore, incident table, routine ops, secret rotation, staging, scaling), `docs/SECURITY.md` (assets, 7 threat classes → controls, reporting, accepted risks), ADR-0004, DECISIONS D-033…D-039, TODO_HARDENING H-015…H-019, TZ_TRACE F8 + E-01/E-05/E-07/E-10 → done
  - [x] Gate (run 2026-09-16 on this machine): `docker compose -f compose.yml -f compose.prod.yml --profile monitoring --profile clamav config` valid (+ staging stack); prod image builds (`ertaaniqla/web:local`, pg_dump 16.15); `check --deploy` green (test); `nginx -t` in `nginx:1.27-alpine` → "syntax is ok / test is successful"; promtool 12 rules OK, amtool OK; **backup → restore into a scratch `postgres:16-alpine` container: 71 pages, 12 institutions, 6 terms**; restic path (local repo) backup + forget + check OK; `restore_test.sh` → "OK (71 pages)"; `tests/ops` 17 passed
- [ ] M7 — Editors, workflow, UAT, launch checklist
- [ ] FINAL REPORT → docs/FINAL_REPORT_uz.md

## Last command run (2026-09-16, M6 close)

```
.venv/Scripts/python -m pytest --cov      → 349 passed, 1 skipped (ffmpeg on host), coverage 92 % (gate 85 %)
ruff check / format --check              → clean (189 files) · mypy → Success: 113 source files
docker build -f docker/web/Dockerfile    → ertaaniqla/web:local OK; pg_dump (PostgreSQL) 16.15 (PGDG)
docker compose … compose.prod.yml --profile monitoring --profile clamav config --quiet → OK; + compose.staging.yml → OK
bash docker/scripts/nginx_test.sh        → nginx: configuration file /etc/nginx/nginx.conf test is successful
promtool check config / amtool check-config → SUCCESS (12 rules)
backup.sh (dev DB) → dump 512 K; restore.sh latest → scratch postgres:16 container → "wagtailcore_page rows: 71"
backup.sh with RESTIC_REPOSITORY=/tmp/restic-repo → snapshot + forget + check OK; restore_test.sh → OK (71 pages)
```

## Next concrete action

Start **M7 — Editors, workflow, UAT, launch checklist** (AUTOPILOT gate): Wagtail groups
Editor / Medical Reviewer / Admin with permissions (data migration in `apps/users`); 2-step
workflow (editor → medical reviewer → publish) as a Wagtail `Workflow` with two `GroupApprovalTask`s
assigned to the root of both language trees; approving as reviewer sets `medically_verified`,
`last_reviewed_by/at` (task/hook) → «Проверено врачом» badge; 2FA enforced for all staff
(`CMS_2FA_REQUIRED`, verify middleware + test); `docs/EDITOR_GUIDE_ru.md` + `_uz.md` with
Playwright screenshots of the CMS (`tests/e2e/screenshots/cms-*.png`); `docs/LAUNCH_CHECKLIST.md`;
`tests/perf/locustfile.py` (200 users, 5 min) + a short run summary in PROGRESS; final
`TZ_TRACE.md` pass (every row done / not done + reason). Gate: e2e "editor creates article in
ru, translates to uz, reviewer approves, page live in both languages"; permission tests; full
check + e2e; commit + tag `m7-release-candidate`. Then FINAL REPORT → `docs/FINAL_REPORT_uz.md`.

(M6 note kept for history:) Start **M6 — Production DevOps** (AUTOPILOT gate): `compose.prod.yml` limits/logging (web 4 GB,
db 4 GB + tuned postgres conf, redis 512 MB, worker 2 GB; `restart: unless-stopped`; json-file
50m×5); `docker/nginx/` (nginx.conf, sites/ertaaniqla.conf, snippets/{security,cache,gzip}.conf:
TLS 1.2/1.3 + OCSP, brotli/gzip, `/static/` 1y immutable, `/media/` 30d + mp4 byte-range,
micro-cache 10 s for anonymous HTML keyed on lang cookie, rate zones 30 r/s general · 5 r/m
`/cms/login/` · 10 r/m form POST, `client_max_body_size 512m` only on `/cms/`, 444 for unknown
hosts, dotfile block, maintenance flag `/srv/maintenance.flag`, `/metrics` basic-auth);
certbot service + renew hook; `scripts/bootstrap_vps.sh` (docker, ufw, fail2ban,
unattended-upgrades, swap 4 GB, sysctl, clone, restore); `backup` container (`pg_dump -Fc` +
restic to S3-compatible in UZ, retention 7d/4w/6m, weekly restore test script, alert on
failure); Prometheus exporters (nginx, postgres, redis, node) + Grafana dashboards JSON +
alert rules → Telegram (profile `monitoring`); CI: build → syft SBOM → trivy → push GHCR →
deploy over SSH (`docker compose pull && run --rm migrate && up -d --no-deps --wait web worker
beat`) → smoke `/readyz/` + 3 pages → Telegram; rollback workflow_dispatch; staging compose
project; `docs/RUNBOOK.md` + `docs/SECURITY.md`. Gate: `compose config` valid, prod image
builds, `check --deploy` green, backup → restore into scratch container (run it), `nginx -t`
in a container, commit + tag `m6`.

(M5 note kept for history:) Start **M5 — SEO, a11y, performance, print, blogger kit**: JSON-LD (MedicalWebPage/Article
with reviewedBy, Organization, BreadcrumbList, FAQPage, VideoObject, MedicalClinic), sitemaps
per language (Wagtail sitemap + Site), share bar (Telegram first), `MaterialsPage` (blogger
kit: downloads, captions uz/ru, hashtags), Yandex.Metrika behind a consent banner
(`apps/analytics`), accessibility toolbar (font ×1.25/×1.5, contrast, reduced motion;
localStorage), full print stylesheets, image `srcset`/WebP renditions, per-view cache with
signal invalidation + nav fragment cache, bundle-size test, pa11y-ci config.

(M4 note kept for history:) Start **M4 — Directory, tools, FAQ, feedback, glossary**: `import_institutions` CSV command +
`data/institutions.sample.csv` (fake), Leaflet map (self-hosted JS via npm, OSM tiles) + HTMX
region/type filters on `DirectoryPage`; `apps/tools` (screening helper — table-driven rules
mammography 45–65/2y, ultrasound <45/2y, HPV 30–50; women's symptom self-check; children's
warning-signs checklist; patient-route page) behind waffle flags; `apps/faq` Question form
(honeypot, Turnstile, rate limit, encrypted contact, consent) → moderation → `FAQPage`, purge
job; `apps/feedback` form + retention job (Celery beat); glossary tooltip tag + glossary page.

(M3 note kept for history:) Start **M3 — Media & stories**: Celery `transcode_video` (ffmpeg 720p/480p + poster, status
machine on `media_library.Video`), VTT subtitles already on the model, galleries/documents
exist as blocks; OG image generation task (Pillow, section colour) on publish;
`stories.PatientStoryPage` with consent enforcement (`consent_obtained`, `consent_guardian`
for minors, private consent document, `is_anonymised`), stories index at `/uz/hikoyalar/`.
ffmpeg: not on host PATH — check `Get-Command ffmpeg`; the Docker image has it (CI installs it).
Remember: restart the web container after adding new templatetag/app modules.
