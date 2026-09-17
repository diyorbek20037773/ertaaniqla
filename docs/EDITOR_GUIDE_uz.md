# «Erta aniqla» muharrir qoʻllanmasi (Wagtail CMS)

> Kopirayterlar, tekshiruvchi shifokorlar va kontent administratorlari uchun.
> Ruscha versiya: [EDITOR_GUIDE_ru.md](EDITOR_GUIDE_ru.md). Skrinshotlar: `tests/e2e/screenshots/cms-*.png`
> (`tests/e2e/test_cms_workflow.py` testi ularni avtomatik yangilaydi; skrinshotlarda CMS interfeysi rus tilida).

## 1. Asosiy qoidalar

1. **Sayt tashxis qoʻymaydi.** Har bir tibbiy fikr shifokor tekshiruvidan oʻtadi (6-boʻlim).
   Tekshiruvsiz sahifada «Shifokor tekshirgan» belgisi boʻlmaydi.
2. **Ikki til versiyasi — oʻzbekcha (lotin) va ruscha.** Har bir sahifa ikkala tilda boʻlishi kerak.
   Oʻzbek kirill versiyasi (`/oz/`) lotin versiyasidan avtomatik hosil qilinadi (5.3-boʻlim).
3. **Toʻldiruvchi belgilar.** Ishga tushirishda yaratilgan barcha sahifalarda
   `[[TODO: content — copywriter]]` (matnni kopirayter yozadi) va `[[VERIFY: doctor]]` (faktni shifokor
   tekshiradi) belgilari bor. Nashrdan oldin matnda bunday belgi qolmasligi shart.
4. **Bemorlarning shaxsiy maʼlumotlari** — faqat yozma rozilik bilan (8-boʻlim). Hech qachon
   F.I.Sh., telefon, hujjat suratlarini eʼlon qilmang.

## 2. CMS ga kirish va ikki bosqichli autentifikatsiya

Manzil: `https://ertaaniqla.uz/cms/`.

| Qadam | Nima qilish kerak | Skrinshot |
|---|---|---|
| 1 | Login va parolni kiriting (kamida 12 belgi). 5 marta xato kiritilsa, kirish 1 soatga bloklanadi. | `cms-01-login.png` |
| 2 | **Birinchi kirish:** CMS qurilma ulashni soʻraydi. Autentifikator ilovasini oʻrnating (Google Authenticator, Microsoft Authenticator, Yandex Klyuch), QR-kodni skanerlang, 6 xonali kodni kiriting, «Saqlash» tugmasini bosing. | — |
| 3 | **Har safar kirishda:** ilovadagi joriy 6 xonali kodni kiriting. | `cms-02-2fa-code.png` |

- Telefon yoʻqolsa — administratorga yozing: u eski qurilmani oʻchiradi, keyingi kirishda yangisini ulaysiz.
- Sessiya 8 soat amal qiladi. Birovning kompyuterida doim «Chiqish»ni bosing.
- CMS interfeysi tili: pastki chapdagi avatar → *Hisob* → *Afzalliklar* → *Til*.
  Wagtail interfeysining oʻzbekcha tarjimasi toʻliq emas, shuning uchun koʻp muharrirlar rus tilini tanlaydi.

## 3. Rollar

| Rol (guruh) | Kim | Qila oladi | Qila olmaydi |
|---|---|---|---|
| **Editor** (muharrir) | kopirayter | barcha tillarda sahifa yaratish va tahrirlash, tarjima qilish, tekshiruvga yuborish, rasm, hujjat, video yuklash, lugʻat, muassasalar, savollarni yuritish | nashr qilish, oʻchirish, sayt sozlamalari va foydalanuvchilarni oʻzgartirish, «Qayta aloqa» murojaatlarini koʻrish |
| **Medical Reviewer** (tekshiruvchi shifokor) | RONM / Ona va bola markazi / bolalar onkogematologiyasi shifokori | tekshiruvga yuborilgan sahifalarni koʻrib chiqish, tekshiruv vaqtida tahrirlash, **tasdiqlash** (nashr + belgi) yoki **tuzatish soʻrash**, tashrif buyuruvchilar savollariga javob berish, lugʻat taʼriflarini tahrirlash | sahifa yaratish, tekshiruvsiz nashr qilish |
| **Admin** (kontent administratori) | kontent rahbari | muharrir qila oladigan hamma narsa + nashr, oʻchirish, sayt sozlamalari, qayta yoʻnaltirishlar, foydalanuvchilar, tekshiruv jarayonlari, qayta aloqa murojaatlari | — |

