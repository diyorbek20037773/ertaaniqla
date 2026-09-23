# COMPONENT INVENTORY / ИНВЕНТАРЬ КОМПОНЕНТОВ / KOMPONENTLAR RO'YXATI

> Hand-off document for the designer (DECISIONS D-003). The site is built at **wireframe**
> level: every visual decision lives in `static/src/tokens.css` (tokens) and
> `static/src/components.css` + `templates/components/*.html` / `templates/blocks/*.html`
> (structure). Applying the Figma design = changing those files only — **no Python changes**.
>
> Документ для дизайнера. Сайт собран на уровне **вайрфрейма**: все визуальные решения
> находятся в `static/src/tokens.css` (токены) и `static/src/components.css` +
> `templates/components/*.html` / `templates/blocks/*.html` (структура). Внедрение дизайна
> из Figma = правка только этих файлов, **без изменения Python**.
>
> Dizayner uchun hujjat. Sayt **wireframe** darajasida yig'ilgan: barcha vizual qarorlar
> `static/src/tokens.css` (tokenlar) va `static/src/components.css` +
> `templates/components/*.html` / `templates/blocks/*.html` (tuzilma) fayllarida. Figma
> dizaynini qo'llash = faqat shu fayllarni o'zgartirish, **Python o'zgarmaydi**.

Last updated: 2026-09-23 (M5b — design applied). Screenshots at 390 px: `tests/e2e/screenshots/`.

> **M5b status:** the designer's Figma (`y76CeUEqpXAuCtaJxB5LUk`) is mapped into the tokens
> below — see `docs/ADR/0006-design-system-figma.md`. Still open: the children's section
> visuals (client is redesigning the pattern and illustrations → **M5c**) and every page the
> Figma file does not cover (forms, search, directory, glossary, stories, error pages), which
> follow the same token language.
>
> **Дизайн M5b:** Figma перенесена в токены (ADR-0006). Открыто: визуал детского раздела (M5c)
> и страницы, которых нет в Figma. / **M5b:** Figma tokenlarga ko'chirildi (ADR-0006). Ochiq:
> bolalar bo'limi vizuali (M5c) va Figma'da yo'q sahifalar.

## 1. Design tokens / Токены / Tokenlar — `static/src/tokens.css`

| Token | Purpose (ru) | Maqsad (uz) | Wireframe default |
|---|---|---|---|
| `--neutral-0…900` | Серая шкала (фон, текст, границы) | Kulrang shkala (fon, matn, chegaralar) | #fff → #111 |
| `--info/--warning/--danger/--success` + `*-bg` | Семантические цвета (уведомления, срочность симптомов) | Semantik ranglar (ogohlantirish, belgilar shoshilinchligi) | blue / amber / red / green |
| `--brand-w`, `--brand-w-soft` | Идентичность раздела «Женский рак» 🎗 | «Ayollar saratoni» bo'limi identikasi 🎗 | rose #b8336a |
| `--brand-c`, `--brand-c-soft` | Идентичность раздела «Детский рак» 🎀 | «Bolalar saratoni» bo'limi identikasi 🎀 | amber #8a5a00 |
| `--brand`, `--brand-soft`, `--brand-contrast` | Активный цвет раздела; переключается `body[data-section]` | Faol bo'lim rangi; `body[data-section]` orqali almashadi | neutral outside sections |
| `--font-sans`, `--text-base` (18px), `--leading`, `--measure` (70ch) | Типографика | Tipografika | Albert Sans + Manrope (Cyrillic) |
| `--fs-hero/-sub/-h1/-h2/-h3/-body/-lead/-ui` | Флюидная шкала `clamp()` 390px → 1728px | 390px → 1728px oralig'idagi `clamp()` shkala | 36→96px … 16→20px |
| `--c-pink-200…900`, `--c-purple-300…900`, `--c-lime` | Палитра Figma (сырые цвета) | Figma paletasi (xom ranglar) | #ff477e … #b2f71b |
| `--grad-hero/-title/-cta` (+ `-w` / `-c`) | Градиенты заголовков и кнопок | Sarlavha va tugma gradientlari | pink / purple |
| `--glass-bg/-border/-blur`, `--stage-*` | Стеклянные поверхности и карточки стадий | Shisha yuzalar va bosqich kartalari | white 36 %, blur 12.25px |
| `--space-1…20`, `--section-gap`, `--radius`, `--radius-glass/-capsule/-stage/-pill`, `--tap-target` (44px), `--container` (1484px), `--gutter` | Отступы, радиусы, размер касания | Bo'shliqlar, radius, bosish maydoni | 4px grid |
| `--font-scale`, `html[data-contrast="high"]` | Панель доступности (шрифт ×1.25/×1.5, контраст) | Maxsus imkoniyatlar paneli (shrift, kontrast) | — |

