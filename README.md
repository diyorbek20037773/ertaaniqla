# Erta aniqla — onco-awareness portal

Bilingual (uz/ru) information portal on early cancer detection: women's cancers (breast, cervical)
and childhood cancer. Django 5.2 + Wagtail 7 + PostgreSQL 16 + Redis 7 + Celery, HTMX/Alpine/Tailwind.

- Engineering constitution: `docs/ENGINEERING_SPEC.md`
- Technical specification (ru, wins on conflicts): `docs/TZ_concept_ru.md`
- Requirement trace: `docs/TZ_TRACE.md` · decisions: `docs/DECISIONS.md` · ADRs: `docs/ADR/`
- Build state / resume point: `PROGRESS.md`

## Quick start (dev)

```bash
cp .env.example .env               # edit if needed
make install                       # uv sync, npm ci, playwright chromium
docker compose -f compose.yml -f compose.dev.yml up -d db redis mailpit
make migrate
make seed                          # full TZ page tree (uz+ru) + sample institutions
make superuser
npm run build                      # or: npm run watch
uv run python manage.py runserver  # http://localhost:8000 → /uz/  · CMS: /cms/
```

Or everything in containers: `make dev`.

## Quality gate

```bash
make check      # ruff + mypy + pytest (coverage ≥ 85 %) + translation completeness
make e2e        # Playwright (needs a running server)
```

## Layout

See `docs/ENGINEERING_SPEC.md` §4.2. Apps live in `apps/`, settings in `config/settings/`,
templates in `templates/` (components in `templates/components/`), design tokens in
`static/src/tokens.css`.