Rollarni dasturchi (superfoydalanuvchi) belgilaydi: *Sozlamalar → Foydalanuvchilar → foydalanuvchi → Rollar*.
Shifokor foydalanuvchining «Tashkilot» maydoniga muassasani yozing — u «Shifokor tekshirgan» belgisida koʻrinadi.

## 4. Sayt tuzilmasi

```
Bosh sahifa (uz / ru)
├── Ayollar saratoni  /uz/ayollar/      (Женский рак /ru/zhenskiy/)
│   ├── Ogohlik → Koʻkrak bezi va bachadon boʻyni saratoni nima · Xavf omillari · Belgilar
│   ├── Skrining → Kimga va qanchalik tez-tez · Qayerda oʻtish mumkin
│   ├── Davolashni tashkil etish (bemor yoʻli, 4 qadam)
│   ├── Qayerga murojaat qilish (muassasalar maʼlumotnomasi + xarita)
│   ├── Davlat yordami
│   ├── Parvarish va qoʻllab-quvvatlash · Saratondan keyingi hayot
├── Bolalar saratoni  /uz/bolalar/      (Детский рак /ru/detskiy/)
├── Bemorlar hikoyalari · Savol-javob · Lugʻat · Tarqatish uchun materiallar
├── Foydali vositalar (skrining, oʻz-oʻzini tekshirish, bolalardagi belgilar) · Qayta aloqa
```

*Sahifalar* → tilni tanlang (roʻyxat tepasidagi almashtirgich) → kerakli boʻlimni oching.
Boʻlim sahifalarini koʻchirmang va oʻchirmang: menyu, boʻlim ranglari va manzillar ularga bogʻliq.

## 5. Sahifa yaratish va tarjima qilish

### 5.1 Yangi maqola (`cms-04-add-article.png`)

1. *Sahifalar* → kerakli mavzu (masalan, «Ogohlik») → «⋯» → *Quyi sahifa qoʻshish* → **Maqola**.
2. **Kontent** yorligʻi:
   - **Sarlavha** — qisqa, oddiy soʻzlar bilan (≤ 60 belgi).
   - **Qisqacha mazmun** (majburiy, ≤ 300 belgi) — kartochkalar, menyu va qidiruvda koʻrinadi.
   - **Asosiy rasm** — ixtiyoriy; har bir rasmda *muqobil matn* boʻlishi shart.
   - **Asosiy matn** — ⊕ ni bosing va blokni tanlang (quyidagi jadval).
3. **Promote** (targʻibot) yorligʻi: *Slug* (manzil qismi, lotincha: `xavf-omillari`), SEO sarlavha,
   qidiruv tizimlari uchun tavsif, ijtimoiy tarmoqlar uchun rasm (tanlanmasa — avtomatik yaratiladi).
4. Pastdagi tugma: **Qoralamani saqlash** — nashrsiz saqlaydi. Yonidagi ▲ →
   **Moderatsiyaga yuborish** (`cms-05-submit-for-moderation.png`).

### 5.2 Boshqa tilga tarjima (`cms-06-translate-submit.png`, `cms-07-translation-edit-uz.png`)

1. Asl sahifani oching → yuqoridagi «⋯» menyusi → **Ushbu sahifani tarjima qilish** (yoki
   `/cms/localize/submit/page/<id>/` manzili).
2. Tilni belgilang (masalan, *Oʻzbekcha*) → **Yuborish**. Ota sahifalar avtomatik yaratiladi.
3. Sahifa nusxasining oddiy muharriri ochiladi: **barcha** matnlar, sarlavha va slugni oʻzbekchaga
   almashtiring (`xavf-omillari`), havolalarni tekshiring.
4. **Moderatsiyaga yuborish** — tarjimani shifokor **alohida** tekshiradi (har bir til versiyasining belgisi oʻziniki).

Saytdagi til almashtirgich tarjima qilingan sahifaga olib boradi; tarjima boʻlmasa — boʻlim bosh sahifasiga.

### 5.3 Oʻzbek kirill yozuvi (`/oz/`)

Saytning kirill versiyasi (`/oz/…`, almashtirgichda «Ўзбекча») har safar sahifa ochilganda oʻzbekcha
lotin versiyasidan **avtomatik hosil qilinadi** (DECISIONS D-049). Kirillga alohida tarjima qilish va
shifokorga alohida tekshirtirish shart emas — lotin versiyasini nashr qilish kifoya.

