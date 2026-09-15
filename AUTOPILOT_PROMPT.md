# AUTOPILOT PROMPT — build "Erta aniqla" end-to-end without stopping

> Qobiljon: bu faylni to'liq nusxalab Claude Code'ga (auto / `--dangerously-skip-permissions` yoki "auto-accept edits" rejimida) birinchi xabar sifatida yuboring.
> Repo ildizida `CLAUDE.md` va `docs/TZ_concept_ru.md` turgan bo'lishi shart.
> Agar sessiya kontekst tugab uzilsa, yangi sessiyada faqat shu bitta gapni yuboring:
> **"Read CLAUDE.md, docs/TZ_concept_ru.md and PROGRESS.md, then continue the autopilot build from the first unfinished item. Same rules as AUTOPILOT_PROMPT.md."**

---

## MISSION

You are the sole senior engineer (backend + frontend + SRE) on the "Erta aniqla" oncology-awareness portal. You are running **unattended in autopilot mode**. Your job is to take this repository from empty to a **production-ready, fully tested, deployable** system that implements **100 % of the Technical Specification** — every page, every table cell, every bullet in `docs/TZ_concept_ru.md`, as decomposed in `CLAUDE.md` §2 — following the architecture, stack, standards, security, DevOps and testing rules in `CLAUDE.md` exactly.

Read, in this order, completely, before writing a single file:
1. `CLAUDE.md` (the constitution — every section applies)
2. `docs/TZ_concept_ru.md` (the spec — the TZ wins on any conflict)
3. `PROGRESS.md` if it exists (resume point)

## AUTOPILOT RULES (override anything in CLAUDE.md §14 that says "wait for confirmation")

1. **Never stop to ask.** No one is watching. Whenever you would ask a question, instead: choose the option that is simplest to operate by one developer, is most faithful to the TZ, and is reversible; write the decision with a one-line rationale into `docs/DECISIONS.md` and the "Decisions" column of `docs/TZ_TRACE.md`; continue.
2. **Never skip, defer, stub or "simplify" a TZ item.** If something is hard, build the simplest correct version, test it, and add a `docs/TODO_HARDENING.md` entry for later improvement. A `NotImplementedError`, a `pass`, a `# TODO` in production code, or an empty template is a failure.
3. **Never write medical content.** All page bodies are seeded with structured placeholders that list the TZ bullets verbatim (ru) plus a real Uzbek (Latin) translation of the bullet headings, tagged `[[TODO: content — copywriter]]` / `[[VERIFY: doctor]]`. Where the TZ gives concrete facts (screening ages/intervals, the 4-step route, the 6 cancer types, institution types), copy them exactly.
4. **Work milestone by milestone, in order** (CLAUDE.md §13: M0 → M1 → M2 → M3 → M4 → M5 → M6 → M7). A milestone is finished only when its **exit gate** below passes. Do not start M(n+1) until M(n)'s gate is green.
5. **Keep `PROGRESS.md` current after every meaningful step** (max 2–3 minutes of work between updates): milestone, task list with `[x]/[ ]`, last command run and its result, the next concrete action. This file is how you survive a context reset — write it as instructions to a future you who remembers nothing.
6. **Commit after every green step**: `git add -A && git commit -m "<type>(<scope>): <what>"` (Conventional Commits). Commit even mid-milestone. Tag each milestone: `git tag m1-content-model` etc.
7. **Verify, don't assume.** After each feature: run it (`make check`, `make test`, spin up `docker compose` and `curl` the URLs, run the management command, render the template). Paste real output into `PROGRESS.md`. If a tool is missing in the environment (docker, node, ffmpeg, postgres), install it; if it cannot be installed, use the closest substitute (e.g. SQLite for a unit-test run) **and** leave the Postgres path intact and documented — never delete infrastructure because you couldn't run it locally.
8. **Self-review loop.** At the end of every milestone, re-read CLAUDE.md §2, §4.3, §5–§12 and the TZ section that milestone covers; list every requirement; for each one, point to the file + test that proves it; fix gaps before declaring the gate passed. Then run a fresh "adversarial pass": try to break your own forms, i18n, cache invalidation, consent enforcement, and fix what breaks.
9. **Budgets and gates are hard.** Coverage ≥ 85 %, `ruff`/`mypy` clean, translations complete for `uz` and `ru`, every seeded URL 200 in both languages, no `[[TODO` outside seed data and docs, Lighthouse/pa11y budgets per CLAUDE.md §4.6/§9 (if Lighthouse cannot run locally, write the CI job and a Playwright-based size check instead, and say so in PROGRESS.md).
10. **Security is not optional.** `django check --deploy` must pass with prod settings; secrets only from env; 2FA on CMS; PII encrypted; EXIF stripped; CSP on. If a shortcut would weaken any of these, do not take it.
11. **Explain in Uzbek.** All human-facing narration in the chat is in Uzbek; code, identifiers, commit messages, docs for developers in English; editor-facing docs in ru + uz.
12. **Finish with a full report** (§ FINAL REPORT below). Do not declare success early. If, after honest effort, something is not done, the report must list it explicitly under "NOT DONE" with the reason — never hide it.

