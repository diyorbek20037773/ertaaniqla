# CLAUDE.md — «ERTA ANIQLA» / «ЭРТА АНИҚЛА» Onco-Awareness Portal

> This file is the single source of truth for Claude Code working in this repository.
> Read it fully before touching any file. When in doubt, the **Technical Specification (TZ)**
> in `docs/TZ_concept_ru.md` wins, then this file, then your own judgment.
> The developer (Qobiljon) is the **sole developer (front + back + DevOps)**. Everything you build
> must be maintainable by one person. Prefer boring, well-documented, widely-used solutions.

---

## 0. TL;DR for every session

1. Run `make check` (lint + type + tests) before and after every change.
2. Never invent medical facts. Content comes from doctors/copywriter via the CMS. Use clearly marked
   placeholders (`[[TODO: medical content — RONC review]]`) in seed data.
3. Every user-facing string exists in **two languages: Uzbek (`uz`, Latin script) and Russian (`ru`)**.
   No hard-coded text in templates — use `{% trans %}` / `{% blocktrans %}` or CMS fields.
4. Two sections, two colour identities, one navigation, one design system:
   - **🎗 Ayollar saratoni / Женский рак** (breast cancer = RMJ/РМЖ, cervical cancer = RShM/РШМ)
   - **🎀 Bolalar saratoni / Детский рак** (paediatric oncology)
5. Mobile-first. Assume 3G and a cheap Android phone in a regional town.
6. Accessibility (WCAG 2.1 AA) is a hard requirement — anxious, elderly, and low-literacy users.
7. Personal data (feedback forms, questions to a doctor) is sensitive health-adjacent data.
   Minimise collection, encrypt at rest, keep it on a server inside Uzbekistan.
8. Small, atomic commits. Conventional Commits. A PR-sized change = one feature.

---

## 1. Project identity