- Oʻzbekcha matnni **lotin** yozuvida, `oʻ gʻ ʼ` belgilarini toʻgʻri qoʻyib yozing (`o' g'` ham boʻladi).
- Brend nomlari (Telegram, WhatsApp, YouTube…), havolalar, e-mail va `[[TODO]]` belgilari oʻzgartirilmaydi.
- Agar soʻz kirillda notoʻgʻri chiqsa (odatda «ь», «ц» li oʻzlashma soʻzlar: `sentabr` → «сентябрь»),
  dasturchiga xabar bering — soʻz istisnolar lugʻatiga qoʻshiladi (`apps/core/uzcyrl.py`).
- Oʻgirilmasligi kerak boʻlgan qismni (masalan, lotincha nom) dasturchi `translate="no"` bilan belgilaydi.

### 5.4 Kontent bloklari

| Blok | Nima uchun | Maslahat |
|---|---|---|
| Matn (rich text) | oddiy xatboshilar, H2/H3 sarlavhalar, roʻyxatlar, havolalar | H1 ishlatmang — sahifa sarlavhasi allaqachon bor |
| Ajratilgan blok | «Tashrifni kechiktirmang», ogohlantirishlar; turi: maʼlumot / ogohlantirish / xavf / yaxshi xabar / **tinchlantirish** | «tinchlantirish» — belgilar sahifalari uchun («bu belgi har doim saraton emas») |
| Uch ustun / Ikki ustun | TZ jadvallari «Parvarish va qoʻllab-quvvatlash», «Saratondan keyingi hayot», «Ota-onalar uchun / Yaqinlar uchun» | har bir ustunda sarlavha + roʻyxat |
| Qadamlar | bemor yoʻli (4 qadam), koʻkrak bezini oʻzi tekshirish | raqamni yozmasa ham boʻladi — 01, 02… qoʻyiladi; «Muddat» maydoni — masalan, PQ-402 boʻyicha yoʻllanma muddati |
| Kartochkalar | bolalar saratonining 6 turi, xavf omillari | ikonka yoki rasm, sarlavha, matn, havola |
| Belgilar roʻyxati | shoshilinchlik darajasi bilan belgilar: rejali / yaqin kunlarda / shoshilinch | shoshilinchlik rang, belgi va matn bilan koʻrsatiladi |
| Statistika | Oʻzbekiston boʻyicha raqamlar | manba va yil majburiy |
| Video | video kutubxonasidagi rolik yoki YouTube/Telegram havolasi | izoh va **transkriptsiya** qoʻshing (qulaylik + qidiruv) |
| Rasmlar galereyasi | infografika | materiallar uchun «yuklab olish mumkin»ni yoqing |
| Yuklab olinadigan hujjat | chop etish uchun PDF eslatmalar | — |
| Savol-javob (akkordeon) | «Shifokordan soʻrash muhim boʻlgan savollar» | — |
| Lugʻat atamalari | tanlangan atamalar taʼriflari | lugʻatdagi atamalar matnda ham avtomatik ajratiladi |
| Muassasalar roʻyxati | «Qayerda oʻtish mumkin» | hudud / tur / «bepul» boʻyicha filtr |
| Harakatga chaqiruv (CTA) | «Skrining qayerda oʻtishni topish» tugmasi | sayt ichidagi sahifaga havola tashqi havoladan afzal |
| Iqtibos | bemor / shifokor soʻzlari | faqat rozilik bilan |
| Jadval | skrining jadvali | birinchi qator — sarlavhalar |
| Joylashtirish | Instagram, TikTok, Telegram, YouTube | Instagram/TikTok faqat tashrif buyuruvchi bosganda yuklanadi |

## 6. Tibbiy tekshiruv (tekshiruvchi shifokor)

1. Muharrir **Moderatsiyaga yuborish**ni bosadi → sahifa **Medical review** jarayoniga tushadi.
2. Shifokor CMS ga kiradi: bosh panelda **«Sizning tekshiruvingizni kutmoqda»** bloki (`cms-08-dashboard-reviewer.png`).
3. Shifokor sahifani ochadi, kerak boʻlsa matnni tuzatadi, soʻng pastdagi ▲ (`cms-09-approve.png`):
   - **Shifokor tekshirgan deb tasdiqlash va nashr qilish** — sahifa nashr qilinadi va unda
     «✓ Shifokor tekshirgan: *ism*, *tashkilot* (*sana*)» paydo boʻladi (`cms-10-live-with-badge.png`);
   - **Izoh bilan tasdiqlash** — xuddi shunday + muharrirga izoh;
   - **Tuzatish soʻrash** — sahifa izoh bilan muharrirga qaytadi, hech narsa nashr qilinmaydi.
