# Full production audit — «Erta aniqla» onco-awareness portal

## Your role

You are a world-class **senior full-stack engineer, DevOps/SRE, UI/UX designer, frontend developer, QA lead, accessibility (WCAG 2.1 AA) auditor, SEO specialist and web-security reviewer** — all in one person. You are auditing a live website in this browser. You are thorough, sceptical and concrete: you click everything, you try every state, you read the page source, network and console, and you never report a guess as a fact.

Your output goes to the project's engineer (Claude Code, which has the full source code). So every finding must be **reproducible and actionable**: exact URL, steps, what you expected, what happened, evidence, and a concrete fix.

## The site

- **URL:** https://ertaaniqla-production.up.railway.app/
- **What it is:** a public, bilingual information-and-education portal about **early detection of cancer** in Uzbekistan (NOT a diagnostic tool). Two sections with one shared navigation:
  - 🎗 **Women** — breast and cervical cancer: `/uz/ayollar/` · `/ru/zhenskiy/`
  - 🎀 **Children** — paediatric oncology: `/uz/bolalar/` · `/ru/detskiy/`
- **Audience:** women of all ages (often elderly, anxious, low-literacy), parents of sick children, bloggers/volunteers; mostly on **cheap Android phones over 3G**. Plus CMS editors and doctors.
- **Languages:** 3 versions — `/uz/` Uzbek Latin (default), `/oz/` Uzbek Cyrillic (automatic transliteration of `/uz/`), `/ru/` Russian. A language switcher must open the **same page** in the other language.
- **Stack (for your fix suggestions):** Django 5.2 + Wagtail 7 CMS, wagtail-localize, PostgreSQL, Redis, Celery, server-rendered templates + HTMX 2 + Alpine.js 3 (CSP build) + Tailwind 3. No SPA. Strict CSP with nonces.
- **Hosting now:** Railway is a **temporary demo host** (one web container, Celery runs eagerly, no nginx in front, no separate worker). The real production target is a VPS with nginx. Report Railway-specific problems separately.

## Known and accepted — do NOT report these as bugs

1. **Placeholder text** like `[[TODO: …]]`, `[[VERIFY: doctor]]`, `[[TODO: перевод с узбекского — копирайтер]]` is intentional — content comes later from doctors/copywriters. Russian women's pages are skeletons on purpose. (Do report placeholders that leak into places a user would find broken: `<title>`, meta description, OG tags, button labels, alt text, navigation labels, JSON-LD.)
2. **Colour contrast below AA in the default theme** is a client decision (pixel-perfect Figma). AA contrast is required **only in the high-contrast theme** of the accessibility toolbar — check that theme strictly.
3. **The children's section visuals** are intentionally simple (waiting for the designer's frames). Report functional/structural bugs there, not "it looks plain".
4. Pages without a designer's frame (directory, tools, FAQ, feedback, glossary, search, stories, materials, error pages) use the landing's primitives — judge consistency and usability, not "missing design".
5. Medical content accuracy is not yours to judge; but DO flag anything that reads like a diagnosis promise, frightening wording without a "see a doctor" next step, or a missing medical disclaimer on tool pages.
6. Institutions in the directory are fake sample rows.

## Previous audit (2026-09-27) — re-verify first

The first audit reported EA-01…EA-38. Fixes were deployed on 2026-09-28. Before the full pass,
re-check each of these and put a status table at the top of your report
(`ID | fixed / still broken / partly | evidence`):

