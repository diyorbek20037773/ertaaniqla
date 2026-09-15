# «ERTA ANIQLA» — loyihaning to'liq tushuntirishi (o'zbek tilida)

Bu hujjat — ruscha TZ (texnik topshiriq / konsepsiya, 14.05.2026) ning to'liq tahlili va siz, yagona dasturchi sifatida, nima qurishingiz kerakligining tushuntirishi. Kod yozish uchun `CLAUDE.md`, boshlash uchun `KICKOFF_PROMPT.md` ishlatiladi.

---

## 1. Bu loyiha aslida nima?

**Bu shifoxona sayti emas, davolash tizimi emas, tashxis qo'yadigan dastur ham emas.** Bu — **axborot-ta'lim portali**. Uning bitta vazifasi bor: odam saratonning ilk belgisini o'zida yoki bolasida ko'rganda qo'rqib qolmasin, "bu nima?" degan savoliga oddiy tilda javob topsin va **ertaga emas, bugun shifokorga borsin**. TZ da bu «онконастороженность» — "onkologik ogohlik" deyiladi.

Huquqiy asos: Prezidentning PQ-402 (22.11.2024 — ayollar saratonini erta aniqlash) va PQ-186 (19.05.2025 — bolalar saratoniga qarshi 2030 gacha milliy strategiya) qarorlari. Buyurtmachi — Strategik islohotlar agentligi qoshidagi «Innovatsiyalarni joriy etish va byurokratiyani bartaraf etish — 2030» loyiha ofisi. Homiylar — Yandex va Hamroh. Tibbiy hamkorlar — RONM (Respublika onkologiya ilmiy markazi), Ona va bola salomatligi markazi, Bolalar onkogematologiyasi.