Editors may override `--brand`/`--brand-soft` per section from the CMS (`SectionIndexPage.colour_primary/accent`); emitted as a nonce'd `<style>`.

## 2. Page templates / Шаблоны страниц / Sahifa shablonlari

| Template | Page type | Regions (ru) | Hududlar (uz) | States |
|---|---|---|---|---|
| `base.html` | all | `<head>` (canonical, hreflang, OG), skip-link, header, banner, breadcrumbs, `<main>`, footer | Umumiy karkas | `data-section` = `women` / `children` / `""` |
| `home/home_page.html` | HomePage | hero (title, subtitle, home banner), 2 карточки разделов, полоса статистики (3), избранные статьи (≤6), избранные видео (≤3), доп. блоки | Hero, 2 bo'lim kartasi, statistika (3), tanlangan maqolalar/videolar | with/without featured, banner on/off |
| `sections/section_index_page.html` | SectionIndexPage | заголовок с эмодзи, tagline, intro-блоки, сетка карточек подразделов (h2) | Bo'lim sarlavhasi, tagline, intro, bo'limchalar kartalari | 5–7 cards |
| `sections/topic_index_page.html` | TopicIndexPage | заголовок, summary, intro, сетка карточек статей (картинка, заголовок, summary, время чтения) | Mavzu sarlavhasi, maqola kartalari | empty state («Articles will appear here») |
| `articles/article_page.html` | ArticlePage | заголовок, summary, page-meta (время чтения, бейдж «Проверено врачом»), hero image, блоки body, дисклеймер | Maqola sahifasi | with/without hero image, verified badge |
| `directory/directory_page.html` + `_results.html` | DirectoryPage | заголовок, intro, форма фильтров (регион, тип, раздел, бесплатно; HTMX), карта Leaflet (`#map`, маркеры по цвету раздела, попап), счётчик, карточки учреждений | Muassasalar katalogi | empty results; no coordinates; loading indicator |
| `tools/tools_index_page.html` | ToolsIndexPage | заголовок, intro, карточки инструментов, дисклеймер | Asboblar sahifasi | flag-off (tool hidden) |
| `tools/screening_tool_page.html` + `_screening_result.html` | ScreeningToolPage | форма (возраст + 3 селекта «когда в последний раз»), результат по тестам (статус: пора / через N лет / не показано), текст из CMS, кнопка «Куда обратиться», дисклеймер | Skrining yordamchisi | before submit / due / ok / not applicable / errors |
| `tools/self_check_page.html` + `_self_check_result.html` | SelfCheckPage | чек-лист (fieldset), живой счётчик (Alpine), результат уровня none/routine/soon/urgent + текст из CMS, кнопка «Куда обратиться» | O'z-o'zini tekshirish | 4 levels; nothing ticked |
| `faq/faq_page.html` + `_form.html` | FAQPage | форма вопроса (имя, контакт, раздел, текст, согласия, honeypot, Turnstile), благодарность, вкладки-фильтр, список Q&A (`<details>`, автор/организация/дата) | Savol-javob sahifasi | success / errors / 429; empty list |
| `feedback/feedback_page.html` + `_form.html` | FeedbackPage | форма (тип, текст, контакт, скрытый page_url, согласие), благодарность | Qayta aloqa | success / errors / 429 |
| `glossary/glossary_page.html` | GlossaryPage | поиск + фильтр раздела, навигация по буквам, группы `<dl>` с якорями `#term-<id>` | Lug'at sahifasi | no terms found |
| `search/search.html` + `search/_results.html` | search view (`/uz/qidiruv/?q=`, `/ru/poisk/?q=`) | заголовок, форма поиска, счётчик, список результатов (заголовок, summary, метка языка, цвет раздела), пустое состояние, подсказка | Qidiruv sahifasi | no query / results / empty; HTMX partial = `_results.html` |
| `stories/story_index_page.html` | StoryIndexPage (`/uz/hikoyalar/`) | заголовок, intro, вкладки-фильтр (все / женский / детский), сетка карточек историй (фото, имя, summary) | Hikoyalar sahifasi | empty state; filter active |
| `stories/patient_story_page.html` | PatientStoryPage | eyebrow «История пациента», имя (псевдоним) + диагноз, summary, page-meta, фото, блоки, подпись о согласии/анонимизации | Bemor hikoyasi | anonymised on/off; section colour |
| `media_library/materials_page.html` | MaterialsPage (`/uz/materiallar/`) | заголовок, intro, вкладки аудитории (все / блогеры / близкие / родители / клиники), карточки материалов: картинка + «Скачать», документ, короткое видео + «Скачать видео», готовая подпись + «Копировать», хэштеги + «Копировать» | Bloger-kit sahifasi | empty state; filter active; item without image/video |
| `404.html`, `429.html`, `500.html`, `core/lockout.html` | errors | текст + ссылка на главную | Xato sahifalari | — |

