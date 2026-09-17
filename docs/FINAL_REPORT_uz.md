# «Erta aniqla» — yakuniy hisobot (autopilot, M0 → M7b)

Sana: 2026-09-17 · Oxirgi teg: `m7b` (`m7-release-candidate` dan keyin) · Filial: `master`

## 1. Nima qurildi

| Milestone | Teg | Asosiy natija | Fayllar |
|---|---|---|---|
| M0 — Skelet | `m0` | Django 5.2 LTS + Wagtail 7.0 LTS (D-001), sozlamalar base/dev/test/prod, Docker (multi-stage), Makefile, CI, PII shifrlash maydoni, healthz/readyz, JSON loglar | `config/`, `docker/`, `Makefile`, `apps/core/fields.py` |
| M1 — Kontent modeli + i18n | `m1` | Barcha sahifa turlari, 18 ta StreamField blok, uz/ru daraxti (wagtail-localize), `seed_content` TZ ning toʻliq tuzilmasi bilan, menyu, breadcrumbs, footer | `apps/*/models.py`, `apps/articles/blocks.py`, `apps/core/seed/` |
| M2 — Komponentlar, qidiruv | `m2` | Bloklar render, bosh sahifa, Postgres FTS (uz/ru sinonimlar, lotin↔kirill), HTMX qidiruv, axe testlari | `apps/search/`, `templates/blocks/` |
| M3 — Media va hikoyalar | `m3` | ffmpeg transkodlash (720p/480p + poster), OG rasm, EXIF tozalash, maxfiy hujjatlar, bemor hikoyalari rozilik bilan | `apps/media_library/services.py`, `apps/stories/` |
| M4 — Maʼlumotnoma, vositalar, FAQ | `m4` | Muassasalar (CSV import, Leaflet xarita, HTMX filtr), skrining/oʻz-oʻzini tekshirish vositalari, savol-javob, qayta aloqa, lugʻat, PII tozalash joblari | `apps/directory/`, `apps/tools/`, `apps/faq/`, `apps/feedback/`, `apps/glossary/` |
| M5 — SEO, a11y, tezlik | `m5` | JSON-LD, sitemaplar, ulashish paneli, bloggerlar uchun materiallar, Metrika (rozilik bilan), qulaylik paneli, print CSS, sahifa keshi, Lighthouse/pa11y CI | `apps/core/seo.py`, `apps/core/cache.py` |
| M6 — Prod DevOps | `m6` | nginx (TLS, rate limit, micro-cache), certbot, backup + restic + haftalik restore testi, monitoring (Prometheus/Grafana/Telegram), staging, CD + rollback, RUNBOOK, SECURITY | `compose.prod.yml`, `docker/nginx/`, `docs/RUNBOOK.md` |
| M7 — Muharrirlar, workflow, launch | `m7-release-candidate` | Rollar Editor / Medical Reviewer / Admin, «Medical review» workflow va «Shifokor tekshirgan» belgisi, 2FA, muharrir qoʻllanmalari (ru+uz), launch checklist, yuklama testi | `apps/users/`, `docs/EDITOR_GUIDE_*.md`, `docs/LAUNCH_CHECKLIST.md`, `tests/perf/locustfile.py` |
| M7b — Oʻzbek kirill | `m7b` | Buyurtmachi talabi: saytning kirill versiyasi `/oz/` (lotin daraxtidan avtomatik), 3 tilli almashtirgich, hreflang `uz-Cyrl` | `apps/core/uzcyrl.py`, `apps/core/middleware.py` |

M7 da topilib tuzatilgan ikki jiddiy xato:
- **2FA umuman ishlamas edi**: django-otp 1.7 + wagtail-2fa 1.8 birga «Please select a device.» xatosini berardi — hech kim CMS ga kira olmasdi. Tuzatildi (`apps/users/otp.py`, D-042), testlar bilan.
- **Rasm/hujjat tanlash** oddiy foydalanuvchilarda ishlamas edi (`choose_*` ruxsati yoʻq edi). Migratsiya bilan tuzatildi.

