# TZ_TRACE.md — requirement → implementation → test

One row per requirement of `docs/TZ_concept_ru.md` as decomposed in `docs/ENGINEERING_SPEC.md`
§2 (structure, pages, F1–F17, A1–A8) plus cross-cutting spec rules. A row is **done** only when it
links to the implementing module **and** a test. Status: `todo` · `wip` · `done` · `not done (reason)`.

Legend for milestone column: M0…M7 per spec §13; M5b = design integration (DECISIONS D-003).

## A. Platform structure (TZ §II, spec §2.1)

| ID | Requirement (TZ) | Decision | Impl | Test | M | Status |
|---|---|---|---|---|---|---|
| S-01 | Two independent sections, shared navigation, one design system | Sections = page-tree subtrees under one HomePage | `apps/sections` `SectionIndexPage`, `apps/core/navigation.py` | `tests/sections/test_models.py` | M1 | done |
| S-02 | Each section has its own colour identity | `data-section` on `<body>` + `--brand` tokens; hues = designer's call (wireframe now) | `static/src/tokens.css`, `core_tags.section_style`, `body[data-section]` | `tests/sections/test_models.py::test_body_data_section_attribute_and_theme` | M1 | done |
| S-03 | Women's section top menu = 5 items: Осведомленность, Скрининг, Организация лечения, Куда обратиться, Государственная поддержка | Care & Support / Life after cancer are pages in the subtree, `show_in_menus` editor-controlled | `apps/core/seed/tree.py` (D-013), `SectionIndexPage.get_menu_items` | `tests/sections/test_seed.py::test_women_menu_has_the_five_tz_items` | M1 | done |
| S-04 | Children's section top menu = 5 items: Об онкозаболеваниях у детей, Диагностика и лечение, Уход и поддержка, Информация для семьи, Жизнь после рака | — | same | `tests/sections/test_seed.py::test_children_menu_has_the_five_tz_items` | M1 | done |
| S-05 | Home page presents both sections equally; key idea "раннее выявление" as CMS hero slogan | `HomePage.hero_*` fields | `apps/home` HomePage (hero, section cards, stats, featured) | `tests/home/test_home.py` | M2 | done |
| S-06 | Domain ertaaniqla.uz (+ oncoportal.uz mentioned in TZ §IV) | canonical = ertaaniqla.uz, alias redirects 301 | `docker/nginx`, `CANONICAL_DOMAIN` | `tests/core/test_infra.py` (M6 nginx test) | M6 | todo |

## B. Section 1 — women's cancer pages (TZ §2.1, spec §2.2)