## EXECUTION PLAN WITH EXIT GATES

Follow CLAUDE.md §13 scopes. The gates below are the minimum; CLAUDE.md's Definition of Done still applies.

### M0 — Scaffold (gate)
- Repo layout exactly as CLAUDE.md §4.2; `pyproject.toml` (Django 5.1, Wagtail 6.x, wagtail-localize, psycopg[binary], redis, celery, django-environ, django-csp, django-axes, django-otp/wagtail-2fa, django-ratelimit, django-crispy-forms + crispy-tailwind, django-storages, python-magic, Pillow, whitenoise, gunicorn, sentry-sdk, django-prometheus, python-json-logger; dev: ruff, mypy + django-stubs, pytest, pytest-django, factory_boy, django-debug-toolbar, playwright, polib).
- `Makefile` with every target from CLAUDE.md §15; `compose.yml` + `compose.dev.yml` + `compose.prod.yml`; multi-stage `docker/web/Dockerfile`; `.env.example` documenting every variable; `.pre-commit-config.yaml`; `.github/workflows/ci.yml` (quality job).
- `docs/TZ_TRACE.md` with one row per requirement (CLAUDE.md §2.1–2.5, F1–F17, A1–A8) + rows for every named page in §2.2/§2.3; `docs/DECISIONS.md`; `docs/ADR/0001-stack.md`; `PROGRESS.md`.
- Gate: `docker compose -f compose.yml -f compose.dev.yml up -d` brings up db+redis+web; `make migrate` ok; `make check` green on empty project; commit + tag `m0`.