## 2. TZ_TRACE xulosasi

Jami **81** talab: **79 done**, **2 not done**.

| ID | Talab | Nima uchun bajarilmagan |
|---|---|---|
| E-11 | Yakuniy vizual dizayn | Figma dizayn hali kelmagan (D-003). Hozir toza wireframe; dizayn faqat `tokens.css` va `templates/components/` ga tushadi (M5b), Python oʻzgarmaydi. |
| M7-08 | Kopirayter/dizayner bilan UAT | Odamlar kerak. Vositalar tayyor: `create_demo_staff`, e2e ssenariy, LAUNCH_CHECKLIST §6. |

Qoʻshimcha: barcha tibbiy matnlar `[[TODO: content — copywriter]]` / `[[VERIFY: doctor]]` toʻldiruvchilari bilan (qoida boʻyicha tibbiy matn yozilmagan). Nashrdan oldin `manage.py find_placeholders --fail` tekshiradi.

## 3. Qabul qilingan qarorlar (`docs/DECISIONS.md`, D-001…D-049)

Buyurtmachi tasdiqlashi **kerak** boʻlganlari:

| ID | Qaror | Nima kerak |
|---|---|---|
| D-044 | VPS Oʻzbekistonda boʻlishi shart emas (sizning javobingiz) | **Yurist tasdigʻi**: ZRU-547 (shaxsiy maʼlumotlarni lokalizatsiya) boʻyicha. Sayt kam PII saqlaydi (ixtiyoriy kontakt, shifrlangan, 90/180 kunda oʻchadi), lekin qonun talabi yuridik jihatdan hal qilinishi kerak. |
| D-049 | Kirill versiyasi lotin matnidan avtomatik (`/oz/`) | Sifatni koʻrib chiqing: `/oz/` sahifalarni oching. Alohida qoʻlda yozilgan kirill daraxti kerak boʻlsa — keyin qoʻshish mumkin, lekin muharrir va shifokor ishi 1,5 barobar oshadi. |
| D-041 | Belgi faqat «Medical review» workflow orqali qoʻyiladi, har bir til alohida tekshiriladi | Shifokorlar ish tartibi shunga rozi ekanini tasdiqlang. |
| D-003 | Dizayn kelguncha wireframe | Figma muddati. |
| D-001 | Django 5.2 / Wagtail 7.0 (TZ dagi 5.1/6 EOL) | Maʼlumot uchun. |

Sizning javoblaringiz asosida: D-045 (DMED — kiritilmaydi), D-046 (muassasalar roʻyxati Vazirlikdan CSV), D-047 (lotin + kirill), D-048 (video: oʻz serverimiz + YouTube — ikkalasi ham ishlaydi).

## 4. Ishga tushirish uchun sizdan kerak boʻlganlar

1. **Domen**: `ertaaniqla.uz` (va `oncoportal.uz` — alias yoki yoʻq), DNS boshqaruvi.
2. **VPS**: 8 vCPU / 16 GB / 1 TB NVMe, SSH kirish; toʻlov shartnomaga (sizning javobingiz). Joylashuvi boʻyicha yurist xulosasi (D-044).
3. **`.env` qiymatlari**: `DJANGO_SECRET_KEY`, `PII_ENCRYPTION_KEYS`, DB/Redis parollari, `DOMAIN`, `LETSENCRYPT_EMAIL`, restic ombori (backup uchun S3/SFTP), Telegram bot (alertlar) — roʻyxat `.env.example` da.
4. **Kalitlar/hisoblar**: Sentry DSN, Yandex.Metrika ID (kimning hisobida), Cloudflare Turnstile kalitlari, Yandex.Webmaster / Google Search Console.
5. **Muassasalar CSV** (Sogʻliqni saqlash vazirligidan) — format `docs/EDITOR_GUIDE_uz.md` §9 va `data/institutions.sample.csv`.
6. **Logotip, ranglar, Figma dizayn** (M5b).
7. **Tibbiy matnlar** (kopirayter + RONM / Ona va bola markazi / bolalar onkogematologiyasi shifokorlari), maxfiylik siyosati, bemor rozilik shakli (yuridik matn, vasiy varianti bilan), tibbiy ogohlantirish yakuniy matni, PQ-402 sanasi.
8. **Odamlar**: har bir muharrir va shifokor uchun hisob (rol + tashkilot), UAT sessiyasi.