- EA-01 absolute URLs (canonical, hreflang, og:image, JSON-LD, share links, sitemap `<loc>`) must use the public host, never `localhost`
- EA-02/EA-03 FAQ and feedback forms: valid submit → success; empty submit → error summary inside the form with focus on it; 6 quick submits → a translated "too many requests" message inside the form
- EA-04 `og:image` and "Story rasmi" URLs return 200
- EA-05 privacy policy linked from both consent checkboxes and the footer (uz / oz / ru)
- EA-07 the directory lists institutions (sample data) with map markers
- EA-08 no search result opens a 404
- EA-09 tabs on a cervical page stay on cervical pages; EA-10 every tab reachable at 360–1536 px, active tab in view
- EA-11 `/oz/` has no `ёʻ` and no `'` after a Cyrillic letter
- EA-12 no literal `<p>` in the children's diagnostics glossary
- EA-13 no duplicate `<title>` / description within a language
- EA-14 `X-Robots-Tag: noindex` and `Disallow: /` on this demo host
- EA-15 "Qayerga murojaat qilish" in the footer of both sections; EA-16 language switch keeps `?q=` on search
- EA-18 high-contrast theme: cards and controls have visible borders
- EA-22 no "TZ", "ТЗ (ru)" or "Figma" text on public pages
- EA-24 `/django-admin/` answers 404; EA-25 form pages are not served with `Cache-Control: public`
- EA-32 web manifest + theme-color; EA-34 404 page offers search and "where to go"; EA-35 print preview has the page title and no banner/tabs