| ID | Page / content (TZ verbatim) | Impl (seed path) | Test | M | Status |
|---|---|---|---|---|---|
| W-01 | Осведомленность (topic index) | `/uz/ayollar/ogohlik/` `/ru/zhenskiy/osvedomlennost/` | `tests/sections/test_seed.py::test_tz_bullets_verbatim_ru` | M1 | done |
| W-02 | Что такое РМЖ и РШМ — что происходит в организме, стадии, статистика по Узбекистану | ArticlePage, callout placeholder listing bullets + `stat` block placeholders | `tests/sections/test_seed.py::test_tz_bullets_verbatim_ru` | M1 | done |
| W-03 | Факторы риска — возраст, наследственность, образ жизни, ВПЧ-инфекция и другие | ArticlePage, `cards_grid` placeholder | `tests/sections/test_seed.py::test_tz_bullets_verbatim_ru` | M1 | done |
| W-04 | Симптомы — признаки, которые нельзя игнорировать | ArticlePage, `symptom_list` placeholder | `tests/sections/test_seed.py::test_tz_bullets_verbatim_ru` | M1 | done |
| W-05 | Самообследование груди — пошаговое руководство (F13) | `steps` block on Symptoms + `print.css` | `tests/articles/test_blocks.py::test_steps_auto_number_and_deadline` | M2 | wip (steps block + placeholder steps seeded; print CSS skeleton; interactive polish M2) |
| W-06 | Скрининг → Кому и как часто: маммография 45–65 раз в 2 года; УЗИ до 45 раз в 2 года; ВПЧ-тест 30–50; призывы к самообследованию | ArticlePage with `table` + `two_columns`, facts verbatim `[[VERIFY: doctor]]` | `tests/sections/test_seed.py::test_tz_bullets_verbatim_ru` | M1 | done |
| W-07 | Скрининг → Где пройти: СВП; районные поликлиники (кабинеты онконастороженности); Центр здоровья матери и ребёнка и филиалы; бесплатно в рамках гос. программы | ArticlePage + `institution_list` block | `tests/sections/test_seed.py`, `tests/articles/test_blocks.py::test_institution_list_filters` | M1/M4 | done (list; map/HTMX M4) |
| W-08 | Организация лечения — 4-step route 01 Первичный приём / 02 Направление на диагностику / 03 Онколог-онкогинеколог (даты ПП-402 → `[[VERIFY: PP-402 referral deadlines]]`) / 04 Лечение (F12) | `steps` block with `deadline` per step, seeded 4 steps | `tests/sections/test_seed.py::test_patient_route_has_four_steps_with_pp402_deadline` | M1/M4 | done (route page; tools page M4) |
| W-09 | Куда обратиться — directory (map + list, region filter) (F11) | `apps/directory` `DirectoryPage` | `tests/directory/test_models.py` | M4 | wip (DirectoryPage list + GET filters, D-010; map + HTMX + CSV M4) |
| W-10 | Государственная поддержка — бесплатный скрининг; возможности в кабинетах онконастороженности; права и обязанности пациентов и врачей | ArticlePage callout placeholder with the 3 bullets | `tests/sections/test_seed.py::test_tz_bullets_verbatim_ru` | M1 | done |
| W-11 | Уход и поддержка — 3 columns verbatim (Физическое здоровье ×4 / Эмоциональная поддержка ×4 / Практические вопросы ×4) | `three_columns` block seeded verbatim | `tests/sections/test_seed.py::test_tz_bullets_verbatim_ru` | M1 | done |
| W-12 | Жизнь после рака — 3 columns verbatim (Наблюдение ×3 / Возвращение ×3 / Долгосрочное здоровье ×3) | `three_columns` block seeded verbatim | `tests/sections/test_seed.py::test_tz_bullets_verbatim_ru` | M1 | done |
| W-13 | Content formats: видеоролики врачей РОНЦ и ЦЗМиР; мобилограф-видео; инфографика и иллюстрации; истории пациентов (с согласия); материалы для распространения (мужья, дети, блогеры) | `Video` snippet (long/short_vertical), `image_gallery`, `PatientStoryPage`, `MaterialsPage` | M3/M5 tests | M3/M5 | todo |

## C. Section 2 — childhood cancer pages (TZ §2.2, spec §2.3)