4. Belgini qoʻlda qoʻyib boʻlmaydi: sahifa sozlamalarida (*Sozlamalar → Tibbiy tekshiruv*) u faqat
   koʻrsatiladi. Sahifaning yangi versiyasi tekshiruvdan qayta oʻtadi — belgidagi sana yangilanadi.
5. Administrator ham Medical Reviewer guruhida boʻlmasa, tekshiruvni tasdiqlay olmaydi.

Jarayonlar holati: *Hisobotlar → Jarayonlar* (workflows) — kim va qachon yubordi, kim tasdiqladi.

## 7. Media fayllar

- **Rasmlar** (*Rasmlar → Qoʻshish*): JPEG/PNG/WebP, 20 MB gacha. Metamaʼlumotlar (EXIF, jumladan
  GPS) avtomatik oʻchiriladi. **Muqobil matn** majburiy («Ayol mammografiyadan oʻtmoqda»), bezak
  rasmlar uchun «dekorativ»ni belgilang.
- **Hujjatlar** (*Hujjatlar*): PDF va boshqalar, 50 MB gacha. **Maxfiy** belgisi — hujjat faqat
  CMS xodimlariga ochiq (rozilik shakllari!).
- **Video** (*Snippetlar → Video*):
  - *Turi*: uzun / qisqa vertikal (mobilograf);
  - *Manba*: fayl yuklash (512 MB gacha) yoki YouTube / Telegram / Instagram / TikTok havolasi;
  - yuklangan fayl avtomatik 720p va 480p ga oʻgiriladi + muqova. Holat:
    *yuklandi → qayta ishlanmoqda → tayyor* (yoki xato matni bilan *xato*). Maqolaga «tayyor» holatdagi videoni qoʻying;
  - oʻzbek va rus tilidagi `.vtt` subtitrlar, **transkriptsiya**, shifokor va tashkilot.

## 8. Bemorlar hikoyalari

*Sahifalar → Bemorlar hikoyalari → Qoʻshish* **Bemor hikoyasi**.

- **Koʻrsatiladigan ism** — taxallus boʻlishi mumkin; ism oʻzgartirilgan boʻlsa «anonimlashtirilgan»ni belgilang.
- **Rozilik olingan** — bu belgisiz sahifani **nashr qilib boʻlmaydi**.
- «Bolalar saratoni» boʻlimi uchun qoʻshimcha **qonuniy vakil roziligi**.
- **Rozilik hujjati** — imzolangan rozilik skaneri; avtomatik maxfiy boʻladi va saytda hech qachon koʻrinmaydi.
- Tashxis — qisqa, muharrir soʻzlari bilan, tibbiy hujjatlarsiz.

## 9. Muassasalar maʼlumotnomasi («Qayerga murojaat qilish»)

- Bittalab tahrirlash: *Snippetlar → Muassasalar*. Maydonlar: nomi (uz/ru), turi, hudud, tuman, manzil,
  telefon `+998 XX XXX-XX-XX`, ish vaqti, koordinatalar, «davlat dasturi boʻyicha bepul», xizmatlar, boʻlim, tekshirilgan sana.
- Sogʻliqni saqlash vazirligidan kelgan roʻyxatni **ommaviy yuklash** (administrator/dasturchi bajaradi):

  ```
  docker compose exec web python manage.py import_institutions /srv/import/institutions.csv --dry-run
  docker compose exec web python manage.py import_institutions /srv/import/institutions.csv
  ```

  CSV formati (UTF-8, birinchi qator — sarlavhalar, namuna `data/institutions.sample.csv`):
  `external_id,name_uz,name_ru,kind,region,district_uz,district_ru,address_uz,address_ru,phone,hours_uz,hours_ru,website,lat,lng,free,services,sections,verified_at`

  | Maydon | Qiymatlar |
  |---|---|
  | `kind` | `svp`, `polyclinic`, `onco_room`, `mother_child_centre`, `oncology_centre`, `paediatric_oncohaematology`, `psych_support`, `ngo` |
  | `region` | `tashkent-city`, `tashkent`, `andijan`, `bukhara`, `fergana`, `jizzakh`, `kashkadarya`, `khorezm`, `namangan`, `navoi`, `samarkand`, `surkhandarya`, `syrdarya`, `karakalpakstan` |
  | `services` | `;` bilan: `mammography`, `ultrasound`, `hpv_test`, `cytology`, `consultation`, `onco_alertness`, `paediatric_oncology`, `psychological_support` |
  | `sections` | `women`, `children`, `both` |
  | `free` | `1` / `0` |

  Qayta yuklash bir xil `external_id` li yozuvlarni yangilaydi, dublikat yaratmaydi. `--dry-run`
  faqat faylni tekshiradi va qatorlar boʻyicha xatolarni chiqaradi.

