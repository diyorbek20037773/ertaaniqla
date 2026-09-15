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