Still open by decision (do not re-report): EA-06 Turnstile test key (client's Cloudflare keys pending), EA-15 hotline number, EA-17/EA-19/EA-26 (planned), EA-20 line-height and EA-21 hidden h1 (designer), EA-23 screening rules (doctor), EA-29 tools not published (doctor), EA-31/EA-36 brand/OG per script (designer).

## How to work

1. Start at `/` — check the redirect. Read `/robots.txt`, `/sitemap.xml` and the per-language sitemaps; use them as the **complete list of URLs** and visit **every one** of them (not a sample). Also follow every menu, footer link, tab, pill, card and CTA.
2. For every page check it **in all three languages** (at least the language switch and one full pass per language for key pages).
3. Test at **three widths**: 360–390 px (mobile), 768 px (tablet), 1280–1440 px (desktop). Use DevTools device mode. Where possible also emulate **Slow 3G / "Fast 3G"** and a mid-range CPU throttle.
4. Keep **DevTools Console and Network** open the whole time. Record every JS error, CSP violation, 404/500 request, mixed-content warning, failed font/image, redirect chain, and very large asset.
5. Interact with everything: menus (mouse, touch, keyboard, Esc, outside click), dropdowns, accordions, tabs, share buttons, copy-link, forms (valid, empty, invalid, very long text, emoji, HTML/script strings like `<script>alert(1)</script>` and `' OR 1=1 --` — only as normal form input, no automated attacks, no load testing), search (Latin, Cyrillic, typos, empty, very long query), directory filters and map, screening helper (edge ages: 17, 29, 30, 44, 45, 50, 65, 66, 120, negative, text), self-check checklists, accessibility toolbar (font ×1.25/×1.5, high contrast, reduce motion — then reload and check persistence), cookie/consent banner, print preview (Ctrl+P) on article, patient route, self-exam and tool pages.
6. Try **error paths**: a non-existent URL in each language, trailing slash / no slash, uppercase URL, `/uz/qidiruv/?q=` with odd characters, double-submit of a form, submitting a form 6+ times quickly (rate limit should kick in gracefully, with a translated message).
7. Do **not** try to log into the CMS with guessed passwords and do not attack the site. You may open `/cms/` and `/django-admin/` just to see what an anonymous visitor gets (should be a login page / not a debug page), and check that `/admin/` is not used.

## Audit checklist (cover every block)

### A. Functional & content integrity
- Every URL from the sitemaps returns 200; no 500s; no debug pages; 404/500 pages are translated and styled.
- Navigation: header top menu (Asosiy · Haqimizda · Bo'limlar ▾ · Shifokorlar · Savol-Javob), section tabs (women: Xabardorlik · Skrining · Davolashni tashkil etish · Qo'llab-quvvatlash · Kasallikdan keyingi hayot; children: 5 items), breadcrumbs, footer links, breast ↔ cervical pill switch. No dead links, no links to the wrong language, no redirect loops.
- Language switcher keeps the same page in uz / oz / ru; untranslated UI strings (e.g. English or Russian words on `/uz/`, Latin on `/oz/`); broken Cyrillic transliteration on `/oz/` (URLs, phone numbers, brand names, emails must NOT be transliterated).
- Forms (FAQ question, feedback): labels, required markers, consent checkbox with a privacy-policy link, inline errors, error summary, success message, no data loss on error, honeypot not visible, Turnstile/anti-spam behaviour, rate-limit page.
- Tools: screening helper logic by age matches what the page itself says; self-check gives a "see a doctor" result, never a diagnosis; disclaimer present; works without JS (disable JS once and retry the key flows).
- Search: results in both languages, highlighting, empty state, HTMX live results and plain-submit fallback.
- Directory: region/type filters, map loads (OSM tiles), list fallback, phone links `tel:`, no layout break with many results.
- Media: images load, correct aspect ratio, no blurry upscaled images on retina, video/embeds are click-to-load, downloads work.
- Share bar: Telegram, WhatsApp, Facebook, copy link, story image — correct URL, title and language.

### B. UI / UX & visual quality (think like a senior product designer)
- Visual hierarchy, spacing rhythm, alignment, consistent components between pages, typography scale, line length ≤ ~70ch, readable body size on mobile (≥ 16–18 px).
- Layout bugs: horizontal scroll, overflow, clipped text, overlapping elements, broken grids at in-between widths (e.g. 1024 px), sticky header covering anchors, CLS while loading, font swap flashes.
- Mobile: tap targets ≥ 44 px, thumb reach, menu usability, no hover-only interactions, forms usable with the on-screen keyboard.
- Emotional UX for anxious users: is the next step ("where to go / who to call") always obvious? Are frightening messages balanced with reassurance? Is the path from awareness → screening → where to go short and clear?
- Consistency between the women's and children's sections (same patterns, distinct colour identity).
- Empty, loading, error and success states for every interactive element.

### C. Accessibility (WCAG 2.1 AA)
- One `h1` per page, logical heading order, landmarks, skip link that actually moves focus.
- Full keyboard pass: Tab order, visible focus everywhere, menus/dropdowns/accordions/dialogs operable and closable with Esc, no keyboard traps, focus returns correctly.
- Screen-reader semantics: `alt` texts (not placeholders, not file names), decorative images hidden, buttons vs links, `aria-expanded`, form labels, `aria-describedby` for errors, `lang` attribute correct per language (`uz`, `uz-Cyrl`, `ru`), language of inline foreign text.
- High-contrast theme: every text and control ≥ 4.5:1 (large text 3:1), focus visible, nothing disappears.
- Colour is never the only carrier of meaning (e.g. urgency levels).
- `prefers-reduced-motion` and the toolbar's reduce-motion are honoured; 200 % browser zoom and 320 px width without loss of content.
- If available, run Lighthouse and/or axe DevTools on the key pages and include the numbers.

### D. Performance (3G, cheap Android)
- Lighthouse mobile on: home, a women's article, directory, a tool page. Report LCP, CLS, TBT/INP, total transfer size, number of requests. Budgets: LCP < 2.5 s, CLS < 0.1, TBT < 200 ms, HTML ≤ 60 KB gz, CSS ≤ 40 KB gz, JS ≤ 50 KB gz.
- Check compression (`content-encoding` gzip/br) on HTML/CSS/JS, `cache-control` on static assets (long, immutable, hashed filenames) and HTML, image formats (WebP/AVIF), `srcset`/`sizes`, `loading="lazy"` below the fold, explicit width/height, font preload and `font-display`, render-blocking resources, unused CSS/JS, oversized images.
- TTFB of cached vs first request (reload twice).

### E. SEO & social
- `<title>` and meta description unique per page and per language; canonical URL correct (watch out: canonical must point to the current host or the intended final domain — report which one it uses); `hreflang` for uz / uz-Cyrl / ru + `x-default`; `html lang`.
- JSON-LD valid (Organization, BreadcrumbList, MedicalWebPage/Article, FAQPage, MedicalClinic, VideoObject) — check with the Rich Results test or schema.org validator if possible.
- OpenGraph / Twitter tags: title, description, image (absolute URL, loads, 1200×630), locale.
- robots.txt, sitemaps (absolute URLs on the right host, all languages, no noindex pages), `noindex` on the Railway demo? (a demo host should probably NOT be indexed — report what you see).
- Favicon, web manifest, theme colour.

### F. Security & privacy (passive checks only)
- Response headers on HTML: `Content-Security-Policy` (nonce-based, no `unsafe-inline` for scripts, `frame-ancestors`), `Strict-Transport-Security`, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`, `X-Frame-Options`, `Cross-Origin-*`. Note which ones are missing on Railway (there is no nginx there) versus which the app itself must send.
- Cookies: `Secure`, `HttpOnly`, `SameSite`; no session cookie for anonymous visitors unless needed; CSRF cookie flags.
- HTTP → HTTPS redirect, no mixed content, no server/version banners, no stack traces, no `DEBUG` pages, no exposed `/.env`, `/.git/`, `/static/` directory listings, source maps with secrets, `/metrics` publicly readable.
- Forms: user input is escaped when echoed back (no XSS), error messages don't leak internals, personal data fields are optional and minimal, privacy policy is linked and exists in all languages.
- Analytics: Yandex.Metrika must load **only after** the consent banner is accepted; no Google Analytics/GTM; no third-party trackers before consent (check Network with a fresh profile).
- CMS login page: no user enumeration in error messages, 2FA mentioned after login is fine; lockout message translated.

### G. DevOps / reliability (from the outside)
- `/healthz/` and `/readyz/` respond (readyz should report db + cache); response times; any cold-start slowness.
- Railway specifics: the public domain vs the future canonical domain `ertaaniqla.uz`; uploaded media persistence (a redeploy on Railway can wipe local files — check whether images come from a volume/object storage or would disappear); Celery-eager side-effects (does submitting a form hang or take long because e-mail is sent synchronously?); OG/story images present.
- Redirects: `/` → `/uz/` (and `Accept-Language` behaviour), `http://` → `https://`, trailing slashes, old short URLs like `/uz/qayerga-murojaat/`.
- Error budget: note any intermittent 502/503/timeouts during the audit with timestamps.

## Output format (strict)

Write the whole report in **English**, as a single Markdown document, so it can be pasted directly to the engineer.

### 1. Executive summary
- Overall verdict (ready for a public demo? ready for launch?), top 10 issues in one line each, scores per area (Functional, UI/UX, A11y, Performance, SEO, Security, DevOps) from 0–10 with one-sentence justification, and the Lighthouse numbers you measured.

### 2. Findings
One block per finding, sorted **P0 → P3**:

```
### [ID] <short title>
- Severity: P0 (broken / security / data loss) | P1 (major UX, a11y blocker, wrong language, SEO blocker) | P2 (noticeable issue) | P3 (polish)
- Area: Functional | UI/UX | A11y | Performance | SEO | Security | DevOps | i18n | Content-structure
- Where: exact URL(s), language(s), viewport(s), browser
- Steps to reproduce: 1. … 2. … 3. …
- Expected: …
- Actual: …
- Evidence: console/network message, response header, HTML snippet, measured number, screenshot description
- Likely cause: your best technical hypothesis (template, CSS rule, header, setting, JS) — mark as "hypothesis" if not certain
- Fix: concrete instructions for the engineer (what to change and how to verify it), e.g. "In the header template, add aria-expanded to the Bo'limlar button and toggle it in nav.js; verify with keyboard + axe"
- Acceptance check: how we will know it is fixed
```

Group duplicates: if one bug appears on many pages, report it once and list all URLs.

### 3. Page-by-page coverage table
| URL | uz | oz | ru | mobile | desktop | issues (IDs) |
Every sitemap URL must appear, so we can see nothing was skipped.

### 4. Ready-to-paste task for Claude Code
Finish with a section titled **"PROMPT FOR CLAUDE CODE"** — a self-contained instruction the engineer will paste to Claude Code (which has the repo, runs `make check`, writes tests, uses Conventional Commits and must keep uz + ru translations complete). It must:
- list the fixes as an ordered backlog (P0 first), each with its finding ID, the acceptance check, and a note on which test should prove it (unit / view / Playwright e2e / axe / Lighthouse);
- group them into small, separately committable batches;
- separate "Railway demo only" issues from "real production" issues;
- say explicitly which findings need a **client / designer / doctor decision** instead of code (do not ask the engineer to invent medical text or design).

Be exhaustive. It is better to report 80 precise findings than 15 vague ones. Do not stop after the first pages — the coverage table must be complete.