## 3. Components / Компоненты / Komponentlar — `templates/components/`

Each partial documents its context variables in a header comment. CSS block of the same name in `components.css`.

| Component | Purpose (ru) | Maqsad (uz) | Context / fields | States |
|---|---|---|---|---|
| `header.html` | Шапка: логотип-заглушка, название, горячая линия (tel:), навигация | Sarlavha: logo, nom, ishonch telefoni, navigatsiya | `settings.core.SiteSettings.hotline_phone` | mobile (menu behind toggle) / desktop (inline) |
| `nav.html` (`{% main_nav %}`) | Мега-меню: 2 раздела × 5 пунктов ТЗ + подпункты; переключатель языка | Mega-menyu: 2 bo'lim × 5 band + ichki bandlar; til almashtirgich | `sections[NavSection{key,title,url,tagline,emoji,items[NavItem{title,url,summary,children}]}]`, `section_key` | mobile `<details>` (no JS), desktop hover panel, active section underline |
| `lang_switch.html` (`{% lang_switch %}`) | Переключатель Oʻzbekcha (латиница) / Ўзбекча (кириллица, `/oz/`) / Русский на ту же страницу | Joriy sahifaning lotin / kirill / rus versiyasiga o'tish | `links[{code,name,url,keep,is_current}]`; названия с `translate="no"` | current = plain text with `aria-current` |
| `banner.html` | Экстренный баннер сайта (месяц скрининга) | Sayt bo'ylab shoshilinch banner | `SiteSettings.emergency_banner_*` | hidden / text / link |
| `breadcrumbs.html` (`{% breadcrumbs %}`) | Хлебные крошки от главной | Yo'l ko'rsatkichi | `crumbs[Page]` | hidden on home; last item `aria-current` |
| `page_meta.html` | Время чтения + бейдж «Проверено врачом: имя, организация (дата)» | O'qish vaqti + «Shifokor tekshirgan» belgisi | `page.reading_time`, `page.verified_badge` | badge on/off |
| `card.html` | Универсальная карточка (статья, тема, элемент сетки) | Universal karta | `title,url,text,image,icon,meta,tag` | with image / with icon / no link |
| `callout.html` | Выделенный блок; kind = info, warning, danger, success, **reassurance** («этот признак не всегда рак») | Ajratilgan blok | `kind,title,text` | 5 kinds; icon + sr-only label (not colour only) |
| `steps.html` | Нумерованные шаги: маршрут пациента (4), самообследование | Raqamlangan qadamlar | `title, steps[{number,title,text,deadline,href}]` | auto numbers 01…; deadline line (ПП-402); print-friendly |
| `symptom_list.html` | Симптомы с срочностью routine / soon / urgent | Belgilar ro'yxati (shoshilinchlik bilan) | `title, symptoms[{symptom,urgency,explanation}]` | 3 urgency levels: colour + icon + text |
| `stat.html` | Одна цифра статистики | Bitta statistik ko'rsatkich | `value,label,source,year` | with/without source |
| `video.html` | Плеер (HTML5 + VTT uz/ru + постер) или провайдер-embed; спикер; подпись; транскрипт (`<details>`) | Video pleer / embed, transkript | `video, embed, caption, transcript` | upload ready / processing / external; vertical 9:16 |
| `embed_frame.html` | iframe YouTube/Telegram; **click-to-load** фасад для Instagram/TikTok; `<noscript>` ссылка | Provayder iframe / bosib yuklash fasadi | `embed{provider,src,vertical,click_to_load}` | facade / loaded / no-JS |
| `institution_card.html` | Карточка учреждения: название, тип, «бесплатно по госпрограмме», адрес, телефон, часы, услуги, сайт, дата проверки | Muassasa kartasi | `institution` | free badge on/off; no phone/hours |
| `filter-tabs` (CSS in stories) | Вкладки фильтра раздела (aria-current) | Bo'lim filtr tugmalari | links | active / inactive |
| `form_field.html` / `form_errors.html` | Поле формы (label, help, inline error, aria-describedby) / сводка ошибок (role=alert, ссылки на поля) | Forma maydoni / xatolar ro'yxati | `field` / `form` | error / checkbox |
| `turnstile.html` | Виджет Cloudflare Turnstile (только при ключе) | Turnstile vidjeti | `TURNSTILE_SITE_KEY` | present / absent |
| `disclaimer.html` | Медицинский дисклеймер на страницах инструментов | Tibbiy ogohlantirish | `text` (fallback: site setting) | custom / default |
| `search_form.html` | Поле поиска (GET-форма; на странице поиска — HTMX «поиск при вводе») | Qidiruv maydoni | `query, autofocus, results_target` | plain / HTMX live |
| `footer.html` | Подвал: дисклеймер (обязателен), горячая линия, соцсети, текст, ПП-402/186, логотипы партнёров (Агентство, Яндекс, Hamroh), ссылки на страницы сайта | Pastki qism | `SiteSettings`, `{% site_links %}` | logos present / placeholders |
| `share.html` (`{% share_bar %}`) | Панель «Поделиться»: Telegram (первый), WhatsApp, Facebook, «Копировать ссылку» (подтверждение), «Картинка для сторис (Instagram/TikTok)» 1080×1920 | «Ulashish» paneli: Telegram birinchi, nusxalash, storis rasmi | `links[{key,label,href,download}]`, `url`, `title`, `story_url` | copied / not copied; no-JS (read-only input); no story image |
| `a11y_toolbar.html` | Панель доступности: A / A+ / A++ (×1.25 / ×1.5), высокий контраст, меньше движения; состояние в `localStorage` | Maxsus imkoniyatlar paneli | — (`static/src/a11y.js`, `html[data-font-scale|data-contrast|data-reduce-motion]`) | each button `aria-pressed` on/off |
| `consent_banner.html` | Баннер согласия на Яндекс.Метрику (появляется только при заданном id; ссылка на политику конфиденциальности) | Metrika uchun rozilik banneri | `metrika_id`, `privacy_url` | hidden (no id / decided) / visible; agree / decline |
| Wagtail `{% picture %}` (in `card.html`, hero) | Адаптивное изображение: WebP + JPEG, `srcset` 400/800, `sizes`, `loading="lazy"`, width/height | Moslashuvchan rasm | image, formats, sizes | — |