| ID | Page / content (TZ verbatim) | Impl (seed path) | Test | M | Status |
|---|---|---|---|---|---|
| C-01 | Об онкозаболеваниях у детей (topic index) | `/uz/bolalar/bolalar-onkologiyasi-haqida/` `/ru/detskiy/ob-onkozabolevaniyah-u-detey/` | `tests/sections/test_seed.py::test_tz_bullets_verbatim_ru` | M1 | done |
| C-02 | Наиболее распространённые виды — 6 cards: Лейкозы (ОЛЛ, ОМЛ) / Лимфомы (Ходжкина, неходжкинская) / Опухоли мозга (медуллобластома, астроцитома) / Нейробластома / Саркомы (мягких тканей, Юинга) / Другие (Вилмса, ретинобластома, гепатобластома) | `cards_grid` with 6 cards verbatim | `tests/sections/test_seed.py::test_tz_bullets_verbatim_ru` | M1 | done |
| C-03 | Как работает детская онкокоманда (педиатр, онколог, медсестра, психолог) | ArticlePage | `tests/sections/test_seed.py::test_tz_bullets_verbatim_ru` | M1 | done |
| C-04 | Наследственный риск и генетическое тестирование: когда стоит проверить семью | ArticlePage | `tests/sections/test_seed.py::test_tz_bullets_verbatim_ru` | M1 | done |
| C-05 | Статистика по Узбекистану: распространённость, тренды (напр. беречь детей от пестицидов) (F17) | ArticlePage + `stat` placeholders | `tests/sections/test_seed.py::test_tz_bullets_verbatim_ru` | M1 | done |
| C-06 | Диагностика и лечение (topic index) | `/uz/bolalar/diagnostika-va-davolash/` | `tests/sections/test_seed.py::test_tz_bullets_verbatim_ru` | M1 | done |
| C-07 | Диагностика — лабораторные анализы; КТ, МРТ, ПЭТ; биопсия и гистология; как читать результаты: словарь для родителей (F14); вопросы врачу (F15) | ArticlePage + `glossary_terms` + `faq_accordion` | `tests/sections/test_seed.py`, `tests/glossary/test_term.py` | M1/M4 | done (glossary block + FAQ block seeded; tooltip tag M4) |
| C-08 | Лечение — химиотерапия; лучевая терапия у детей; трансплантация костного мозга; иммуно- и таргетная терапия; клинические испытания | ArticlePage, bullets verbatim | `tests/sections/test_seed.py::test_tz_bullets_verbatim_ru` | M1 | done |
| C-09 | Уход и поддержка — 3 columns verbatim (Физический уход ×4 / Эмоциональная поддержка ×4 / Практические вопросы ×4) | `three_columns` | `tests/sections/test_seed.py::test_tz_bullets_verbatim_ru` | M1 | done |
| C-10 | Информация для семьи — 2 columns verbatim (Для родителей ×5 / Для близких ×5) | `two_columns` | `tests/sections/test_seed.py::test_tz_bullets_verbatim_ru` | M1 | done |
| C-11 | Жизнь после рака — 3 columns verbatim (Наблюдение ×3 / Возвращение ×3 (школа) / Долгосрочное здоровье ×3) | `three_columns` | `tests/sections/test_seed.py::test_tz_bullets_verbatim_ru` | M1 | done |
| C-12 | Content formats: видео врачей Детской онкогематологии; мобилограф; инфографика; истории (согласие законного представителя) ; материалы (родители, дети, блогеры) | `Video`, `PatientStoryPage.consent_guardian`, `MaterialsPage` | M3/M5 tests | M3/M5 | todo |
| C-13 | Structure follows St. Jude "Together" model; content per PP-186 | page tree mirrors St. Jude "Together" structure; note in section intro | `tests/sections/test_seed.py::test_children_menu_has_the_five_tz_items` | M1 | done |

## D. Cross-cutting features F1–F17 (spec §2.4)

| ID | Feature | Impl | Test | M | Status |
|---|---|---|---|---|---|
| F1 | Bilingual ru/uz with switcher preserving page | wagtail-localize trees, `core_tags.lang_switch` / `hreflang_links` | `tests/core/test_templatetags.py` | M1 | done |
| F2 | Mobile adaptation | mobile-first CSS, 390 px screenshots | `tests/e2e/test_screens.py` | M1 | done (wireframe; design M5b) |
| F3 | Video (long + short vertical) | `Video` snippet, ffmpeg transcode | `tests/media_library` | M3 | todo |
| F4 | Infographics / galleries, downloadable | `image_gallery` block | `tests/articles/test_blocks.py` | M3 | todo |
| F5 | Feedback forms | `apps/feedback` | `tests/feedback` | M4 | todo |
| F6 | Navigation: mega-menu per section, breadcrumbs, sitemap | `apps/core/navigation.py`, `components/nav.html`, `breadcrumbs.html` | `tests/sections/test_models.py::test_navigation_structure_and_cache` | M1/M5 | wip (mega-menu + breadcrumbs done; sitemap per language M5) |
| F7 | Speed optimisation | caching §4.5, budgets §4.6 | `tests/perf/test_budgets.py` | M5 | todo |
| F8 | Stable operation: admin, updates, bug-fix, data protection | M6 DevOps + §8 security | M6 gate | M6 | todo |
| F9 | Social distribution: OG tags, share buttons, blogger materials | `share.html`, OG image task, `MaterialsPage` | `tests/core/test_seo.py` | M5 | todo |
| F10 | Patient stories with consent | `PatientStoryPage.clean()` | `tests/stories/test_consent.py` | M3 | todo |
| F11 | Where-to-go directory with regions | `apps/directory` | `tests/directory` | M4 | todo |
| F12 | 4-step patient route component | `steps` block | `tests/articles/test_blocks.py::test_steps_auto_number_and_deadline` | M2/M4 | wip (block done; tools page M4) |
| F13 | Step-by-step self-exam guide | `steps` block on Symptoms + `print.css` | `tests/sections/test_seed.py` | M2/M5 | wip (steps + placeholders + print skeleton; interactive M2) |
| F14 | Parents' glossary | `apps/glossary` Term + tooltip tag | `tests/glossary` | M4 | todo |
| F15 | Questions-to-ask-the-doctor checklists (both sections) | `faq_accordion` block | `tests/articles/test_blocks.py::test_faq_accordion_uses_details` | M2/M5 | wip (faq_accordion block + placeholders; print M5) |
| F16 | Support groups / psychological help contacts | `Institution.kind=psych_support|ngo` + care pages | `tests/directory` | M4 | todo |
| F17 | Statistics blocks (Uzbekistan) | `stat` block | `tests/articles/test_blocks.py::test_stat_render` | M2 | wip (stat block + placeholders; design M2) |