Domen: **ertaaniqla.uz** (hujjatning boshqa joyida oncoportal.uz ham tilga olingan — ikkalasini ham qo'llab-quvvatlaymiz, asosiysi ertaaniqla.uz).

Muddat TZ bo'yicha: iyul 2026 — prototip, avgust 2026 — ishga tushirish, dekabrgacha kontent ishlab chiqarish. Server: 8 yadro / 16 GB / 1 TB NVMe.

## 2. Sayt ikki mustaqil bo'limdan iborat

Bitta navigatsiya, bitta dizayn tizimi, lekin har bo'limning **o'z rangi** bor:

| 🎗 Ayollar saratoni (pushti) | 🎀 Bolalar saratoni (oltin/sariq) |
|---|---|
| Ko'krak bezi saratoni (РМЖ) va bachadon bo'yni saratoni (РШМ) | Bolalardagi onkologik kasalliklar |
| Ogohlik → Skrining → Davolashni tashkil etish → Qayerga murojaat → Davlat ko'magi → Parvarish va qo'llab-quvvatlash → Saratondan keyingi hayot | Bolalar onkokasalliklari haqida → Diagnostika va davolash → Parvarish va qo'llab-quvvatlash → Oila uchun ma'lumot → Saratondan keyingi hayot |

### 2.1 Ayollar bo'limi — har bir sahifada nima bo'lishi shart

- **Ogohlik**: "РМЖ va РШМ nima" (organizmda nima bo'ladi, bosqichlar, O'zbekiston statistikasi); **xavf omillari** (yosh, irsiyat, turmush tarzi, HPV-infeksiya); **belgilar** (e'tiborsiz qoldirib bo'lmaydigan belgilar + **ko'krakni o'z-o'zini tekshirish bosqichma-bosqich qo'llanmasi**).
- **Skrining**: *kimga va qanchalik tez-tez* — mammografiya 45–65 yosh, 2 yilda 1 marta; UZI 45 yoshgacha, 2 yilda 1 marta; HPV-test 30–50 yosh; o'z-o'zini tekshirishga chaqiriqlar. *Qayerdan o'tish* — oilaviy shifokorlik punktlari, tuman poliklinikalari (onkologik ogohlik xonalari), Ona va bola markazi va filiallari; **davlat dasturi doirasida bepul**.
- **Davolashni tashkil etish** — bemorning 4 bosqichli yo'li: 01 birlamchi qabul (terapevt/ginekolog) → 02 diagnostikaga yo'llanma (UZI, mammografiya, onko-ogohlik xonasi) → 03 onkolog/onkoginekolog (onkologiya markaziga yo'llanma) → 04 davolash bosqichlari.
- **Davlat ko'magi** — bepul skrining, onko-ogohlik xonalari imkoniyatlari, bemor va shifokor huquq-majburiyatlari.
- **Parvarish va qo'llab-quvvatlash** — 3 ustun: jismoniy salomatlik (ovqatlanish, nojo'ya ta'sirlar, teri/soch parvarishi, reabilitatsiya) / emotsional ko'mak (qo'rquv bilan kurashish, psixolog, yaqinlar, o'zaro yordam guruhlari) / amaliy savollar (kasallik varaqasi va mehnat huquqlari, moliyaviy ko'mak, yaqin insonga qanday yordam berish, shifokorga beriladigan savollar).
- **Saratondan keyingi hayot** — 3 ustun: kuzatuv (nazorat ko'riklari jadvali, kechki ta'sirlar, salomatlik pasporti) / hayotga qaytish (ish, reabilitatsiya, emotsional tiklanish) / uzoq muddatli salomatlik (retsidiv profilaktikasi, reproduktiv salomatlik, psixologik farovonlik).

### 2.2 Bolalar bo'limi — St. Jude (AQSh) "Together" platformasi modelida

- **Eng ko'p uchraydigan turlar** — 6 ta karta: leykozlar (ОЛЛ, ОМЛ) / limfomalar (Xodjkin, no-Xodjkin) / miya o'smalari (medulloblastoma, astrotsitoma) / neyroblastoma / sarkomalar (yumshoq to'qima, Yuing) / boshqalar (Vilms, retinoblastoma, gepatoblastoma). Qo'shimcha: bolalar onko-jamoasi qanday ishlaydi; irsiy xavf va genetik test; O'zbekiston statistikasi.
- **Diagnostika va davolash** — tahlillar, KT/MRT/PET, biopsiya, "natijalarni qanday o'qish: ota-onalar lug'ati", shifokorga savollar / kimyoterapiya, nur terapiyasi, suyak iligi transplantatsiyasi, immuno- va target-terapiya, klinik sinovlar.
- **Parvarish** — jismoniy (ovqatlanish, og'riq, infeksion xavfsizlik, markaziy venoz kateterlar) / emotsional (bola bilan kasallik haqida gaplashish, ota-ona xavotiri, aka-uka/opa-singillar, psixologik xizmatlar) / amaliy (shifoxonada o'qish, moliyaviy yordam, bola-bemor huquqlari, qo'llab-quvvatlash guruhlari).
- **Oila uchun** — ota-onalar uchun / yaqinlar uchun (TZ dagi barcha bandlar).
- **Saratondan keyingi hayot** — kuzatuv / hayotga qaytish (maktab!) / uzoq muddatli salomatlik (o'sish va rivojlanish, reproduktiv, retsidiv profilaktikasi).

### 2.3 Kontent formatlari (ikkala bo'lim uchun)

Shifokorlar ishtirokidagi uzun videolar; ijtimoiy tarmoqlar uchun "mobilograf" qisqa vertikal videolar; infografika va belgilar illyustratsiyasi; real bemorlar hikoyalari (**rozilik bilan**); tarqatish materiallari (erlar, bolalar, ota-onalar, ko'ngilli blogerlar uchun).

## 3. TZ da dasturchidan bevosita talab qilingan narsalar (5.1-band)

1. Ikki tilli (rus/o'zbek) platformani **ishlab chiqish va texnik kuzatib borish**, ikkala bo'lim bilan, **mobil qurilmalarga moslashgan**.
2. **Barqaror ishlash**: administrlash, kontentni yangilash, xatolarni bartaraf etish, **foydalanuvchi ma'lumotlarini himoya qilish**.
3. **Multimedia integratsiyasi** (video, infografika, **qayta aloqa formalari**, navigatsiya) va **tezlikni optimallashtirish**.

Ya'ni siz faqat "sayt qilib berish" emas — yil oxirigacha (byudjetda "с поддержкой до конца года" deb yozilgan) **DevOps + admin + qo'llab-quvvatlash** ham qilasiz. Shuning uchun CLAUDE.md da monitoring, backup, CI/CD shunchalik jiddiy yozilgan: 3 oydan keyin tunda server yiqilsa, buni siz bir o'zingiz 2 soatda tiklay olishingiz kerak.

## 4. Nima uchun aynan shu stack

**Django 5 + Wagtail 6 + wagtail-localize + PostgreSQL + Redis + Celery + HTMX + Alpine.js + Tailwind + Docker Compose + nginx.**

- **Wagtail** — bu Django ustidagi eng kuchli CMS. Kopirayter va shifokor kodga tegmasdan maqola yozadi, rasm/video yuklaydi, preview ko'radi, tarjima qiladi (wagtail-localize — sahifaning ruscha va o'zbekcha nusxasini yonma-yon boshqaradi), "Shifokor tekshirdi" belgisini qo'yadi. Buni o'zingiz yozsangiz — 2 oy ketadi, Wagtail'da tayyor.
- **Django templates + HTMX + Alpine** (React/Next.js emas) — SEO uchun server HTMLni tayyor beradi, Google/Yandex darrov indekslaydi. Bitta til, bitta repo, bitta deploy — bir kishi uchun ideal. Kerakli interaktivlik (qidiruv, filtr, checklist, akkordeon) HTMX/Alpine bilan 30 KB JS da hal bo'ladi. Hududlardagi 3G internetda 100 KB sahifa 1–2 soniyada ochiladi.
- **PostgreSQL** — Wagtail'ning StreamField JSONB da yaxshi ishlaydi, ichida to'liq matnli qidiruv (FTS) bor, alohida Elasticsearch shart emas.
- **Redis** — kesh + sessiyalar + Celery navbati.
- **Celery** — video transkodlash (ffmpeg), email, backup, PII tozalash — fon ishlari.
- **Docker Compose bitta VPS'da** — Kubernetes bir kishi uchun ortiqcha. Compose bilan 8 ta konteyner (nginx, web, worker, beat, db, redis, backup, monitoring) bitta faylda, `docker compose up -d` bilan ko'tariladi, boshqa serverga 1 soatda ko'chadi.

## 5. Tizim dizayni — qanday ishlaydi (oddiy tilda)

1. Foydalanuvchi `ertaaniqla.uz/uz/ayollar/skrining/` ni ochadi.
2. **nginx** (eshik) — TLS (https), statik fayllar va rasm/videoni o'zi beradi; anonim foydalanuvchi uchun tayyor HTML sahifani 10 soniya "mikro-kesh"da saqlaydi — 1000 kishi bir vaqtda kirsa ham Django'ga 1 ta so'rov boradi.
3. **gunicorn + Django/Wagtail** — sahifani DB dan yig'adi, Redis'ga 5 daqiqaga keshlaydi; muharrir sahifani "publish" qilganda kesh darhol tozalanadi.
4. **PostgreSQL** — sahifalar daraxti, tarjimalar, muassasalar, savollar.
5. **Celery worker** — mobilograf 300 MB video yuklasa, sayt qotib qolmaydi: worker fonda 720p/480p ga siqadi, poster rasm chiqaradi, tayyor bo'lgach sahifada ko'rinadi.
6. **Backup konteyneri** — har kecha 02:00 da DB dump + media → shifrlangan holda O'zbekistondagi boshqa joyga; har hafta avtomatik "tiklab ko'rish" testi.
7. **Monitoring** — Sentry (xatolar), Prometheus/Grafana (metrikalar), Telegram'ga alert: 5xx > 1%, disk > 80%, backup 26 soatdan eski, sertifikat 14 kundan kam qoldi.

Asosiy prinsip: **sayt 99.9% o'qiladi, kamdan-kam yoziladi** — shuning uchun hamma narsa kesh atrofida qurilgan. Web konteynerlar holatsiz (stateless) — kerak bo'lsa `scale web=2`.

## 6. Ma'lumotlar modeli (Wagtail sahifa turlari)

- `HomePage` → 2 ta `SectionIndexPage` (ayollar/bolalar, har biri o'z rangi bilan) → `TopicIndexPage` (Skrining, Diagnostika…) → `ArticlePage`.
- `ArticlePage` ning tanasi — **StreamField bloklari**: matn, callout ("Tashrifni kechiktirmang"), 3 ustun (TZ dagi jadvallar aynan shu), 2 ustun, bosqichlar (bemor yo'li 01–04, o'z-o'zini tekshirish), kartalar to'plami (6 ta bolalar saratoni turi), belgilar ro'yxati (shoshilinchlik rangi bilan), statistika, video (transkript bilan), galereya, yuklab olinadigan hujjat, FAQ-akkordeon, lug'at atamalari, muassasalar ro'yxati, CTA, iqtibos, jadval, embed.
- `PatientStoryPage` — `consent_obtained=True` bo'lmasa **publish bo'lmaydi** (kodda majburlanadi), rozilik hujjati maxfiy saqlanadi.
- `Video` — yuklangan yoki YouTube/Telegram havola; `long` / `short_vertical`; subtitrlar uz/ru.
- `Institution` + `Region` — "Qayerga murojaat qilish" katalogi: 14 hudud, tur (SVP, poliklinika, onko-ogohlik xonasi, Ona-bola markazi, onkologiya markazi, bolalar onkogematologiyasi, psixologik yordam, NNT), xizmatlar, "davlat dasturi bo'yicha bepul" belgisi, xarita (Leaflet + OSM).
- `Term` — ota-onalar lug'ati, matnda birinchi uchragan atamaga tooltip.
- `Question` — "shifokorga savol" formasi → moderatsiya → anonim FAQ. Kontakt shifrlangan, 90 kundan keyin avtomatik o'chadi.
- `FeedbackSubmission` — qayta aloqa, 180 kun saqlanadi.

## 7. Qo'shimcha (TZ da yo'q, lekin "erta aniqlash"ga bevosita xizmat qiladi, arzon)

Skrining kalkulyatori ("menga qaysi tekshiruv kerak?" — yosh + oxirgi tekshiruv sanasi, hech narsa saqlanmaydi); belgilar bo'yicha o'z-o'zini tekshirish checklisti (natija: "N kun ichida shifokorga boring" + eng yaqin muassasa, **tashxis emas**); to'liq matnli qidiruv; chop etish/PDF (poliklinikalar bosib osadi); blogerlar uchun "materiallar to'plami" sahifasi; Yandex.Metrika (rozilik bilan); kirish imkoniyati paneli (shrift kattalashtirish, kontrast). Bularni CLAUDE.md da A1–A8 deb belgiladim — qilamiz, lekin tibbiy tasdiqdan oldin feature-flag ostida.

## 8. Xavfsizlik va shaxsiy ma'lumotlar — bu yerda ehtiyot bo'ling

- **ЗРУ-547 "Shaxsiy ma'lumotlar to'g'risida"gi qonun** — O'zbekiston fuqarolarining shaxsiy ma'lumotlari **O'zbekiston hududidagi serverda** saqlanishi shart. Demak VPS ham, backup ham O'zbekistonda. Hetzner/AWS'ga qo'ymang.
- Tashrif buyuruvchilar uchun akkaunt yo'q, formalarda minimal ma'lumot, kontakt ixtiyoriy, rozilik checkbox.
- PII ustunlari shifrlangan, avtomatik tozalanadi. Rasmlardan EXIF (GPS!) o'chiriladi.
- CMS: 2FA majburiy, `django-axes`, admin `/admin/` da emas, IP ro'yxati (ixtiyoriy).
- CSP, HSTS, xavfsiz cookie'lar, `pip-audit` + `trivy` CI da.
- Google Analytics yo'q; Yandex.Metrika faqat rozilikdan keyin.
- Har bir "vosita" sahifasida va footer'da tibbiy disclaimer.

## 9. Kirish imkoniyati (WCAG 2.1 AA) — bu ixtiyoriy emas

Auditoriya — xavotirdagi ayollar, keksalar, ota-onalar, hududlardagi arzon telefonlar. Klaviatura bilan ishlash, `alt` majburiy, video subtitr + transkript, kontrast ≥ 4.5:1, 44px tugmalar, `pa11y-ci` CI da. O'zbek lotin harflari (oʻ, gʻ) shrift subsetida bo'lishi — tekshiriladi.

## 10. Ish rejasi (7 hafta + launch)

| Hafta | Nima |
|---|---|
| M0 (1–2 kun) | Repo, Docker dev, CI skeleti, TZ ni `docs/` ga, `TZ_TRACE.md` (har bir TZ bandi → kod → test jadvali) |
| M1 | Sahifa modellari, bloklar, i18n, **`seed_content` — TZ dagi to'liq daraxt uz+ru** placeholder bilan, bazaviy layout, menyu, til almashtirgich |
| M2 | Barcha komponentlar, bo'lim ranglari, bosh sahifa, qidiruv |
| M3 | Video transkodlash, galereya, yuklamalar, OG-rasm, bemor hikoyalari |
| M4 | Katalog + xarita, vositalar (skrining, o'z-tekshiruv, bemor yo'li), FAQ/savol formasi, lug'at |
| M5 | SEO (JSON-LD, sitemap, hreflang), a11y, performance, print |
| M6 | Prod DevOps: nginx/TLS, backup + restore test, monitoring, staging, CD, RUNBOOK, VPS bootstrap, 2FA |
| M7 | Muharrir qo'llanmasi (ru/uz), rollar va workflow (muharrir → shifokor tasdig'i → publish), UAT, load test |
| M8 | Launch, keyin: 48 soatlik bug SLA, oylik yangilanish, choraklik restore mashqi |

## 11. Claude Code bilan qanday ishlaysiz

1. Loyiha papkasini yarating, ichiga `CLAUDE.md` ni qo'ying, `docs/TZ_concept_ru.md` ni qo'ying.
2. VS Code'da Claude Code'ni oching, `KICKOFF_PROMPT.md` matnini birinchi xabar sifatida yuboring.
3. Claude avval **reja** beradi — o'qing, "ok" deng. Har qadamdan keyin `make check` natijasini so'rang.
4. Har milestone oxirida `docs/TZ_TRACE.md` ni oching: TZ ning har bir bandi "done" bo'lganini o'zingiz tekshiring. Bu — "1000% TZ dagidek" ning kafolati.
5. Tibbiy matnni hech qachon Claude'dan yozdirmang — u placeholder qo'yadi, matnni kopirayter + RONM shifokorlari beradi. Bu sizni ham, loyihani ham himoya qiladi.
6. Keyingi sessiyalarda: "CLAUDE.md §13 dagi M2 ni boshla, avval reja ber" — shu kifoya, Claude kontekstni CLAUDE.md dan oladi.

## 12. TZ da noaniq qolgan, buyurtmachidan so'rashingiz kerak bo'lgan narsalar

- Domen: ertaaniqla.uz yoki oncoportal.uz? (ikkalasi ham hujjatda). Kim sotib oladi/kimning nomida?
- VPS provayder qaysi (O'zbekistonda bo'lishi shart)? Kim to'laydi? SSH kirish kimda?
- "DMED narxini aniqlashtirish" — DMED bilan integratsiya kutilyaptimi (masalan, skrining yozuvi)? Agar ha — bu alohida katta ish, TZ ga kirmagan.
- Muassasalar ro'yxati (nomi, manzil, telefon, hudud) kimdan keladi? CSV formatida so'rang.
- O'zbek tili — lotinmi, kirillmi? (Men lotin deb oldim, kirill keyin qo'shiladi.)
- Rasmiy logotip, ranglar — dizaynerdan qachon?
- Bemor hikoyalari uchun rozilik shakli (yuridik matn) kimdan?
- Video: o'z serverda saqlaymizmi (1 TB yetadi) yoki YouTube'da? Men ikkalasini qo'llab-quvvatlaydigan qilib yozdim.
- Yandex.Metrika hisobi kimniki?