## 4. Content blocks / Блоки контента / Kontent bloklari — `templates/blocks/`

Blocks are the editor's building kit (`apps/articles/blocks.py`). Each maps to a component above or has its own structure.

| Block | Fields | Renders via | Used on (TZ) |
|---|---|---|---|
| `rich_text` | HTML (h2,h3,b,i,ol,ul,link,doc,image,embed) | `.prose` | everywhere |
| `callout` | kind, title, text | `components/callout.html` | «Не откладывайте визит», placeholders |
| `three_columns` | 3 × (title, items list) | `.columns--3` | Уход и поддержка, Жизнь после рака |
| `two_columns` | 2 × (title, items list) | `.columns--2` | Информация для семьи |
| `steps` | title, steps[number,title,text,deadline,link] | `components/steps.html` | Маршрут пациента (4 шага), самообследование |
| `cards_grid` | title, cards[image/icon,title,text,link] | `components/card.html` | 6 видов детского рака, факторы риска, онкокоманда |
| `symptom_list` | title, symptoms[symptom,urgency,explanation] | `components/symptom_list.html` | Симптомы |
| `stat` | value,label,source,year | `components/stat.html` | Статистика по Узбекистану, home strip |
| `video` | video snippet / external URL, caption, transcript | `components/video.html` | видео врачей, мобилограф |
| `image_gallery` | title, images[image+alt, caption], downloadable | `.gallery` | инфографика |
| `document_download` | document, description | `.document` | печатные материалы |
| `faq_accordion` | title, items[question, answer] | `.faq` (`<details>`) | «Вопросы врачу» |
| `glossary_terms` | title, terms[] | `.glossary-terms` (`<dl>`) | «Словарь для родителей» |
| `institution_list` | title, region, kind, free_only, limit | `components/institution_card.html` | «Где пройти» |
| `cta` | text, button_label, link, style | `.cta` + `.button` | переходы между страницами |
| `quote` | text, author, role | `.quote` | цитаты пациентов/врачей |
| `table` | caption, typed columns, rows | `.table` | таблица скрининга |
| `embed` | url, caption | `components/embed_frame.html` | посты Telegram/Instagram/TikTok/YouTube |