## E. Recommended additions A1–A8 (spec §2.5)

| ID | Feature | Impl | Test | M | Status |
|---|---|---|---|---|---|
| A1 | Screening eligibility helper | `apps/tools/screening.py` (table-driven) | `tests/tools/test_screening.py` (every boundary) | M4 | todo |
| A2 | Self-check checklists (women; children warning signs) | `apps/tools/selfcheck.py` | `tests/tools/test_selfcheck.py` | M4 | todo |
| A3 | Ask-a-question + moderated FAQ | `apps/faq` | `tests/faq` | M4 | todo |
| A4 | Full-text search (FTS, uz/ru, accent-insensitive) | `apps/search` + core migration `ertaaniqla` config | `tests/search` | M2 | todo |
| A5 | Printable/PDF key pages | print CSS | `tests/e2e/test_print.py` | M5 | todo |
| A6 | Telegram deep links + blogger materials page | `share.html`, `MaterialsPage` | `tests/core/test_seo.py` | M5 | todo |
| A7 | Yandex.Metrika behind consent; no ad trackers | `apps/analytics` | `tests/analytics` | M5 | todo |
| A8 | Accessibility toolbar | Alpine component, `tokens.css` | `tests/e2e/test_a11y.py` | M5 | todo |

## F. Cross-cutting engineering rules (spec §4–§12) — tracked at gate level

| ID | Rule | Impl | Test | M | Status |
|---|---|---|---|---|---|
| E-01 | Layout §4.2, settings split, env-only config | `config/settings/*`, `.env.example` | `tests/core/test_settings_prod.py` | M0 | wip |
| E-02 | `/healthz` `/readyz`, request-id, JSON logs | `apps/core/views.py`, `middleware.py` | `tests/core/test_infra.py` | M0 | wip |
| E-03 | Admin not at `/admin/`; CMS at `/cms/`; 2FA; axes lockout | `config/urls.py`, settings | `tests/core/test_infra.py` | M0/M7 | wip |
| E-04 | PII encrypted at rest, key rotation | `apps/core/fields.py` | `tests/core/test_fields.py` | M0 | wip |
| E-05 | CSP nonce, security headers | settings, nginx | `tests/core/test_infra.py` | M0/M6 | wip |
| E-06 | FTS config with unaccent | `apps/core/migrations/0001` | `tests/search` | M0/M2 | wip |
| E-07 | Docker multi-stage, compose dev/prod, Makefile §15, CI quality job | `docker/`, `compose*.yml`, `Makefile`, `.github/workflows/ci.yml` | CI | M0 | wip |
| E-08 | Coverage ≥ 85 %, ruff, mypy strict on core/tools/directory/feedback | `pyproject.toml` | CI | M0 | wip |
| E-09 | Translations complete uz+ru (CI check) | `scripts/check_translations.py` | CI | M0 | wip |
| E-10 | Data residency in Uzbekistan, backups in UZ, retention 90/180 d | RUNBOOK, purge jobs | `tests/faq`, `tests/feedback` | M4/M6 | todo |
| E-11 | Wireframe-only UI until Figma; tokens + components only (D-003) | `static/src/tokens.css`, `static/src/components.css`, `templates/components/` | — | all | wip (M1: tokens.css + components.css + templates/components) |
| E-12 | COMPONENT_INVENTORY.md (ru+uz) for the designer | `docs/COMPONENT_INVENTORY.md` | — | M1 | done (kept current every milestone) |

## Decisions column summary

See `docs/DECISIONS.md` for the full log; IDs referenced above: D-001 (Django 5.2/Wagtail 7),
D-003 (wireframe UI), D-004 (PII field), D-008 (Turnstile), D-009 (FTS config).
