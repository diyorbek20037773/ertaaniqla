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

Start **M5 — SEO, a11y, performance, print, blogger kit**: JSON-LD (MedicalWebPage/Article
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