| Item | Value |
|---|---|
| Name | Erta aniqla (uz) / Эрта аниқла (ru transliteration) — "Detect early" |
| Domain | `ertaaniqla.uz` (TZ also mentions `oncoportal.uz` for publication — support both, canonical = `ertaaniqla.uz`) |
| Type | Information-and-education platform (NOT a medical service, NOT a diagnostic tool) |
| Legal basis | Presidential Resolution PP-402 (women's cancer early detection; TZ cites both 22.11.2024 and 24.11.2024 — `[[VERIFY: client]]`) and PP-186 (19.05.2025, National Strategy on childhood cancer to 2030) |
| Owner | Project Office "Innovation & Debureaucratization 2030", Agency for Strategic Development and Reforms; sponsors Yandex & Hamroh |
| Medical partners | RONC (Republican Oncology Scientific Centre), Centre for Mother & Child Health, Paediatric Onco-haematology. Content-strategy people named in TZ §III: D. Aniyezova (screening lead), S. Azlarova (psychologist), RONC doctors, paediatric oncologists/paediatricians/haematologists — pre-seed as `doctor_org`/reviewer choices, never as public contact data |
| DMED | TZ budget says "уточнить стоимость DMED" (national e-health platform). Integration/hosting scope is **undefined** — treat as open item, do not design it out: keep institution & screening data in importable/exportable form; record in ADR-0002 once the client answers |
| Audience | (a) women of all ages and their relatives (screening rules target 30–65; ultrasound <45); (b) parents/relatives of children with suspected/confirmed cancer; (c) general public, volunteers, bloggers; (d) editors/doctors (CMS users) |
| Support period | Developer contract includes support **until 31.12.2026** (TZ §5.1); plan M8 accordingly |
| Languages | `uz` (default, Latin), `ru`. Architecture must allow adding `uz-Cyrl` and `en` later without refactor. |
| Key idea | **Early detection.** Reduce fear, remove medical jargon, point to a concrete next step ("where to go"). |
| Timeline (TZ) | Prototype July 2026 → launch August 2026; content production through December 2026 |
| Server (TZ) | 8 vCPU / 16 GB RAM / 1 TB NVMe, single VPS |

### 1.1 Roles that will use the system

| Role | Needs |
|---|---|
| Visitor (anonymous) | Read, search, watch video, use self-check tools, find a clinic, submit a question, share |
| Editor (copywriter) | Create/edit bilingual articles in a rich editor, preview, schedule publish, manage media |
| Medical reviewer (doctor) | Review/approve pages; mark "medically verified by … on …" |
| Admin (developer) | Everything + settings, users, redirects, analytics, backups |

---

## 2. Non-negotiable requirements (100% of the TZ)

Everything in this section is **required**, not optional. Track each item in `docs/TZ_TRACE.md`
(a checklist mapping every TZ paragraph to code/pages/tests). A feature is not done until its
row in `TZ_TRACE.md` links to the implementing module and a test.

### 2.1 Platform structure (TZ §II)

- Two independent sections sharing one navigation and one design system; each section has its own colour identity (TZ requires distinct identities; the exact hues are the **designer's decision** — the values below are working defaults in tokens, swap when the designer delivers):
  - Women's section: default **pink/rose** (`--brand-w`), symbol 🎗
  - Children's section: default **gold/amber** (`--brand-c`), symbol 🎀 (keep emoji decorative only, provide SVG icons)
- Top-level menu of the women's section per TZ §II table = **5 items**: Осведомленность, Скрининг, Организация лечения, Куда обратиться, Государственная поддержка. «Уход и поддержка» and «Жизнь после рака» (TZ §2.1 body) are pages in the same subtree, reachable from the section index and the "Organisation of treatment"/state-support pages; whether they get top-menu slots is an editor setting (`show_in_menus`). Record in TZ_TRACE.
- Children's section top-level menu per TZ = 5 items: Об онкозаболеваниях у детей, Диагностика и лечение, Уход и поддержка, Информация для семьи, Жизнь после рака.
- Global home page presents both sections equally; hero slogan is a CMS field (copywriter; TZ key idea = "раннее выявление / erta aniqlash").

### 2.2 Section 1 — Women's cancer (breast & cervical) — required pages

```
/uz/ayollar/  (/ru/zhenskiy/)
├── Осведомленность / Ogohlik
│   ├── Что такое РМЖ и РШМ   — what happens in the body, stages, statistics for Uzbekistan
│   ├── Факторы риска         — age, heredity, lifestyle, HPV, others
│   └── Симптомы              — signs not to ignore; STEP-BY-STEP breast self-examination guide (interactive)
├── Скрининг
│   ├── Кому и как часто      — mammography 45–65 every 2 yrs; ultrasound <45 every 2 yrs; HPV test 30–50; self-exam calls
│   └── Где пройти            — family clinics (СВП), district polyclinics (onco-alertness rooms), Mother&Child Centre + branches; FREE under state programme
├── Организация лечения       — 4-step patient route:
│                               01 Первичный приём — therapist or gynaecologist at first signs or routine visit
│                               02 Направление на диагностику — ultrasound, mammography, tests, onco-alertness room, etc.
│                               03 Онколог / онкогинеколог — on suspicion/confirmation → referral to oncology centre
│                                  **"в соответствии с датами в ПП-402"** → seed placeholder `[[VERIFY: PP-402 referral deadlines]]`, render deadlines as a field per step
│                               04 Лечение — information on treatment stages
├── Куда обратиться           — directory of institutions (map + list, filter by region)
├── Государственная поддержка — free screening under state programme; opportunities in onco-alertness rooms; rights & duties of patients and doctors
├── Уход и поддержка          — 3 columns, items verbatim:
│     Физическое здоровье: питание во время лечения; управление побочными эффектами; уход за кожей и волосами; физическая активность и реабилитация
│     Эмоциональная поддержка: как справляться со страхом и тревогой; психологическая помощь — куда обратиться; поддержка близких и семьи; группы взаимопомощи пациентов
│     Практические вопросы: больничный и трудовые права; финансовая поддержка и льготы; как помочь близкому человеку с диагнозом; вопросы, которые важно задать врачу
└── Жизнь после рака          — 3 columns, items verbatim:
      Наблюдение после лечения: график контрольных осмотров; поздние эффекты лечения; паспорт здоровья пациента
      Возвращение к жизни: возврат к работе и привычному ритму; физическая реабилитация; эмоциональное восстановление
      Долгосрочное здоровье: профилактика рецидива; репродуктивное здоровье после лечения; психологическое благополучие в долгосрочной перспективе
```

Content formats (must be supported by the CMS for this section): long videos with RONC & Mother&Child doctors; short vertical "mobilograph" videos for social media (Instagram, Telegram, TikTok); infographics & symptom illustrations; real patient stories (with consent flag); shareable materials for husbands, children, volunteer bloggers.

### 2.3 Section 2 — Childhood cancer (family information) — required pages

Structure follows the **St. Jude "Together"** model (togetherbystjude.org) and PP-186.

```
/uz/bolalar/  (/ru/detskiy/)
├── Об онкозаболеваниях у детей
│   ├── Наиболее распространённые виды  — 6 cards: Leukaemias (ALL, AML) / Lymphomas (Hodgkin, non-Hodgkin) /
│   │                                      Brain tumours (medulloblastoma, astrocytoma) / Neuroblastoma /
│   │                                      Sarcomas (soft tissue, Ewing) / Others (Wilms, retinoblastoma, hepatoblastoma, rare)
│   ├── Как работает детская онкокоманда — paediatrician, oncologist, nurse, psychologist
│   ├── Наследственный риск и генетическое тестирование
│   └── Статистика по Узбекистану        — prevalence, trends, prevention (e.g. pesticides)
├── Диагностика и лечение
│   ├── Диагностика — lab tests; CT/MRI/PET; biopsy & histology; "how to read results: parents' glossary"; questions to ask the doctor
│   └── Лечение     — chemotherapy; radiotherapy in children; bone-marrow transplant; immuno/targeted therapy; clinical trials
├── Уход и поддержка         — 3 columns, items verbatim:
│     Физический уход: питание во время химиотерапии; управление болью; инфекционная безопасность; центральные венозные катетеры
│     Эмоциональная поддержка: как говорить с ребёнком о болезни; работа с тревогой у родителей; поддержка братьев и сестёр; психологические службы
│     Практические вопросы: обучение в больнице; финансовая помощь семьям; права ребёнка-пациента; группы поддержки
├── Информация для семьи     — 2 columns, items verbatim:
│     Для родителей: как справляться с эмоциями и не выгореть; уход за собой во время лечения ребёнка; как общаться с медицинской командой; совместное принятие решений о лечении; ресурсы юридической и финансовой помощи
│     Для близких: как помочь, когда не знаешь, что сказать; практическая помощь — что реально нужно семье; поддержка братьев и сестёр больного ребёнка; разговоры с бабушками и дедушками; сообщество семей — группы взаимопомощи
└── Жизнь после рака         — 3 columns, items verbatim:
      Наблюдение после лечения: график контрольных осмотров; поздние эффекты терапии; паспорт здоровья выжившего
      Возвращение к жизни: возврат в школу и учёба; физическая реабилитация; эмоциональное восстановление
      Долгосрочное здоровье: рост и развитие; репродуктивное здоровье; профилактика рецидива
```

Content formats for this section (same CMS capabilities, different people): long videos with **Paediatric Onco-haematology** doctors; short vertical "mobilograph" videos (Instagram, Telegram, TikTok); infographics & symptom illustrations; real patient stories (with consent — for minors, consent of the legal guardian, `consent_guardian: bool`); shareable materials for **parents, children, volunteer bloggers**.

### 2.4 Cross-cutting features required by the TZ

| # | Feature | TZ source |
|---|---|---|
| F1 | Bilingual (ru/uz) with language switcher preserving the current page | §IV "двуязычность" |
| F2 | Mobile adaptation | §5.1 developer task 1 |
| F3 | Video integration (long + short vertical) | §5.1 task 3, content formats |
| F4 | Infographics/illustrations (image galleries, downloadable) | same |
| F5 | Feedback forms ("обратная связь") | §5.1 task 3 |
| F6 | Navigation (mega-menu per section, breadcrumbs, sitemap) | same |
| F7 | Speed optimisation | same |
| F8 | Stable operation: administration, content updates, bug fixing, user-data protection | §5.1 task 2 |
| F9 | Social-media distribution: OG tags, share buttons (Telegram, Instagram, Facebook, copy link), materials for bloggers | §III |
| F10 | Patient stories with explicit consent handling | §II content formats |
| F11 | "Where to go" directory with regions | §II |
| F12 | Step-by-step patient route (4 steps) as a visual component | §II 2.1 |
| F13 | Step-by-step breast self-examination guide | §II 2.1 symptoms |
| F14 | Parents' glossary of medical terms | §II 2.2 diagnostics |
| F15 | "Questions to ask the doctor" checklists (both sections) | §II |
| F16 | Support groups / psychological help contacts | §II care & support |
| F17 | Statistics blocks (Uzbekistan) | §II both sections |

### 2.5 Strongly recommended additions (build them; they are cheap and directly serve "early detection")

| # | Feature | Why |
|---|---|---|
| A1 | **Screening eligibility helper** ("Am I due for screening?"): age + last test date → which test, how often, where. No account, no storage. | Turns the screening table into action |
| A2 | **Symptom self-check checklist** (women) and **"warning signs in children" checklist** (parents): checkbox list → result text "see a doctor within X days" + nearest clinic link. Never a diagnosis. Store nothing. | Reduces fear, drives visits |
| A3 | **Ask-a-question form** with moderated public FAQ (answered by doctors, anonymised) | Feedback form that produces content |
| A4 | Full-text search (Postgres FTS, both languages, accent-insensitive) | Content discovery |
| A5 | Printable/PDF version of key pages (self-exam guide, patient route, questions list) | Regional clinics print them |
| A6 | Telegram share deep links & a "materials for bloggers" downloads page | Distribution strategy in TZ |
| A7 | Yandex.Metrika + privacy-respecting server-side analytics; no third-party ad trackers | Sponsor is Yandex; measure reach |
| A8 | Accessibility toolbar (font size, high contrast) | Elderly audience |

---

## 3. Technology stack (pinned; do not swap without a written ADR)

| Layer | Choice | Notes |
|---|---|---|
| Language | Python 3.12 | `pyproject.toml`, `uv` for dependency management (fallback: pip-tools) |
| Web framework | Django 5.1 LTS-track | Settings split: `base/dev/prod/test` |
| CMS | **Wagtail 6.x** | Page tree, StreamField, rich text, image renditions, workflows, previews, redirects, sitemaps, search |
| i18n | `wagtail-localize` + Django i18n (`LocaleMiddleware`, `i18n_patterns`) | Page-level translation with translation memory |
| Database | PostgreSQL 16 | FTS with `unaccent` + custom dictionaries; JSONB for StreamField |
| Cache / queue broker | Redis 7 | Django cache, sessions, Celery broker, rate limiting |
| Background jobs | Celery 5 + celery-beat | Emails, video thumbnail extraction, sitemap ping, search index rebuild, backups |
| Frontend | Django templates + **HTMX 2** + **Alpine.js 3** + **Tailwind CSS 3** (`django-tailwind` or standalone CLI) | No SPA, no Node runtime in production image; Tailwind built at image build time |
| Forms | `django-crispy-forms` + `crispy-tailwind`, honeypot + Turnstile/hCaptcha | Anti-spam without Google reCAPTCHA (privacy) |
| Media | Local disk (`/srv/media`) behind nginx; images via Wagtail renditions (WebP/AVIF, `srcset`) | Ready to switch to S3-compatible (MinIO) via `django-storages` — abstract from day 1 |
| Video | Upload to CMS → Celery transcodes with `ffmpeg` to H.264 720p/480p + poster; served by nginx with byte-range; **also** allow embedding YouTube/Telegram links | Social videos come from the mobilograph |
| Search | Wagtail search with Postgres backend (`wagtail.search.backends.database`) | Upgrade path: Meilisearch |
| Web server | nginx (TLS, static/media, gzip+brotli, cache) → gunicorn (sync workers, `--workers 2*CPU+1` capped at 9) | Single-node |
| Containers | Docker + Docker Compose (prod & dev) | One `compose.yml`, overrides per env |
| CI/CD | GitHub Actions (lint → test → build → push → deploy over SSH) | Zero-downtime via `docker compose up --no-deps --wait web` behind nginx |
| Monitoring | Sentry (errors), Prometheus + Grafana or Uptime-Kuma + `django-prometheus`, nginx access logs → Loki (optional) | Alerts to Telegram |
| Backups | `pg_dump` nightly + media rsync to off-site (S3-compatible in UZ or 2nd server), 30-day retention, weekly restore test | Non-negotiable |
| Quality | `ruff` (lint+format), `mypy` (strict on `core/`), `pytest` + `pytest-django` + `factory_boy`, `django-debug-toolbar` (dev), `pre-commit` | `make check` |
| Security | `django-csp`, `django-axes` (admin brute force), HSTS, secure cookies, 2FA for CMS users (`django-otp` / `wagtail-2fa`), `pip-audit` in CI | See §8 |

---

## 4. System design

### 4.1 High-level

```
                    ┌──────────────────────────── VPS (Uzbekistan, 8c/16g) ────────────────────────────┐
 Internet ──TLS──►  │ nginx ──► gunicorn (Django+Wagtail)  ──► PostgreSQL 16                            │
 (Cloudflare        │   │           │        │             ──► Redis 7 (cache, sessions, broker)        │
  optional, DNS+    │   │           │        └── Celery worker + beat ──► ffmpeg, email, backups        │
  DDoS only)        │   ├── /static (immutable, hashed)                                                  │
                    │   ├── /media  (images, video; X-Accel-Redirect for private)                       │
                    │   └── micro-cache 10s for anonymous HTML                                            │
                    │ Sentry-agent · node_exporter · promtail  ──► Grafana/Loki (same host or separate)  │
                    └───────────────────────────────────────────────────────────────────────────────────┘
```

Design principles:

- **Read-heavy, write-rare.** 99.9% of traffic is anonymous reads. Cache aggressively: Wagtail page cache via `django-cache` per URL+language, nginx micro-cache, `Cache-Control: public, max-age=300, stale-while-revalidate=3600` for anonymous HTML; immutable static assets with 1-year TTL.
- **Everything is a Wagtail Page or a Snippet.** No bespoke article models outside Wagtail. Editors never touch Django admin except for users.
- **Sections are page-tree subtrees**, not separate apps: `HomePage → SectionIndexPage(women) / SectionIndexPage(children) → TopicIndexPage → ArticlePage`. Section colour and navigation derive from the nearest `SectionIndexPage` ancestor.
- **Translation is a first-class tree.** `wagtail-localize` creates `/uz/...` and `/ru/...` trees; slugs are per-language; `hreflang` emitted automatically.
- **Stateless web containers.** No local state; media on a volume; sessions in Redis. Enables `docker compose scale web=2`.
- **Fail soft.** If Redis is down, site still serves (cache falls back to dummy with a Sentry alert). If Celery is down, forms still save; email is retried later.

### 4.2 Django project layout

```
ertaaniqla/
├── CLAUDE.md
├── README.md
├── pyproject.toml            # deps, ruff, mypy, pytest config
├── Makefile                  # make dev / check / test / build / deploy / backup
├── compose.yml               # base services
├── compose.dev.yml           # bind mounts, debug toolbar, mailpit
├── compose.prod.yml          # restart policies, resource limits, logging drivers
├── .env.example
├── docker/
│   ├── web/Dockerfile        # multi-stage: node (tailwind build) → python slim; non-root user
│   ├── nginx/nginx.conf, sites/ertaaniqla.conf, snippets/{security,cache,gzip}.conf
│   └── scripts/{entrypoint.sh,wait-for.sh,backup.sh,restore.sh,healthcheck.sh}
├── docs/
│   ├── TZ_concept_ru.md      # verbatim TZ (converted from docx)
│   ├── TZ_TRACE.md           # requirement → implementation → test
│   ├── ADR/0001-stack.md …   # architecture decision records
│   ├── CONTENT_MODEL.md      # page types, StreamField blocks, editor guide
│   ├── RUNBOOK.md            # deploy, rollback, backup/restore, incident steps
│   └── EDITOR_GUIDE_ru.md / EDITOR_GUIDE_uz.md
├── config/
│   ├── settings/{base,dev,prod,test}.py
│   ├── urls.py               # i18n_patterns, wagtail urls, sitemap, robots, healthz
│   ├── wsgi.py, asgi.py, celery.py
├── apps/
│   ├── core/                 # abstract base pages, mixins, SEO, section theming, template tags, middleware
│   ├── home/                 # HomePage
│   ├── sections/             # SectionIndexPage, TopicIndexPage (women / children share models)
│   ├── articles/             # ArticlePage + StreamField blocks (all content blocks live here)
│   ├── media_library/        # VideoPage/Video snippet (transcoding), Infographic, downloadable materials
│   ├── directory/            # Institution (clinic) model, Region, map page, "where to go"
│   ├── tools/                # screening helper, self-check checklists, patient route (HTMX views, no DB)
│   ├── stories/              # PatientStoryPage with consent metadata
│   ├── faq/                  # Question form + moderated FAQ pages
│   ├── glossary/             # Term snippets + glossary page + inline tooltip tag
│   ├── feedback/             # generic contact/feedback form, storage, export, retention
│   ├── search/               # search view, Postgres FTS config, synonyms uz/ru
│   ├── analytics/            # Metrika tag, consent banner, server-side event log (optional)
│   └── users/                # CMS user roles (Editor, Medical Reviewer, Admin), 2FA enforcement
├── templates/                # base.html, section layouts, components/ (BEM-ish partials), emails/
├── static/src/               # tailwind input.css, alpine components, htmx extensions
├── locale/{uz,ru}/LC_MESSAGES/django.po
├── tests/                    # mirrors apps/, plus e2e/ (Playwright smoke), perf/ (locust)
└── scripts/                  # seed_content.py, import_institutions.py, make_fixtures.py
```

### 4.3 Content model (Wagtail) — implement exactly

**Abstract `BasePage(Page)`** in `core`:
- `seo_title`, `search_description` (Wagtail built-ins) + `og_image`, `noindex: bool`
- `last_reviewed_by: FK(User) null`, `last_reviewed_at: date null`, `medically_verified: bool` → renders the "Проверено врачом / Shifokor tekshirgan" badge
- `show_in_menus` default True
- `get_section()` → nearest `SectionIndexPage` or None
- `reading_time` computed from StreamField text

**`HomePage`**: hero (title, subtitle, two CTA cards to sections), `featured_articles` (orderable, max 6), `featured_videos` (max 3), statistics strip (3 stat blocks), `emergency_banner` (optional text, e.g. screening campaign month).

**`SectionIndexPage`**: `section_key: choices(women|children)`, `colour_primary`, `colour_accent`, `icon`, intro StreamField, `subsections` auto from children. Provides the mega-menu for its subtree.

**`TopicIndexPage`**: (e.g. "Скрининг", "Диагностика и лечение") intro + auto-listing of child `ArticlePage`s as cards (image, title, summary, reading time).

**`ArticlePage`**: `summary` (max 300), `hero_image`, `body: StreamField` with these blocks (all bilingual through localize):

| Block | Fields | Used for |
|---|---|---|
| `rich_text` | limited features: h2,h3,bold,italic,ol,ul,link,document-link,image,embed | body text |
| `callout` | `kind: info|warning|danger|success`, `title`, `text` | "Не откладывайте визит" |
| `three_columns` | 3× (`title`, rich_text list) | Care & Support / Life after cancer tables from TZ |
| `two_columns` | 2× (`title`, rich_text) | "Кому и как часто / Где пройти", "Для родителей / Для близких" |
| `steps` | list of (`number`, `title`, `text`, optional link) | 4-step patient route; self-exam steps |
| `cards_grid` | list of (`icon/image`, `title`, `text`, `link`) | 6 childhood cancer types; risk factors |
| `symptom_list` | list of (`symptom`, `urgency: routine|soon|urgent`, `explanation`) | Symptoms pages, rendered with colour coding |
| `stat` | `value`, `label`, `source`, `year` | Uzbekistan statistics |
| `video` | FK to `Video` snippet or external URL, caption, transcript (rich text) | doctor videos; transcript = accessibility + SEO |
| `image_gallery` | images with captions, `downloadable: bool` | infographics |
| `document_download` | Wagtail Document, description | printable materials |
| `faq_accordion` | list of (`q`, `a`) | questions to ask a doctor |
| `glossary_terms` | selected Term snippets | inline definitions |
| `institution_list` | filter by region/type | "Где пройти" |
| `cta` | text, button label, page/URL, style by section | |
| `quote` | text, author, role | patient/doctor quotes |
| `table` | Wagtail TypedTable | screening schedule |
| `embed` | oEmbed / provider embed (YouTube, Telegram, Instagram, TikTok) — TikTok/Instagram embeds load only after user click (privacy, weight) | |

**`PatientStoryPage(BasePage)`**: `person_display_name` (may be pseudonym), `consent_obtained: bool` (required True to publish — enforce in `clean()`), `consent_document` (private Document, never public), `section`, `diagnosis_short` (plain text, editor-written), body StreamField, `hero_image`, `is_anonymised`.

**`Video` (snippet)**: `title`, `kind: long|short_vertical`, `source: upload|youtube|telegram|instagram|tiktok`, `file`, `external_url`, `poster`, `duration`, `doctor_name`, `doctor_org`, `transcript`, `subtitles_uz`, `subtitles_ru` (VTT), `status: uploaded|processing|ready|failed`, renditions JSON. Celery task `transcode_video`.

**`Institution` (snippet + `directory` app)**: `name`, `kind: svp|polyclinic|onco_room|mother_child_centre|oncology_centre|paediatric_oncohaematology|psych_support|ngo`, `region: FK(Region)`, `district`, `address`, `phone`, `hours`, `lat`, `lng`, `free_under_state_programme: bool`, `services: M2M(Service)` (mammography, ultrasound, HPV test, consultation…), `sections` (women/children/both), `verified_at`. `Region` = 14 regions (12 viloyat + Tashkent city + Karakalpakstan). Map: Leaflet + OpenStreetMap tiles (self-hosted tile proxy optional), fallback to list. Import via CSV management command.

**`Term` (snippet)**: `term`, `definition`, `section`, `synonyms`. Template tag `{% glossary_wrap %}` wraps first occurrence in `<abbr>`-style tooltip.

**`Question` (model, `faq`)**: `name (optional)`, `contact (optional, encrypted)`, `section`, `text`, `consent_to_publish: bool`, `status: new|answered|published|rejected`, `answer`, `answered_by`. Published Q&As appear on `FAQPage`. PII fields encrypted with `django-fernet-fields`-style field or `pgcrypto`; auto-purge contact after 90 days (Celery beat).

**`FeedbackSubmission`**: `kind: feedback|bug|partnership`, `text`, `contact (encrypted, optional)`, `page_url`, `user_agent`, `created_at`; retention 180 days.

**Site settings (Wagtail `BaseSiteSetting`)**: hotline phones, social links, footer text, Metrika ID, emergency banner, partner logos (Yandex, Hamroh, Agency), legal texts.

### 4.4 URL scheme

```
/                          → redirect to /uz/ (Accept-Language aware, cookie remembers)
/uz/ … /ru/ …              → i18n_patterns
/uz/ayollar/…              /ru/zhenskiy/…
/uz/bolalar/…              /ru/detskiy/…
/uz/qayerga-murojaat/      /ru/kuda-obratitsya/     (directory + map)
/uz/vositalar/skrining/    /ru/instrumenty/skrining/ (screening helper)
/uz/vositalar/oz-tekshiruv/                          (self-check)
/uz/savol-javob/           /ru/voprosy-otvety/
/uz/hikoyalar/             /ru/istorii/
/uz/lugat/                 /ru/slovar/
/uz/qidiruv/?q=            /ru/poisk/?q=
/uz/materiallar/           /ru/materialy/            (downloads for bloggers, clinics)
/cms/                      Wagtail admin (IP allow-list optional, 2FA required)
/django-admin/             superusers only
/healthz/  /readyz/        no auth, no cache
/sitemap.xml /robots.txt
```

Slugs are editor-controlled per language; Wagtail `redirects` app handles renames.

### 4.5 Request flow & caching

1. nginx: TLS termination, static/media served directly, `proxy_cache` micro-cache 10s for anonymous GET HTML (bypass when `sessionid`/`csrftoken` cookie or `Authorization` present).
2. Django `UpdateCacheMiddleware`/`FetchFromCacheMiddleware` **not** used (too coarse). Instead: Wagtail `cache_page`-style per-view cache keyed on `(url, lang, section)` for 5 minutes, with **explicit invalidation** on `page_published` / `page_unpublished` signals → `cache.delete_pattern` via redis.
3. Template fragment caching for nav mega-menu (`{% cache 3600 nav lang %}`), footer, institution lists.
4. HTMX partial responses share the same cache keys with a `HX-Request` vary.
5. Image renditions pre-generated on publish (`prefetch_renditions`), served with far-future headers.

### 4.6 Performance budgets (CI fails if violated in Lighthouse CI on 3 key pages)

- LCP < 2.5 s on "Slow 4G", CLS < 0.1, TBT < 200 ms
- HTML ≤ 60 KB gz, CSS ≤ 40 KB gz (Tailwind purged), JS ≤ 50 KB gz total (HTMX 14 KB + Alpine 15 KB + own)
- Images: responsive `srcset`, WebP + fallback, lazy below the fold, explicit width/height
- Fonts: 1 family, 2 weights, `font-display: swap`, self-hosted WOFF2, subset Latin+Cyrillic
- p95 server time for cached page < 30 ms; uncached < 250 ms

---

## 5. Frontend rules

- Tailwind with a small design-token layer in `static/src/tokens.css`: `--brand-w-*`, `--brand-c-*`, neutral, semantic (`--info/--warning/--danger`). Section theme applied via `data-section="women|children"` on `<body>`; components use `text-[color:var(--brand)]` so one component serves both sections.
- Component partials in `templates/components/` (`card.html`, `callout.html`, `steps.html`, `video.html`, `symptom_list.html`, `stat.html`, `breadcrumbs.html`, `lang_switch.html`, `share.html`, `institution_card.html`). Each partial documented with its context variables at the top.
- HTMX for: search-as-you-type, region filter on directory, form submission with inline validation, "load more" listings, language switch without full reload where cheap. Always ensure a non-JS fallback (real `<form>`/`<a>`).
- Alpine for: mobile menu, accordion, tabs, self-check checklist state, accessibility toolbar (persist in `localStorage`).
- No inline scripts (CSP nonce for the few needed). No jQuery. No third-party CSS frameworks besides Tailwind.
- Typography: base 18px on mobile for readability; line length ≤ 70ch; high contrast (≥ 4.5:1); minimum tap target 44px.
- Tone components: a `reassurance` callout style ("Bu belgi har doim saraton degani emas") used on symptom pages — copywriter fills text.
- Print stylesheet for article, patient route, self-exam guide, questions checklists.
- RTL not required. Uzbek Latin diacritics (oʻ, gʻ, ʼ) must render — check font subset includes U+02BB/U+02BC.

---

## 6. Backend engineering standards

- Type hints everywhere; `mypy --strict` on `apps/core`, `apps/tools`, `apps/directory`, `apps/feedback`.
- Fat models / thin views; business logic in `services.py` per app; views are ≤ 30 lines.
- Every model: `__str__`, `Meta.ordering`, `verbose_name` in ru+uz (`gettext_lazy`), indexes for filter fields, `created_at/updated_at` via `TimeStampedModel`.
- Migrations are reviewed, squashed before launch, never edited after deploy.
- Query discipline: `select_related/prefetch_related` in listings; `assertNumQueries` tests on list pages; `django-debug-toolbar` in dev; N+1 = bug.
- Forms: server-side validation is the truth; HTMX only mirrors it. Rate limit form POSTs (`django-ratelimit` via Redis: 5/min/IP). Honeypot field + Turnstile.
- Emails via Celery, templates in `templates/emails/` (txt + html), Mailpit in dev.
- Management commands: `seed_content` (creates full page tree in both languages with placeholders exactly matching the TZ structure), `import_institutions`, `rebuild_search`, `purge_pii`, `check_links`.
- Logging: JSON to stdout (`python-json-logger`), request-id middleware, no PII in logs.
- Settings from env only (`django-environ`); `.env` never committed; `SECRET_KEY` rotation documented.
- Feature flags via `django-waffle` for tools that need medical sign-off before going public.
- API: not required for launch. If needed, expose read-only Wagtail API v2 at `/api/v2/` for a future mobile app/Telegram bot — design page models so this works (no view-only logic in templates).

---

## 7. Internationalisation rules

- **Decision (TZ says only "двуязычность")**: default language `uz`, Uzbek in **Latin** script; `uz-Cyrl` can be added later. Record in TZ_TRACE/ADR-0003.
- `LANGUAGE_CODE = "uz"`, `LANGUAGES = [("uz","Oʻzbekcha"),("ru","Русский")]`, `WAGTAIL_I18N_ENABLED = True`, `WAGTAIL_CONTENT_LANGUAGES = LANGUAGES`.
- Uzbek uses **Latin script** in UI. Provide a `uz-Cyrl` locale stub so switching later is a config change.
- All static UI strings in `.po` files; run `make messages` / `make compilemessages` in CI; CI fails on untranslated strings for `ru` and `uz` (`polib` check script).
- Dates/numbers localised; phone numbers formatted `+998 XX XXX-XX-XX`.
- Language switcher links to the **translated counterpart of the same page** (localize `get_translation_or_none`), falling back to the section root.
- `hreflang` + `x-default` in `<head>`; separate sitemaps per language.
- Search: Postgres FTS config `simple` + `unaccent`; add a synonym dictionary for common uz/ru medical terms (e.g. "ko'krak"↔"грудь", "saraton"↔"рак", "skrining"↔"скрининг"). Latin/Cyrillic transliteration normaliser for queries.

---

## 8. Security & data protection (treat as a health-adjacent public-sector site)

- Comply with the Law of the Republic of Uzbekistan "On Personal Data" (ЗРУ-547): personal data of citizens is processed and **stored on servers physically located in Uzbekistan** → VPS provider must be in UZ; backups off-site also in UZ. Document in `docs/RUNBOOK.md`.
- Data minimisation: no accounts for visitors; forms ask only what is needed; contact fields optional; explicit consent checkbox with link to the privacy policy page (CMS-editable, both languages).
- Encryption: TLS 1.2+ only, HSTS preload; PII columns encrypted at application level (Fernet key from env; key rotation command); disk encryption on the VPS if the provider supports it.
- Retention: contacts in `Question` purged 90 days after answer; `FeedbackSubmission` 180 days; Celery beat job + test.
- CMS: 2FA mandatory for all staff; `django-axes` lockout; strong password validators; session timeout 8 h; admin URL not `/admin/`; optional IP allow-list in nginx for `/cms/`.
- Headers: CSP (nonce-based, `frame-ancestors 'none'`, allow YouTube/Telegram/Instagram/TikTok embeds explicitly (`frame-src`), click-to-load facade for the last two), `X-Content-Type-Options`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy` minimal.
- Uploads: validate MIME with `python-magic`, strip EXIF (GPS!) from images, size limits, videos transcoded (never serve raw upload), documents scanned with ClamAV container (optional but wired).
- Dependencies: `pip-audit` + Dependabot; base image `python:3.12-slim` rebuilt weekly by CI.
- No Google Analytics/Tag Manager. Yandex.Metrika only after consent banner; IP anonymisation on.
- Medical disclaimer in footer and on every tool page: "Sayt tashxis qo'ymaydi; shifokorga murojaat qiling" (copywriter provides final text).
- Threat model doc `docs/SECURITY.md`: defacement, spam, DDoS (Cloudflare optional in front, but origin must still work without it), PII leak, admin takeover.

---

## 9. Accessibility (WCAG 2.1 AA) — audit is part of Definition of Done

- Semantic landmarks, one `h1` per page, logical heading order, skip-link.
- Keyboard-operable menus, accordions, tabs, modals (Alpine with focus trap).
- Colour is never the only carrier of meaning (urgency icons + text).
- All images: `alt` required in CMS (Wagtail `WAGTAILIMAGES_ALT_TEXT_REQUIRED`), decorative marked as such.
- Video: poster, captions (VTT) in both languages, transcript below.
- Forms: labels, `aria-describedby` for errors, error summary at top.
- `pa11y-ci` on key pages in CI; axe in Playwright e2e.
- Accessibility toolbar: font size ×1.25/×1.5, high-contrast theme, reduce motion honours `prefers-reduced-motion`.

---

## 10. SEO & distribution

- Wagtail `sitemap`, `robots.txt`, canonical URLs, `hreflang`.
- Structured data (JSON-LD): `MedicalWebPage` / `Article` with `reviewedBy` (doctor) and `lastReviewed`, `Organization`, `BreadcrumbList`, `FAQPage` for Q&A, `VideoObject` for videos, `MedicalClinic` for institutions.
- OpenGraph/Twitter cards; OG image auto-generated per page via Pillow template with section colour (Celery on publish).
- Share bar: Telegram, Instagram (copy link + "download story image" 1080×1920), TikTok (copy link + download vertical video), Facebook, WhatsApp, copy link. Telegram first — dominant in UZ. TZ names Instagram, Telegram, TikTok as the target networks.
- Blogger kit page: downloadable infographics, short-video files, ready captions in uz/ru, hashtags — all CMS-managed.
- Yandex.Webmaster + Google Search Console verification via site settings.

---

## 11. DevOps — build this like a senior SRE would, but keep it one-person-operable

### 11.1 Containers

- `docker/web/Dockerfile`: stage 1 `node:20-alpine` builds Tailwind → stage 2 `python:3.12-slim` installs deps with `uv`, copies app, `collectstatic` (with `ManifestStaticFilesStorage` + whitenoise as fallback), non-root `app` user, `HEALTHCHECK` hits `/healthz/`.
- Same image runs `web` (gunicorn), `worker` (celery), `beat`, `migrate` (one-shot) via different commands.
- `compose.yml` services: `nginx`, `web`, `worker`, `beat`, `db` (postgres:16-alpine), `redis` (redis:7-alpine, `appendonly yes`), `backup` (cron container), optional `clamav`, `mailpit` (dev only), `grafana`/`prometheus`/`loki`/`promtail` (prod, profile `monitoring`).
- Resource limits in `compose.prod.yml` (web 4 GB, db 4 GB shared_buffers 2 GB, redis 512 MB, worker 2 GB). `restart: unless-stopped`. `logging: json-file, max-size 50m, max-file 5`.
- Named volumes: `pgdata`, `media`, `static`, `redisdata`, `letsencrypt`. Everything under `/srv/ertaaniqla/`.
- Postgres tuned for 16 GB host: `shared_buffers=2GB`, `effective_cache_size=6GB`, `work_mem=32MB`, `maintenance_work_mem=512MB`, `wal_level=replica`, `max_wal_size=2GB`. PgBouncer not needed at this scale (document the trigger to add it: > 200 concurrent conns).

### 11.2 nginx

- TLS via `certbot` (dns or webroot), auto-renew, OCSP stapling, TLS 1.2/1.3, modern ciphers, HTTP/2 (+HTTP/3 if built), HSTS.
- `gzip` + `brotli` for text; `open_file_cache`; `sendfile`; `client_max_body_size 512m` only on `/cms/` for video uploads, 2m elsewhere.
- `/static/` `expires 1y, immutable`; `/media/` `expires 30d`; video with `mp4` module byte-range.
- `proxy_cache` micro-cache for anonymous HTML (`proxy_cache_key "$scheme$host$request_uri$http_accept_language_cookie_lang"`), `proxy_cache_use_stale error timeout updating`.
- Rate limit zones: general 30 r/s burst 60 per IP; `/cms/login/` 5 r/m; form POST 10 r/m.
- Security headers in one snippet; block `.git`, `.env`, dotfiles; return 444 for unknown hosts.
- Maintenance page toggle (`/srv/maintenance.flag`).

### 11.3 CI/CD (GitHub Actions)

```
on: push/PR
jobs:
  quality:  ruff → mypy → pytest (postgres+redis services) → coverage ≥ 85% on apps/ → pip-audit → translations check
  frontend: tailwind build → lighthouse-ci + pa11y-ci against a preview container on 3 URLs
  build:    docker buildx → ghcr.io/<org>/ertaaniqla:sha + :latest (main only), SBOM (syft), image scan (trivy, fail on HIGH)
  deploy:   (main, manual approval for prod) ssh → `docker compose pull && docker compose run --rm migrate && docker compose up -d --no-deps --wait web worker beat` → smoke test /healthz/ + 3 pages → Telegram notification
  rollback: workflow_dispatch with image tag
```

- Staging environment = same compose on a `staging.ertaaniqla.uz` subdomain (can share the VPS, separate compose project + DB). Every merge to `main` auto-deploys to staging; prod is a manual approval.
- Migrations must be backward-compatible with the previous image (expand/contract) so `--wait` rollovers are zero-downtime.

### 11.4 Backups & DR

- `backup` container: nightly 02:00 `pg_dump -Fc` + `restic` snapshot of `pgdump + media` to an S3-compatible bucket in Uzbekistan (or second VPS via SFTP), encryption on, retention 7 daily / 4 weekly / 6 monthly.
- Weekly automated **restore test** into a scratch Postgres container, count pages, alert on failure.
- `make restore DATE=…` documented in RUNBOOK; RPO 24 h, RTO 2 h. Document how to rebuild the VPS from scratch in ≤ 1 h (`scripts/bootstrap_vps.sh`: docker install, firewall (ufw: 22 restricted, 80, 443), fail2ban, unattended-upgrades, swap 4 GB, sysctl, clone repo, restore).

### 11.5 Observability

- `/healthz/` (process up) vs `/readyz/` (DB + Redis ping) — nginx uses `/healthz/`, deploy uses `/readyz/`.
- Sentry with release = git SHA, environment, PII scrubbing, performance sampling 10%.
- Prometheus: `django-prometheus`, `nginx-prometheus-exporter`, `postgres_exporter`, `redis_exporter`, `node_exporter`; Grafana dashboards committed as JSON; alert rules: 5xx rate > 1%, p95 > 1 s, disk > 80%, backup age > 26 h, cert expiry < 14 d, Celery queue > 100 → Telegram bot.
- Uptime check from outside (Uptime-Kuma on another host or a free external monitor).
- Logs: JSON, rotated; optional Loki. Access logs anonymise last IP octet.

### 11.6 Environments & secrets

- `.env.example` documents every variable. Secrets on the server in `/srv/ertaaniqla/.env` (chmod 600), in GitHub via Environments secrets. Never in images.
- `DJANGO_SETTINGS_MODULE=config.settings.prod`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` include both domains.

---

## 12. Testing strategy

| Level | Tool | Must cover |
|---|---|---|
| Unit | pytest | services, template tags, blocks' `clean`, consent enforcement, PII encryption/purge, screening helper logic (table-driven from the TZ screening rules), self-check scoring |
| Model/page | pytest-django + wagtail test utils | every page type can be created, published, translated; `seed_content` builds the full TZ tree; `get_section()`; slug uniqueness per locale |
| View | Django test client | every URL in §4.4 returns 200 in both languages; cache invalidation on publish; HTMX partials; forms happy/sad paths; rate limits |
| Integration | docker compose in CI | migrations from zero; Celery transcoding on a 3-second sample video; backup script produces a restorable dump |
| E2E | Playwright | mobile viewport: home → section → article → share; language switch keeps page; directory filter; question form submit; CMS login with 2FA; editor creates & translates an article |
| Accessibility | pa11y-ci, axe | key pages 0 serious violations |
| Performance | Lighthouse CI, locust (200 users, 5 min) | budgets §4.6; no errors, p95 < 300 ms cached |
| Security | pip-audit, trivy, `django check --deploy`, ZAP baseline (optional) | no HIGH |

Coverage gate 85%. Tests live in `tests/` mirroring `apps/`; fixtures via `factory_boy`.

---

## 13. Delivery plan (milestones — each ends with `make check` green, TZ_TRACE updated, tagged release)

| M | Scope | Target |
|---|---|---|
| M0 | Repo scaffold, Docker dev env, settings split, CI skeleton, `docs/TZ_concept_ru.md`, `TZ_TRACE.md`, ADR-0001 | day 1–2 |
| M1 | Core page models + StreamField blocks, i18n with wagtail-localize, `seed_content` creating the **complete TZ tree in uz+ru** with placeholders, base templates, design tokens, nav, footer, language switch | week 1 |
| M2 | All article-level components (steps, three_columns, symptom_list, cards_grid, stat, callout, table, faq_accordion), section theming, home page, search | week 2 |
| M3 | Media: Video snippet + ffmpeg transcoding, galleries, downloads, OG image generation; stories with consent | week 3 |
| M4 | Directory (regions, institutions, map, filters, CSV import), tools (screening helper, self-checks, patient route), FAQ/question form, feedback form, glossary | week 4 |
| M5 | SEO (JSON-LD, sitemaps, hreflang), accessibility pass, performance pass, print styles, blogger kit page | week 5 |
| M6 | Prod DevOps: nginx/TLS, compose.prod, backups + restore test, monitoring, alerts, staging, CD pipeline, RUNBOOK, VPS bootstrap script, security hardening, 2FA | week 6 |
| M7 | Editor guides (ru/uz), CMS roles & workflow (editor → medical reviewer → publish), UAT with copywriter/designer, load test, launch checklist | week 7 |
| M8 | Launch on `ertaaniqla.uz`; support period per TZ until **31.12.2026**: analytics review, bug-fix SLA 48 h, content-update help for editors, monthly dependency updates, quarterly restore drill, hand-over doc for the support programmer | Aug → Dec 2026 |

Definition of Done for any feature: code + tests + docs + translation strings + TZ_TRACE row + accessibility check + no new Sentry errors on staging for 24 h.

---

## 14. How Claude Code must work in this repo

1. **Start every task by reading** `CLAUDE.md`, `docs/TZ_TRACE.md`, and the relevant `apps/<app>/README.md`. State the plan in 5–10 bullets before writing code; wait for confirmation on anything that changes architecture, dependencies, or the data model.
2. **One feature per branch** (`feat/…`, `fix/…`, `ops/…`). Conventional Commits in English (`feat(directory): add region filter with HTMX`). Keep diffs small; explain non-obvious decisions in the commit body.
3. **Never** commit secrets, real patient data, or real doctor contact details. Seed data is obviously fake.
4. **Never write medical content.** Where the TZ specifies content (e.g., "mammography 45–65 every 2 years"), copy it verbatim into seed data and mark `[[VERIFY: doctor]]`. Where the TZ says "будет содержаться информация…", create the page with a structured placeholder listing the TZ bullet points so the copywriter sees exactly what to fill.
5. Always produce **both** `uz` and `ru` for any string/page you create. Uzbek placeholder text should be real Uzbek (Latin), not transliterated Russian.
6. Run `make check` and `make test` before declaring done; paste the summary. If a test cannot run in your environment, say so explicitly.
7. Write/update an ADR in `docs/ADR/` for any new dependency or infra choice; keep `docs/RUNBOOK.md` in sync with any ops change.
8. Prefer Wagtail's built-in mechanisms (workflows, revisions, redirects, sitemaps, search, settings, snippets, TypedTable, localize) over custom code.
9. Every new template component gets: a docstring of context vars, dark-mode-free (site is light-only by design), mobile screenshot check via Playwright in `tests/e2e/screenshots/`.
10. When the TZ is ambiguous, list the options with trade-offs and pick the one that is simplest to operate by one developer; record it in `TZ_TRACE.md` "Decisions" column.
11. Respond to the developer in **Uzbek** for explanations and in English for code, identifiers, commit messages, and docs (docs that editors read are ru+uz).
12. Never delete data-bearing tables/columns in the same release as the code that stops using them (expand → migrate → contract).

---

## 15. Make targets (implement these)

```
make dev            # docker compose up (dev overrides), tailwind watch
make shell          # django shell_plus
make migrate / makemigrations
make seed           # seed_content --lang uz,ru ; import_institutions data/institutions.csv
make messages / compilemessages
make lint / fmt / type / test / check   # check = lint+type+test+translations
make e2e            # playwright
make lighthouse     # lhci autorun against local
make build          # docker build with tailwind
make deploy ENV=staging|prod
make backup / restore DATE=YYYY-MM-DD
make logs SERVICE=web
```

---

## 16. Glossary (so the code and the domain match)

| Term (ru/uz) | Meaning | Code identifier |
|---|---|---|
| РМЖ / Ko'krak bezi saratoni | Breast cancer | `breast_cancer` |
| РШМ / Bachadon bo'yni saratoni | Cervical cancer | `cervical_cancer` |
| Онконастороженность / Onkologik ogohlik | Cancer alertness/awareness | `onco_alertness` |
| Кабинет онконастороженности | Onco-alertness room in polyclinic | `Institution.kind = onco_room` |
| СВП / Oilaviy shifokorlik punkti | Family doctor point | `svp` |
| РОНЦ | Republican Oncology Scientific Centre | `ronc` |
| Центр здоровья матери и ребёнка | Mother & Child Health Centre | `mother_child_centre` |
| Мобилограф | Mobile-phone videographer (short vertical video) | `Video.kind = short_vertical` |
| Маршрут пациента / Bemor yo'li | 4-step patient route | `steps` block, `tools.patient_route` |
| Паспорт здоровья | Health passport (follow-up record) | content only |
| ПП-402 / ПП-186 | Presidential resolutions | referenced in footer/legal page |

---

*Last updated: 2026-09-15. Keep this file under 1,500 lines; move details into `docs/`.*
