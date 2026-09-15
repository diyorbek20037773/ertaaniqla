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
- [ ] M2 — Components, home, search (structure + a11y only; no visual polish)
- [ ] M3 — Media & stories
- [ ] M4 — Directory, tools, FAQ, feedback, glossary
- [ ] M5 — SEO, a11y, perf, print, blogger kit (structure only; no visual polish)
- [ ] M5b — Design integration (blocked until Figma arrives)
  - [ ] map Figma tokens → `static/src/tokens.css`
  - [ ] restyle each partial in `templates/components/` (no Python changes)
  - [ ] screenshot-compare (Playwright, 390 px + 1280 px) against Figma exports
  - [ ] re-run pa11y/axe + Lighthouse budgets; update COMPONENT_INVENTORY.md
- [ ] M6 — Production DevOps
- [ ] M7 — Editors, workflow, UAT, launch checklist
- [ ] FINAL REPORT → docs/FINAL_REPORT_uz.md

## Last command run

```
.venv/Scripts/python -m pytest --cov      → all passed, coverage 94.65 % (gate 85 %)
E2E_BASE_URL=http://localhost:8001 pytest tests/e2e -m e2e → 11 passed (screenshots written)
ruff check / format --check              → clean
mypy                                     → Success: no issues found in 70 source files
scripts/check_translations.py            → translations: uz + ru complete
manage.py check --deploy (prod env)      → no issues
manage.py seed_content (dev DB, 2nd run) → created=0 updated=0 unchanged=52
curl :8001 → /uz/ /ru/ sections, topics, articles, directory all 200; /uz/qayerga-murojaat/ 301
```

## Next concrete action

Start **M2 — Components, home, search** (structure + a11y only, no visual polish):
`apps/search` (Postgres FTS view `/uz/qidiruv/?q=`, uz/ru synonyms, Latin↔Cyrillic normaliser,
HTMX search-as-you-type + non-JS form), home featured logic already exists; axe (Playwright)
0 serious on 5 pages; block render tests in both locales already exist — extend for search.
Remember: web container must be restarted after adding new templatetag modules
(`docker compose -f compose.yml -f compose.dev.yml restart web`).
