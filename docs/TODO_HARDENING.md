# TODO_HARDENING.md — later improvements (never blockers)

Per AUTOPILOT rule 2: when the simplest correct version is built, the better version is listed
here. Each item: what, why, where.

| # | Area | Item | Where |
|---|---|---|---|
| H-001 | i18n | Add `uz-Cyrl` as a live locale once the client confirms demand (locale stub exists, ADR-0003). | `config/settings/base.py`, Wagtail locales |
| H-002 | infra | Move `/metrics` basic-auth to nginx `auth_basic` + IP allow-list once Prometheus host is known (M6). | `docker/nginx` |
| H-003 | search | Upgrade path to Meilisearch if Postgres FTS relevance is insufficient on real content. | `apps/search` |
| H-004 | ops | PgBouncer when concurrent DB connections exceed 200 (spec §11.1). | `compose.prod.yml` |