## 5. Global states the design must cover / Состояния / Holatlar

- Mobile 390 px first; desktop ≥ 1024 px (`64rem`) shows the mega-menu inline.
- No JS: menu and accordions work through `<details>`; embeds show a link.
- Accessibility toolbar (`a11y_toolbar.html`): font ×1.25 / ×1.5 (`html[data-font-scale]`), high contrast (`html[data-contrast="high"]` — neutral palette inverted, brand colours kept), reduced motion (`html[data-reduce-motion]`). The design must work in all three.
- Print (`static/src/print.css`, tested in `tests/e2e/test_print.py`): article, patient route, self-exam steps, symptom list, question checklists, tool results, glossary — chrome hidden, accordions expanded, `ertaaniqla.uz` footer note.
- Consent banner (`consent_banner.html`) is fixed at the bottom on first visit; JSON-LD, OG/Twitter tags and share bar are on every page (`base.html`).
- Placeholders `[[TODO: content — copywriter]]` / `[[VERIFY: doctor]]` appear in content until the copywriter replaces them — style `.placeholder` only.

## 6. What the designer must deliver / Что нужно от дизайнера / Dizaynerdan kerak

1. Colour values for `--brand-w*`, `--brand-c*`, neutrals and semantic colours (WCAG AA ≥ 4.5:1 on text).
2. One font family (2 weights, Latin + Cyrillic + U+02BB/U+02BC), WOFF2.
3. Icons: section symbols 🎗/🎀 as SVG, urgency icons (routine/soon/urgent), callout icons, card icons (`data-icon` names above).
4. Mockups for each template in §2 at 390 px and 1280 px, including empty/error states.
5. Logo and partner logos (Agency, Yandex, Hamroh).