Toʻliq roʻyxat: `docs/LAUNCH_CHECKLIST.md`.

## 5. Test natijalari (haqiqiy chiqish, 2026-09-17)

| Tekshiruv | Natija |
|---|---|
| `ruff check` / `ruff format --check` | All checks passed |
| `mypy` | Success: no issues found in 122 source files |
| `pytest --cov` | **432 passed**, 1 skipped (hostda ffmpeg yoʻq; konteynerda M3 da oʻtgan), coverage **92 %** (chegara 85 %) |
| Tarjimalar | uz + ru complete |
| E2E (Playwright, dev server) | **41 passed**: ekran rasmlari (390 px), menyu, til almashtirish (uz↔ru, lotin↔kirill), print, CSP, axe (13 sahifa, 0 jiddiy), CMS: muharrir ru maqola → uz tarjima → shifokor tasdiqlaydi → ikkala tilda nashr + belgi, 2FA orqali |
| Yuklama (locust, 200 foydalanuvchi, 5 daqiqa) | 28 736 soʻrov, **0 xato**, 96.8 req/s; sahifa p50 12 ms · **p95 32 ms** · p99 75 ms (budjet p95 < 300 ms). ⚠️ Prod sozlamali image, lekin dev noutbukda (Docker Desktop), VPS da emas — staging da qayta oʻtkazish LAUNCH_CHECKLIST §6 da. |
| Lighthouse (M5, lokal) | perf 0.98–0.99, a11y 1.00, LCP 2.0–2.1 s, CLS 0, TBT 48–130 ms |
| pa11y-ci (M5) | 8/8 URL WCAG 2.1 AA; M7b da `/oz/` URL qoʻshildi (CI da ishlaydi) |
| Hajm budjeti | CSS 2.6 KB gz, JS 37.7 KB gz (budjet 40/50) |
| `check --deploy` (prod) | yashil (M6) |
| `nginx -t` | successful (M7b oʻzgarishidan keyin qayta tekshirildi) |
| Backup → restore (M6) | scratch postgres:16 ga tiklandi: 71 sahifa, 12 muassasa, 6 atama |

## 6. Maʼlum kamchiliklar va `docs/TODO_HARDENING.md` (H-001…H-023)

- **Dizayn yoʻq** (wireframe) — M5b, Figma kutilmoqda.
- **Kirill transliteratsiyasi** qoidalarga asoslangan: «ь», «ц» li oʻzlashma soʻzlar istisnolar lugʻatida (kodda). Filolog koʻrib chiqishi va CMS orqali boshqarish — H-023.
- **Wagtail admin oʻzbekcha tarjimasi toʻliq emas** — muharrirlar rus tilini tanlashi mumkin (H-022).
- Admin workflow ni chetlab toʻgʻridan-toʻgʻri nashr qilsa, eski belgi saqlanib qoladi (H-020).
- wagtail-2fa uchun vaqtinchalik tuzatish — yangi versiya chiqqach olib tashlanadi (H-021).
- Yuklama testi VPS da emas, noutbukda oʻtkazilgan — staging da takrorlash kerak.
- Tashqi uptime monitor (H-016), Loki loglar (H-017), ZAP skan (H-019), brotli (H-015) — ixtiyoriy yaxshilanishlar.
- Qolgan H-bandlar (`docs/TODO_HARDENING.md`) — keyingi yaxshilashlar, launch ni toʻsmaydi.

Keyingi qadamlar: M5b (Figma kelganda) → LAUNCH_CHECKLIST boʻyicha M8 (ishga tushirish) → qoʻllab-quvvatlash 31.12.2026 gacha.