### M1 — Content model + i18n + full seeded tree (gate)
- All page types and every StreamField block from CLAUDE.md §4.3, each block with a template and a unit test for `clean()`/render.
- wagtail-localize configured; `uz` default (Latin), `ru`; `hreflang`; language switcher to translated counterpart.
- `seed_content` builds the **entire** tree of CLAUDE.md §2.2 + §2.3 in both locales, body = callout listing TZ bullets verbatim; idempotent (re-running updates, doesn't duplicate).
- Base layout, tokens, `data-section` theming, mega-menu (5 items per section per CLAUDE.md §2.1), breadcrumbs, footer with disclaimer + partner placeholders, print CSS skeleton.
- Gate: test that iterates every live page and asserts 200 in `uz` and `ru`; `assertNumQueries` on section index; translation check passes; screenshots of home + both section indexes at 390 px via Playwright saved to `tests/e2e/screenshots/`; commit + tag `m1`.

### M2 — Components, home, search (gate)
- Every block rendered with real design (steps, three_columns, two_columns, cards_grid, symptom_list with urgency colours+icons, stat, callout kinds, table, faq_accordion, quote, cta, embed with click-to-load for Instagram/TikTok).
- Home page with featured content, stats strip, emergency banner from settings.
- Postgres FTS search with `unaccent`, uz/ru synonym list, Latin↔Cyrillic normaliser, HTMX search-as-you-type + non-JS fallback.
- Gate: render test for every block in both locales; search tests (uz query finds ru page via synonym; Cyrillic query finds Latin slug); accessibility (axe via Playwright) 0 serious on 5 pages; commit + tag `m2`.

### M3 — Media & stories (gate)
- `Video` snippet (upload/youtube/telegram/instagram/tiktok), Celery `transcode_video` with ffmpeg (720p/480p + poster), status machine, VTT subtitles uz/ru, transcript rendering; galleries with downloadable infographics; documents; OG image generation per page on publish.
- `PatientStoryPage` with consent enforcement (`consent_obtained` required; `consent_guardian` for minors), private consent document, anonymisation flag.
- Gate: Celery integration test transcodes a generated 2-second sample; publishing a story without consent raises `ValidationError`; OG image task produces a PNG; commit + tag `m3`.

### M4 — Directory, tools, FAQ, feedback, glossary (gate)
- `Region` (14) + `Institution` (all `kind`s from CLAUDE.md §4.3, services M2M, free flag), CSV import command with a sample `data/institutions.sample.csv` (fake data), list + Leaflet map + HTMX region/type filters, `institution_list` block.
- `tools`: screening eligibility helper (rules table-driven from TZ: mammography 45–65/2y, ultrasound <45/2y, HPV 30–50), women's symptom self-check, children's warning-signs checklist, patient-route page — all stateless, disclaimer on every tool page, behind `waffle` flags defaulting ON in dev, OFF in prod.
- `faq`: question form (honeypot, Turnstile placeholder, rate limit, encrypted contact, consent to publish) → moderation in Wagtail → `FAQPage`; purge job.
- `feedback` form + retention job; `glossary` Term snippet + tooltip tag + glossary page.
- Gate: table-driven tests for screening rules (every age boundary), self-check scoring, purge jobs (freeze time), rate limit, CSV import; e2e: filter directory, submit question; commit + tag `m4`.

### M5 — SEO, a11y, performance, print, blogger kit (gate)
- JSON-LD types per CLAUDE.md §10, sitemaps per language, robots, canonical, OG/Twitter, share bar (Telegram first), `MaterialsPage` (blogger kit), Yandex.Metrika behind consent banner, accessibility toolbar, full print stylesheets, image `srcset`/WebP renditions prefetch, per-view cache with signal invalidation, nav fragment cache.
- Gate: JSON-LD validated with a schema test; cache test (publish → page updated within 1 request); pa11y-ci config + run; bundle size test (CSS ≤ 40 KB gz, JS ≤ 50 KB gz); commit + tag `m5`.

### M6 — Production DevOps (gate)
- `compose.prod.yml` with limits/logging; nginx config per CLAUDE.md §11.2 (TLS, brotli/gzip, micro-cache, rate zones, headers, maintenance flag, mp4 byte-range, `/cms/` upload limit); certbot flow; `scripts/bootstrap_vps.sh`; `backup` container with `pg_dump` + restic, retention, weekly restore test script; `/healthz` `/readyz`; Sentry; Prometheus exporters + Grafana dashboards JSON + alert rules → Telegram; CI: build → trivy → push GHCR → deploy over SSH with `--wait` → smoke test → rollback workflow; staging compose project.
- `docs/RUNBOOK.md` (deploy, rollback, backup/restore, incident, secret rotation, rebuild VPS in ≤ 1 h), `docs/SECURITY.md` threat model.
- Gate: `docker compose -f compose.yml -f compose.prod.yml config` valid; prod image builds; `django check --deploy` passes with prod settings and a dummy env; backup script produces a dump and restore script restores it into a scratch container (run it); nginx config passes `nginx -t` in a container; commit + tag `m6`.

### M7 — Editors, workflow, UAT, launch checklist (gate)
- Wagtail groups Editor / Medical Reviewer / Admin with permissions; 2-step workflow (editor → medical reviewer → publish); "Проверено врачом" badge; 2FA enforced; `EDITOR_GUIDE_ru.md` + `EDITOR_GUIDE_uz.md` with screenshots; `docs/LAUNCH_CHECKLIST.md`; locust load test file + run summary; final `TZ_TRACE.md` with every row `done` or an honest `not done + reason`.
- Gate: e2e "editor creates article in ru, translates to uz, reviewer approves, page live in both languages"; permission tests; full `make check` + `make e2e`; commit + tag `m7-release-candidate`.

## FINAL REPORT (write to `docs/FINAL_REPORT_uz.md` and print it in the chat, in Uzbek)

1. Nima qurildi — milestone bo'yicha, faylga havolalar bilan.
2. `TZ_TRACE.md` xulosasi: jami talab / done / not done (sabab bilan).
3. Qabul qilingan qarorlar ro'yxati (`DECISIONS.md`) — buyurtmachi tasdiqlashi kerak bo'lganlari alohida.
4. Ishga tushirish uchun sizdan kerak bo'lgan narsalar: domen, VPS (O'zbekistonda), `.env` qiymatlari, Sentry/Metrika/Turnstile kalitlari, muassasalar CSV, logotip/ranglar, tibbiy matnlar.
5. Test natijalari (coverage, e2e, load, a11y, size) — real chiqish.
6. Ma'lum kamchiliklar va `TODO_HARDENING.md`.

## START NOW

Begin with M0. First action: create `PROGRESS.md` with the full milestone checklist, then scaffold. Do not ask anything. Do not summarise the plan and wait — execute.