## 10. Tashrif buyuruvchilar savollari (FAQ)

*Snippetlar → Savollar*. Holatlar: **Yangi → Javob berilgan (ommaviy emas) → Eʼlon qilingan** yoki **Rad etilgan**.

- Shifokor javob beradi: «Javob» maydoni va «Javob bergan» maydoni (oʻzingizni tanlang). Nashr uchun
  «Eʼlon qilinadigan savol» maydonidan foydalaning — savolning tahrirlangan, anonim matni.
- Savolning asl matnini oʻzgartirib boʻlmaydi. Unda ism, telefon, qishloq nomi kabi odamni tanitadigan
  narsalar boʻlsa, savolni ularsiz «Eʼlon qilinadigan savol»ga qayta yozing (boʻsh maydon = saytda asl matn koʻrinadi).
- **Eʼlon qilish** faqat tashrif buyuruvchi «eʼlon qilishga roziman»ni belgilagan savol uchun mumkin —
  aks holda holat «Javob berilgan» boʻlib qoladi.
- Tashrif buyuruvchining kontakti shifrlangan holda saqlanadi va javobdan 90 kun oʻtgach avtomatik oʻchiriladi.

## 11. Lugʻat, materiallar, qayta aloqa

- **Lugʻat** (*Snippetlar → Atamalar*): atama, oddiy soʻzlar bilan taʼrif, boʻlim, sinonimlar
  (vergul bilan). Maqola matnida atamaning birinchi eslatilishi avtomatik izohli havolaga aylanadi.
- **Tarqatish uchun materiallar** («Materiallar» sahifasi): infografika, qisqa videolar, bloggerlar,
  erlar, ota-onalar, koʻngillilar uchun tayyor uz/ru izohlar va heshteglar.
- **Qayta aloqa** (*Snippetlar → Murojaatlar*, faqat Admin): fikrlar, xatolar haqida xabarlar,
  hamkorlik takliflari. 180 kundan keyin avtomatik oʻchiriladi.

## 12. Sayt sozlamalari (Admin)

*Sozlamalar → Sayt sozlamalari*: ishonch telefonlari, ijtimoiy tarmoq havolalari, pastki qism matni va
tibbiy ogohlantirish (uz/ru), **favqulodda banner** (masalan, skrining oyi), hamkorlar logotiplari,
Yandex.Metrika ID, maxfiylik siyosati sahifasi, Yandex.Webmaster / Google tasdiqlash kodlari.

Foydali vositalar (skrining tekshiruvi, oʻz-oʻzini tekshirish) matnlari tibbiy kelishilgandan keyingina
dasturchi tomonidan yoqiladi (`tools_screening`, `tools_selfcheck` bayroqlari).

## 13. Muharrirlarning tez-tez beradigan savollari

| Muammo | Yechim |
|---|---|
| «Nashr qilish» tugmasi yoʻq | Editor roli uchun shunday boʻlishi kerak — moderatsiyaga yuboring. |
| Oʻzgarishlar saytda koʻrinmayapti | Sahifa hali tekshiruvda yoki faqat qoralama saqlangan; nashrdan keyin kesh darhol yangilanadi. |
| Til almashtirgich boʻlim bosh sahifasiga olib boradi | Sahifaning tarjimasi yoʻq — uni yarating (5.2). |
| Rasm tanlab boʻlmayapti | Administratorga murojaat qiling: foydalanuvchi rolini tekshirsin. |
| Video «xato» holatida | Video kartochkasidagi xato matnini koʻring; odatda fayl buzilgan — qayta yuklang yoki YouTube havolasidan foydalaning. |
| Kirish bloklangan | 5 marta notoʻgʻri parol → 1 soatga blok; administrator oldinroq ochishi mumkin. |
