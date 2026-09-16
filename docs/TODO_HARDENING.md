# TODO_HARDENING.md — later improvements (never blockers)

Per AUTOPILOT rule 2: when the simplest correct version is built, the better version is listed
here. Each item: what, why, where.

| # | Area | Item | Where |
|---|---|---|---|
| H-001 | i18n | Add `uz-Cyrl` as a live locale once the client confirms demand (locale stub exists, ADR-0003). | `config/settings/base.py`, Wagtail locales |
| H-002 | infra | Move `/metrics` basic-auth to nginx `auth_basic` + IP allow-list once Prometheus host is known (M6). | `docker/nginx` |
| H-003 | search | Upgrade path to Meilisearch if Postgres FTS relevance is insufficient on real content. | `apps/search` |
| H-004 | ops | PgBouncer when concurrent DB connections exceed 200 (spec §11.1). | `compose.prod.yml` |
| H-005 | search | Move the uz/ru synonym list to a CMS snippet once editors want to maintain it; add `AutocompleteField` on `summary` and per-locale relevance boosting. | `apps/search/synonyms.py` |
| H-006 | media | Docker Desktop bind mounts on Windows can return an empty read right after a write, so Django may null image dimensions; code keeps known values. Not an issue on Linux/named volumes. | `apps/media_library/services.py`, `signals.py` |
| H-007 | media | Poster frame is taken at 1 s; add an editor-chosen poster timestamp and WebM/AV1 renditions if bandwidth data justify it. | `apps/media_library/services.py` |
| H-008 | directory | Self-hosted OSM tile proxy / cache in nginx for regions with slow access to tile.openstreetmap.org; marker clustering when > 200 institutions. | `docker/nginx`, `static/src/map.js` |
| H-009 | forms | Turnstile widget needs the client's site key; until then forms rely on honeypot + rate limit only (prod refuses to start without the secret). | `.env` |
| H-010 | faq | Moderator notification is a single e-mail; add Telegram bot alert (M6 alerts channel) and daily digest of unanswered questions. | `apps/faq/tasks.py` |
| H-011 | perf | Page cache stores full HTML per (language, path, query); add an allow-list of query keys (`q`, `region`, `kind`, `page`) so random query strings cannot fill Redis; nginx micro-cache in M6 gives the second layer. | `apps/core/cache.py` |
| H-012 | seo | `VideoObject.uploadDate` uses the page's first-published date; add `Video.published_at` once editors need the true recording date. | `apps/core/seo.py` |
| H-013 | a11y | Toolbar contrast theme is token-level (neutral palette inverted); revisit with the designer's palette (M5b) and add a WCAG AAA check to pa11y. | `static/src/tokens.css` |
| H-014 | analytics | Server-side event log (page views without cookies) as a Metrika-free fallback; spec lists it as optional. | `apps/analytics` |
| H-015 | nginx | Brotli: switch to an nginx build with `ngx_brotli` (or serve whitenoise's `.br` files) once assets grow; today gzip + `gzip_static`. | `docker/nginx` |
| H-016 | ops | External uptime check (Uptime-Kuma on another host or a free monitor) — the in-host blackbox probe cannot see a full VPS outage. | RUNBOOK §5 |
| H-017 | ops | Loki + promtail for log search (optional in the spec); today `docker compose logs` + Sentry. | `compose.prod.yml` profile `logs` |
| H-018 | ops | Page-cache query allow-list (H-011) also at nginx level (`proxy_cache_key` without unknown query args). | `docker/nginx/templates` |
| H-019 | security | ZAP baseline scan in CI against the preview server (optional in the spec §12). | `.github/workflows/ci.yml` |
