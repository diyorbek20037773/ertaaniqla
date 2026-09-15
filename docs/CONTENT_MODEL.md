# CONTENT_MODEL.md — page types, blocks, settings (developer reference)

Implements spec §4.3 exactly. Editor-facing guides live in `EDITOR_GUIDE_ru.md` / `_uz.md` (M7).

## Page tree

```
Root
└── HomePage (uz)  ⇄ HomePage (ru)            apps/home        /uz/  /ru/
    ├── SectionIndexPage women                 apps/sections    /uz/ayollar/  /ru/zhenskiy/
    │   ├── TopicIndexPage   Осведомленность      └── ArticlePage ×3
    │   ├── TopicIndexPage   Скрининг              └── ArticlePage ×2
    │   ├── ArticlePage      Организация лечения (steps ×4)
    │   ├── DirectoryPage    Куда обратиться      apps/directory (+ redirect /uz/qayerga-murojaat/)
    │   ├── ArticlePage      Государственная поддержка
    │   ├── ArticlePage      Уход и поддержка     (show_in_menus = False)
    │   └── ArticlePage      Жизнь после рака     (show_in_menus = False)
    └── SectionIndexPage children              /uz/bolalar/  /ru/detskiy/
        ├── TopicIndexPage   Об онкозаболеваниях у детей  └── ArticlePage ×4
        ├── TopicIndexPage   Диагностика и лечение        └── ArticlePage ×2
        ├── ArticlePage      Уход и поддержка
        ├── ArticlePage      Информация для семьи
        └── ArticlePage      Жизнь после рака
```

Every page exists in both locales, linked by `translation_key` (wagtail-localize). Slugs are
per language. `seed_content` (`apps/core/seed/`) creates/updates the whole tree idempotently.

## Models

| Model | App | Key fields | Notes |
|---|---|---|---|
| `BasePage` (abstract) | core | `og_image`, `noindex`, `last_reviewed_by`, `last_reviewed_at`, `medically_verified` | `get_section()`, `section_key`, `reading_time` (180 wpm), `verified_badge`, context adds `section`/`section_key` |
| `HomePage` | home | `hero_title`, `hero_subtitle`, `emergency_banner`, `stats` (≤3 stat), `body` (IntroBlock), `featured_articles` (≤6), `featured_videos` (≤3) | sections derived from children |
| `SectionIndexPage` | sections | `section_key` women/children, `tagline`, `colour_primary/accent` (hex, optional), `icon`, `intro` | `get_menu_items()` = live children in menus (5 per TZ) |
| `TopicIndexPage` | sections | `summary`, `intro` | `get_articles()` |
| `ArticlePage` | articles | `summary` (≤300), `hero_image`, `body` (ArticleBodyBlock) | `block_types` helper |
| `DirectoryPage` | directory | `intro`, `default_section` | GET filters `region`, `kind`, `section`, `free=1` |
| `Institution`, `Region` (14, migration), `Service` (8, migration) | directory | per spec §4.3 | snippet; CSV import + map in M4 |
| `Video` | media_library | `title`, `kind`, `source`, `file`, `external_url`, `poster`, `duration`, `doctor_name/org`, `transcript`, `subtitles_uz/ru`, `status`, `renditions` | `clean()` validates provider URL; transcoding M3 |
| `ToolsIndexPage`, `ScreeningToolPage` (result texts, where_page, disclaimer), `SelfCheckPage` (kind, items StreamField, result_* texts) | tools | waffle flags `tools_screening` / `tools_selfcheck`; logic in `screening.py` / `selfcheck.py` | POST + HTMX partials, nothing stored |
| `FAQPage`, `Question` (snippet) | faq | encrypted contact, status new/answered/published/rejected, consent_to_publish | purge 90 d after answer |
| `FeedbackPage`, `FeedbackSubmission` (snippet) | feedback | kind, encrypted contact, page_url, UA | purge 180 d |
| `GlossaryPage` | glossary | letters, section, `?q=` | `glossary_wrap` filter |
| `Term` | glossary | `term`, `definition`, `section`, `synonyms` | translatable snippet |
| `SiteSettings` | core | hotline ×2, socials ×5, footer/disclaimer/legal (uz+ru), emergency banner, partner logos ×3, Metrika id | `{{ settings.core.SiteSettings|localized:"field" }}` |

## Blocks (`apps/articles/blocks.py`)

`ArticleBodyBlock`: rich_text, callout, three_columns, two_columns, steps, cards_grid,
symptom_list, stat, video, image_gallery, document_download, faq_accordion, glossary_terms,
institution_list, cta, quote, table, embed. `IntroBlock` (index pages): rich_text, callout,
cards_grid, stat, cta, video.

Validation rules: `LinkBlock` page XOR url; `cta` needs a link; `video` needs snippet or URL of
a supported provider; `embed` accepts only YouTube / Telegram / Instagram / TikTok (parsed
offline in `apps/articles/embeds.py`, rendered as provider iframes — Instagram/TikTok behind a
click-to-load facade); `three_columns` exactly 3, `two_columns` exactly 2; `stat.year` 1990–2100.

## Navigation

`apps/core/navigation.py` builds `NavSection → NavItem → children` per locale, cached 1 h in
Redis (`nav:<lang>`), invalidated by `page_published` / `page_unpublished` / `post_page_move`
/ page delete (`apps/core/signals.py`).

## Template tags (`core_tags`)

`{% main_nav %}`, `{% breadcrumbs %}`, `{% lang_switch %}`, `{% hreflang_links %}`,
`{% canonical_url %}`, `{% section_style section %}`; filters `phone_display`, `phone_href`,
`localized`. `article_tags`: `link_href`, `resolve_step_links`.
