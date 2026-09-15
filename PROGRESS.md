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

## Milestones

- [x] Read ENGINEERING_SPEC, TZ, AUTOPILOT_PROMPT fully.
- [ ] **M0 — Scaffold** (all items done; gate verification of the web container in progress)
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
  - [ ] Gate: compose up db+redis+web (web on host :8001), curl /healthz /readyz /uz/ /cms/login/ → commit + tag `m0`
- [ ] M1 — Content model + i18n + seeded tree
  - [ ] BasePage mixin (SEO, og_image, noindex, reviewed_by/at, medically_verified, get_section, reading_time)
  - [ ] HomePage, SectionIndexPage, TopicIndexPage, ArticlePage + every block of spec §4.3 (template + clean/render test each)
  - [ ] Site settings (hotline, socials, footer, Metrika, banner, partners, legal)
  - [ ] wagtail-localize locales uz/ru (+ uz-Cyrl stub), hreflang, language switcher to translated counterpart
  - [ ] `seed_content` — full TZ tree in uz+ru, idempotent
  - [ ] base layout, tokens, `data-section` theming, mega-menu (5 items per section), breadcrumbs, footer, print CSS skeleton
  - [ ] docs/COMPONENT_INVENTORY.md (ru+uz) — designer hand-off
  - [ ] Gate: every live page 200 in uz and ru; `assertNumQueries` on section index; translations; Playwright screenshots 390 px → `tests/e2e/screenshots/`; tag `m1`
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
.venv/Scripts/python -m pytest --cov   → 36 passed, coverage 94.87 % (gate 85 %)
.venv/Scripts/ruff check .             → All checks passed
.venv/Scripts/mypy                     → Success: no issues found in 50 source files
pip-audit -r req.txt --strict          → No known vulnerabilities found
scripts/check_translations.py          → translations: uz + ru complete
docker build -f docker/web/Dockerfile  → ertaaniqla/web:local built
docker compose … up -d web (WEB_PORT=8001, INSTALL_DEV=1) → verifying curl checks
```

## Next concrete action

If the web curl checks pass: `git add -A && git commit -m "feat: M0 scaffold" && git tag m0`; then start M1
with `apps/core/models.py` (BasePage), `apps/articles/blocks.py`, `apps/sections/models.py`, `apps/home/models.py`.
