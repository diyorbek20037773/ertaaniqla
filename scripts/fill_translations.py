"""Fill uz/ru translations for UI strings (run after `make messages`).

Kept in the repo so the wording is reviewable; safe to re-run (only fills empty entries).
Usage: python scripts/fill_translations.py
"""

from __future__ import annotations

from pathlib import Path

import polib

ROOT = Path(__file__).resolve().parent.parent

# msgid: (uz, ru)
T: dict[str, tuple[str, str]] = {
    "Page": ("Sahifa", "Страница"),
    "External URL": ("Tashqi havola", "Внешняя ссылка"),
    "Link": ("Havola", "Ссылка"),
    "Choose either a page or a URL, not both.": (
        "Sahifa yoki havoladan faqat bittasini tanlang.",
        "Выберите либо страницу, либо ссылку, но не обе.",
    ),
    "Text": ("Matn", "Текст"),
    "Info": ("Maʼlumot", "Информация"),
    "Warning": ("Ogohlantirish", "Предупреждение"),
    "Danger — do not delay": ("Xavf — kechiktirmang", "Опасно — не откладывайте"),
    "Success / good news": ("Yaxshi xabar", "Хорошая новость"),
    "Reassurance (this sign is not always cancer)": (
        "Tinchlantirish (bu belgi har doim saraton emas)",
        "Успокоение (этот признак не всегда рак)",
    ),
    "Kind": ("Turi", "Тип"),
    "Title": ("Sarlavha", "Заголовок"),
    "Callout": ("Ajratilgan blok", "Выделенный блок"),
    "Items (list)": ("Bandlar (roʻyxat)", "Пункты (список)"),
    "Columns": ("Ustunlar", "Колонки"),
    "Three columns": ("Uch ustun", "Три колонки"),
    "Two columns": ("Ikki ustun", "Две колонки"),
    "Number": ("Raqam", "Номер"),
    "Leave empty to number automatically (01, 02, …).": (
        "Avtomatik raqamlash uchun boʻsh qoldiring (01, 02, …).",
        "Оставьте пустым для автоматической нумерации (01, 02, …).",
    ),
    "Deadline / timing": ("Muddat / vaqt", "Срок / сроки"),
    "E.g. referral deadline per PP-402. Shown as a separate line.": (
        "Masalan, PQ-402 boʻyicha yoʻllanma muddati. Alohida qatorda koʻrsatiladi.",
        "Например, срок направления по ПП-402. Показывается отдельной строкой.",
    ),
    "Heading": ("Sarlavha", "Заголовок"),
    "Steps": ("Qadamlar", "Шаги"),
    "Steps (patient route, self-exam guide)": (
        "Qadamlar (bemor yoʻli, oʻz-oʻzini tekshirish)",
        "Шаги (маршрут пациента, самообследование)",
    ),
    "Icon name": ("Ikonka nomi", "Имя иконки"),
    "Optional icon identifier for the designer (e.g. 'dna', 'age').": (
        "Dizayner uchun ixtiyoriy ikonka identifikatori (masalan, 'dna', 'age').",
        "Необязательный идентификатор иконки для дизайнера (например, 'dna', 'age').",
    ),
    "Cards": ("Kartalar", "Карточки"),
    "Cards grid": ("Kartalar toʻri", "Сетка карточек"),
    "Routine — mention at the next visit": (
        "Odatiy — keyingi tashrifda ayting",
        "Планово — скажите на следующем приёме",
    ),
    "Soon — see a doctor within days": (
        "Tez orada — bir necha kun ichida shifokorga boring",
        "Скоро — обратитесь к врачу в ближайшие дни",
    ),
    "Urgent — see a doctor now": (
        "Shoshilinch — hoziroq shifokorga boring",
        "Срочно — обратитесь к врачу сейчас",
    ),
    "Symptom": ("Belgi", "Симптом"),
    "Urgency": ("Shoshilinchlik", "Срочность"),
    "Symptoms": ("Belgilar", "Симптомы"),
    "Symptom list": ("Belgilar roʻyxati", "Список симптомов"),
    "Value": ("Qiymat", "Значение"),
    "E.g. '1 из 8' or '45–65'.": (
        "Masalan, '8 dan 1' yoki '45–65'.",
        "Например, «1 из 8» или «45–65».",
    ),
    "Label": ("Izoh", "Подпись"),
    "Source": ("Manba", "Источник"),
    "Year": ("Yil", "Год"),
    "Statistic": ("Statistika", "Статистика"),
    "Video from library": ("Kutubxonadagi video", "Видео из библиотеки"),
    "YouTube, Telegram, Instagram or TikTok link (used when no library video).": (
        "YouTube, Telegram, Instagram yoki TikTok havolasi (kutubxona videosi boʻlmasa).",
        "Ссылка YouTube, Telegram, Instagram или TikTok (если нет видео из библиотеки).",
    ),
    "Caption": ("Izoh", "Подпись"),
    "Transcript": ("Transkript", "Расшифровка"),
    "Video": ("Video", "Видео"),
    "Choose a video or enter an external URL.": (
        "Video tanlang yoki tashqi havola kiriting.",
        "Выберите видео или укажите внешнюю ссылку.",
    ),
    "Only YouTube, Telegram, Instagram and TikTok links are supported.": (
        "Faqat YouTube, Telegram, Instagram va TikTok havolalari qoʻllab-quvvatlanadi.",
        "Поддерживаются только ссылки YouTube, Telegram, Instagram и TikTok.",
    ),
    "Allow download (infographics)": (
        "Yuklab olishga ruxsat (infografika)",
        "Разрешить скачивание (инфографика)",
    ),
    "Image gallery / infographics": (
        "Rasmlar galereyasi / infografika",
        "Галерея изображений / инфографика",
    ),
    "Document download": ("Hujjatni yuklab olish", "Скачивание документа"),
    "Answer": ("Javob", "Ответ"),
    "FAQ accordion / questions to ask the doctor": (
        "Savol-javob akkordeoni / shifokorga savollar",
        "Аккордеон вопросов / вопросы врачу",
    ),
    "Terms": ("Atamalar", "Термины"),
    "All regions": ("Barcha viloyatlar", "Все регионы"),
    "All types": ("Barcha turlar", "Все типы"),
    "Region": ("Viloyat", "Регион"),
    "Type": ("Turi", "Тип"),
    "Only free under the state programme": (
        "Faqat davlat dasturi boʻyicha bepul",
        "Только бесплатно по госпрограмме",
    ),
    "Max items": ("Maksimal soni", "Макс. количество"),
    "Institution list": ("Muassasalar roʻyxati", "Список учреждений"),
    "Button label": ("Tugma matni", "Текст кнопки"),
    "Primary (section colour)": ("Asosiy (boʻlim rangi)", "Основная (цвет раздела)"),
    "Secondary": ("Ikkilamchi", "Вторичная"),
    "Style": ("Uslub", "Стиль"),
    "Call to action": ("Harakatga chaqiriq", "Призыв к действию"),
    "A page or a URL is required.": (
        "Sahifa yoki havola kiritilishi shart.",
        "Нужна страница или ссылка.",
    ),
    "Quote": ("Iqtibos", "Цитата"),
    "Author": ("Muallif", "Автор"),
    "Rich text": ("Formatlangan matn", "Форматированный текст"),
    "Table": ("Jadval", "Таблица"),
    "URL": ("Havola (URL)", "Ссылка (URL)"),
    "YouTube, Telegram post, Instagram post/reel or TikTok video.": (
        "YouTube, Telegram posti, Instagram post/reel yoki TikTok videosi.",
        "YouTube, пост Telegram, пост/reel Instagram или видео TikTok.",
    ),
    "Embed (YouTube / Telegram / Instagram / TikTok)": (
        "Joylashtirish (YouTube / Telegram / Instagram / TikTok)",
        "Встраивание (YouTube / Telegram / Instagram / TikTok)",
    ),
    "summary": ("qisqacha mazmun", "краткое описание"),
    "Shown in listings, the mega-menu and search results.": (
        "Roʻyxatlarda, mega-menyuda va qidiruv natijalarida koʻrsatiladi.",
        "Показывается в списках, мега-меню и результатах поиска.",
    ),
    "body": ("asosiy matn", "содержимое"),
    "Women's cancer": ("Ayollar saratoni", "Женский рак"),
    "Childhood cancer": ("Bolalar saratoni", "Детский рак"),
    "social sharing image": ("ijtimoiy tarmoq rasmi", "изображение для соцсетей"),
    "Shown when the page is shared in Telegram/Facebook. Generated automatically if empty.": (
        "Sahifa Telegram/Facebook’da ulashilganda koʻrsatiladi. Boʻsh boʻlsa avtomatik yaratiladi.",
        "Показывается при публикации ссылки в Telegram/Facebook. Если пусто — создаётся автоматически.",
    ),
    "hide from search engines": ("qidiruv tizimlaridan yashirish", "скрыть от поисковых систем"),
    "Adds a noindex meta tag. Use for drafts-in-public and utility pages.": (
        "noindex meta-tegini qoʻshadi. Ochiq qoralamalar va xizmat sahifalari uchun.",
        "Добавляет мета-тег noindex. Для черновиков и служебных страниц.",
    ),
    "medically reviewed by": ("tibbiy tekshiruvni oʻtkazgan", "медицинский рецензент"),
    "reviewed on": ("tekshirilgan sana", "дата проверки"),
    "medically verified": ("tibbiy tasdiqlangan", "проверено врачом"),
    "Shows the 'Verified by a doctor' badge. Set by the medical reviewer.": (
        "«Shifokor tekshirgan» belgisini koʻrsatadi. Tibbiy rezensent belgilaydi.",
        "Показывает бейдж «Проверено врачом». Устанавливает медицинский рецензент.",
    ),
    "Medical review": ("Tibbiy tekshiruv", "Медицинская проверка"),
    "hotline phone": ("ishonch telefoni", "телефон горячей линии"),
    "Format: +998 XX XXX-XX-XX": ("Format: +998 XX XXX-XX-XX", "Формат: +998 XX XXX-XX-XX"),
    "second hotline phone": ("ikkinchi ishonch telefoni", "второй телефон горячей линии"),
    "Telegram channel": ("Telegram kanali", "Telegram-канал"),
    "Instagram": ("Instagram", "Instagram"),
    "Facebook": ("Facebook", "Facebook"),
    "YouTube": ("YouTube", "YouTube"),
    "TikTok": ("TikTok", "TikTok"),
    "footer text (uz)": ("pastki matn (uz)", "текст подвала (uz)"),
    "footer text (ru)": ("pastki matn (ru)", "текст подвала (ru)"),
    "medical disclaimer (uz)": ("tibbiy ogohlantirish (uz)", "медицинский дисклеймер (uz)"),
    "medical disclaimer (ru)": ("tibbiy ogohlantirish (ru)", "медицинский дисклеймер (ru)"),
    "show emergency banner": ("shoshilinch bannerni koʻrsatish", "показывать экстренный баннер"),
    "emergency banner (uz)": ("shoshilinch banner (uz)", "экстренный баннер (uz)"),
    "emergency banner (ru)": ("shoshilinch banner (ru)", "экстренный баннер (ru)"),
    "emergency banner link": ("banner havolasi", "ссылка баннера"),
    "Yandex.Metrika counter id": ("Yandex.Metrika hisoblagich ID", "ID счётчика Яндекс.Метрики"),
    "legal / privacy text (uz)": (
        "huquqiy / maxfiylik matni (uz)",
        "правовой текст / политика (uz)",
    ),
    "legal / privacy text (ru)": (
        "huquqiy / maxfiylik matni (ru)",
        "правовой текст / политика (ru)",
    ),
    "Agency logo": ("Agentlik logotipi", "Логотип Агентства"),
    "Yandex logo": ("Yandex logotipi", "Логотип Яндекса"),
    "Hamroh logo": ("Hamroh logotipi", "Логотип Hamroh"),
    "Hotline": ("Ishonch telefoni", "Горячая линия"),
    "Social networks": ("Ijtimoiy tarmoqlar", "Социальные сети"),
    "Footer & legal": ("Pastki qism va huquqiy matnlar", "Подвал и правовые тексты"),
    "Emergency banner (e.g. screening month)": (
        "Shoshilinch banner (masalan, skrining oyi)",
        "Экстренный баннер (например, месяц скрининга)",
    ),
    "Partner logos": ("Hamkorlar logotiplari", "Логотипы партнёров"),
    "site settings": ("sayt sozlamalari", "настройки сайта"),
    "code": ("kod", "код"),
    "name (uz)": ("nomi (uz)", "название (uz)"),
    "name (ru)": ("nomi (ru)", "название (ru)"),
    "sort order": ("tartib", "порядок сортировки"),
    "region": ("viloyat", "регион"),
    "service": ("xizmat", "услуга"),
    "services": ("xizmatlar", "услуги"),
    "Family doctor point (SVP)": (
        "Oilaviy shifokorlik punkti (OShP)",
        "Семейный врачебный пункт (СВП)",
    ),
    "District polyclinic": ("Tuman poliklinikasi", "Районная поликлиника"),
    "Onco-alertness room": ("Onkologik ogohlik xonasi", "Кабинет онконастороженности"),
    "Mother & Child Health Centre / branch": (
        "Ona va bola salomatligi markazi / filiali",
        "Центр здоровья матери и ребёнка / филиал",
    ),
    "Oncology centre (RONC / regional)": (
        "Onkologiya markazi (RONM / viloyat)",
        "Онкологический центр (РОНЦ / региональный)",
    ),
    "Paediatric onco-haematology": ("Bolalar onkogematologiyasi", "Детская онкогематология"),
    "Psychological support": ("Psixologik yordam", "Психологическая поддержка"),
    "NGO / support group": ("NNT / qoʻllab-quvvatlash guruhi", "НКО / группа поддержки"),
    "Both": ("Ikkalasi", "Оба"),
    "kind": ("turi", "тип"),
    "district (uz)": ("tuman (uz)", "район (uz)"),
    "district (ru)": ("tuman (ru)", "район (ru)"),
    "address (uz)": ("manzil (uz)", "адрес (uz)"),
    "address (ru)": ("manzil (ru)", "адрес (ru)"),
    "phone": ("telefon", "телефон"),
    "opening hours (uz)": ("ish vaqti (uz)", "часы работы (uz)"),
    "opening hours (ru)": ("ish vaqti (ru)", "часы работы (ru)"),
    "website": ("veb-sayt", "сайт"),
    "latitude": ("kenglik", "широта"),
    "longitude": ("uzunlik", "долгота"),
    "free under the state programme": (
        "davlat dasturi boʻyicha bepul",
        "бесплатно по госпрограмме",
    ),
    "data verified on": ("maʼlumot tekshirilgan sana", "дата проверки данных"),
    "published": ("eʼlon qilingan", "опубликовано"),
    "external id": ("tashqi ID", "внешний ID"),
    "Identifier in an external registry (e.g. DMED) for future synchronisation.": (
        "Kelajakda sinxronlash uchun tashqi reyestrdagi (masalan, DMED) identifikator.",
        "Идентификатор во внешнем реестре (например, DMED) для будущей синхронизации.",
    ),
    "Name": ("Nomi", "Название"),
    "Contact": ("Aloqa", "Контакты"),
    "Status": ("Holat", "Статус"),
    "institution": ("muassasa", "учреждение"),
    "institutions": ("muassasalar", "учреждения"),
    "intro": ("kirish", "вступление"),
    "default section filter": ("standart boʻlim filtri", "фильтр раздела по умолчанию"),
    "Pre-selects the section filter; visitors can change it.": (
        "Boʻlim filtrini oldindan tanlaydi; tashrif buyuruvchilar oʻzgartira oladi.",
        "Предварительно выбирает фильтр раздела; посетители могут изменить.",
    ),
    "directory page (where to go)": (
        "katalog sahifasi (qayerga murojaat qilish)",
        "страница справочника (куда обратиться)",
    ),
    "term": ("atama", "термин"),
    "synonyms": ("sinonimlar", "синонимы"),
    "Comma-separated alternative spellings (e.g. Cyrillic, abbreviations).": (
        "Vergul bilan ajratilgan muqobil yozilishlar (masalan, kirillcha, qisqartmalar).",
        "Альтернативные написания через запятую (например, кириллица, сокращения).",
    ),
    "Key idea of the portal — early detection. Filled by the copywriter.": (
        "Portalning asosiy gʻoyasi — erta aniqlash. Kopirayter toʻldiradi.",
        "Ключевая идея портала — раннее выявление. Заполняет копирайтер.",
    ),
    "home emergency banner": ("bosh sahifa shoshilinch banneri", "экстренный баннер главной"),
    "Optional home-only banner (e.g. screening campaign month). The site-wide banner lives in Settings → Site settings.": (
        "Faqat bosh sahifa uchun ixtiyoriy banner (masalan, skrining oyi). Sayt boʻylab banner: Sozlamalar → Sayt sozlamalari.",
        "Необязательный баннер только для главной (например, месяц скрининга). Баннер для всего сайта: Настройки → Настройки сайта.",
    ),
    "statistics strip (3 stats)": (
        "statistika qatori (3 ta koʻrsatkich)",
        "полоса статистики (3 показателя)",
    ),
    "Hero": ("Bosh blok (hero)", "Главный блок (hero)"),
    "Featured articles": ("Tanlangan maqolalar", "Избранные статьи"),
    "Featured videos": ("Tanlangan videolar", "Избранные видео"),
    "video": ("video", "видео"),
    "featured video": ("tanlangan video", "избранное видео"),
    "Long video (doctor interview, lecture)": (
        "Uzun video (shifokor intervyusi, maʼruza)",
        "Длинное видео (интервью врача, лекция)",
    ),
    "Short vertical video (mobilograph, social media)": (
        "Qisqa vertikal video (mobilograf, ijtimoiy tarmoqlar)",
        "Короткое вертикальное видео (мобилограф, соцсети)",
    ),
    "Uploaded file": ("Yuklangan fayl", "Загруженный файл"),
    "Telegram": ("Telegram", "Telegram"),
    "Uploaded": ("Yuklangan", "Загружено"),
    "Processing": ("Qayta ishlanmoqda", "Обрабатывается"),
    "Ready": ("Tayyor", "Готово"),
    "Failed": ("Xatolik", "Ошибка"),
    "source": ("manba", "источник"),
    "video file": ("video fayl", "видеофайл"),
    "Original upload. Never served directly — transcoded renditions are.": (
        "Asl fayl. Toʻgʻridan-toʻgʻri koʻrsatilmaydi — faqat qayta kodlangan versiyalar.",
        "Исходный файл. Не отдаётся напрямую — только перекодированные версии.",
    ),
    "external URL": ("tashqi havola", "внешняя ссылка"),
    "poster image": ("poster rasmi", "постер"),
    "duration (seconds)": ("davomiyligi (soniya)", "длительность (секунды)"),
    "doctor's name": ("shifokor ismi", "имя врача"),
    "transcript": ("transkript", "расшифровка"),
    "subtitles (uz, VTT)": ("subtitrlar (uz, VTT)", "субтитры (uz, VTT)"),
    "subtitles (ru, VTT)": ("subtitrlar (ru, VTT)", "субтитры (ru, VTT)"),
    "status": ("holat", "статус"),
    "processing error": ("qayta ishlash xatosi", "ошибка обработки"),
    "Media": ("Media", "Медиа"),
    "Speaker": ("Soʻzlovchi", "Спикер"),
    "Accessibility": ("Maxsus imkoniyatlar", "Доступность"),
    "videos": ("videolar", "видео"),
    "Upload a video file or choose an external source.": (
        "Video fayl yuklang yoki tashqi manba tanlang.",
        "Загрузите видеофайл или выберите внешний источник.",
    ),
    "An external URL is required.": ("Tashqi havola kiritilishi shart.", "Нужна внешняя ссылка."),
    "The URL does not belong to the selected provider.": (
        "Havola tanlangan provayderga tegishli emas.",
        "Ссылка не относится к выбранному провайдеру.",
    ),
    "Enter a colour like #b8336a.": (
        "Rangni #b8336a koʻrinishida kiriting.",
        "Введите цвет в формате #b8336a.",
    ),
    "🎗 ribbon (women)": ("🎗 lenta (ayollar)", "🎗 лента (женщины)"),
    "🎀 ribbon (children)": ("🎀 lenta (bolalar)", "🎀 лента (дети)"),
    "tagline": ("shior", "слоган"),
    "One sentence shown on the home page card and under the section title.": (
        "Bosh sahifa kartasida va boʻlim sarlavhasi ostida koʻrsatiladigan bitta jumla.",
        "Одно предложение на карточке главной и под заголовком раздела.",
    ),
    "primary colour": ("asosiy rang", "основной цвет"),
    "Overrides the token default (--brand). Leave empty to use tokens.css.": (
        "Standart tokenni (--brand) almashtiradi. tokens.css ishlatish uchun boʻsh qoldiring.",
        "Переопределяет токен по умолчанию (--brand). Оставьте пустым, чтобы использовать tokens.css.",
    ),
    "accent colour": ("qoʻshimcha rang", "акцентный цвет"),
    "icon": ("ikonka", "иконка"),
    "Section identity": ("Boʻlim identikasi", "Идентичность раздела"),
    "section index page": ("boʻlim bosh sahifasi", "главная страница раздела"),
    "Shown on the section index card and in the mega-menu.": (
        "Boʻlim sahifasidagi kartada va mega-menyuda koʻrsatiladi.",
        "Показывается на карточке раздела и в мега-меню.",
    ),
    "topic index page": ("mavzu sahifasi", "страница темы"),
    "Download": ("Yuklab olish", "Скачать"),
    "No institutions match the selected filters yet.": (
        "Tanlangan filtrlarga mos muassasalar hozircha yoʻq.",
        "Учреждений по выбранным фильтрам пока нет.",
    ),
    "Breadcrumbs": ("Yoʻl koʻrsatkichi", "Хлебные крошки"),
    "Important": ("Muhim", "Важно"),
    "Good to know": ("Bilib qoʻying", "Полезно знать"),
    "Reassurance": ("Tinchlantirish", "Успокоение"),
    "Note": ("Eslatma", "Примечание"),
    "Loads content from a third-party site.": (
        "Tashqi saytdan kontent yuklanadi.",
        "Загружает содержимое со стороннего сайта.",
    ),
    "Open on": ("Ochish:", "Открыть в"),
    "Partners": ("Hamkorlar", "Партнёры"),
    "Free under the state programme": (
        "Davlat dasturi boʻyicha bepul",
        "Бесплатно по госпрограмме",
    ),
    "Website": ("Veb-sayt", "Сайт"),
    "Data verified": ("Maʼlumot tekshirilgan", "Данные проверены"),
    "Menu": ("Menyu", "Меню"),
    "Reviewed by a doctor": ("Shifokor tekshirgan", "Проверено врачом"),
    "Verified by a doctor": ("Shifokor tekshirgan", "Проверено врачом"),
    "Timing": ("Muddat", "Сроки"),
    "Learn more": ("Batafsil", "Подробнее"),
    "The video is being processed. Please check back later.": (
        "Video qayta ishlanmoqda. Keyinroq qayta urinib koʻring.",
        "Видео обрабатывается. Загляните позже.",
    ),
    "Filter institutions": ("Muassasalarni filtrlash", "Фильтр учреждений"),
    "All": ("Barchasi", "Все"),
    "Show": ("Koʻrsatish", "Показать"),
    "Results": ("Natijalar", "Результаты"),
    "Map will be shown here.": ("Bu yerda xarita koʻrsatiladi.", "Здесь будет карта."),
    "Key figures": ("Asosiy raqamlar", "Ключевые цифры"),
    "Topics": ("Mavzular", "Темы"),
    "Articles will appear here.": ("Maqolalar shu yerda paydo boʻladi.", "Здесь появятся статьи."),
    # M2 — search
    "qidiruv/": ("qidiruv/", "poisk/"),
    "Search the site": ("Sayt boʻylab qidirish", "Поиск по сайту"),
    "e.g. mammography": ("masalan, mammografiya", "например, маммография"),
    "In Russian": ("Rus tilida", "На русском"),
    "In Uzbek": ("Oʻzbek tilida", "На узбекском"),
    "Nothing found. Try another word, for example the name of a symptom or a test.": (
        "Hech narsa topilmadi. Boshqa soʻzni sinab koʻring, masalan, belgi yoki tekshiruv nomini.",
        "Ничего не найдено. Попробуйте другое слово, например название симптома или обследования.",
    ),
    "Type at least two characters.": (
        "Kamida ikkita belgi kiriting.",
        "Введите не менее двух символов.",
    ),
    "Search: %(q)s": ("Qidiruv: %(q)s", "Поиск: %(q)s"),
    # M3 — media & stories
    "generated sharing image": (
        "avtomatik yaratilgan ulashish rasmi",
        "сгенерированное изображение для соцсетей",
    ),
    "Rendered automatically on publish when no sharing image is chosen.": (
        "Ulashish rasmi tanlanmagan boʻlsa, eʼlon qilinganda avtomatik yaratiladi.",
        "Создаётся автоматически при публикации, если изображение не выбрано.",
    ),
    "%(label)s is too large (max %(mb)d MB).": (
        "%(label)s juda katta (maks. %(mb)d MB).",
        "%(label)s слишком большой (макс. %(mb)d МБ).",
    ),
    "%(label)s content type %(mime)s is not allowed.": (
        "%(label)s tarkib turi %(mime)s ruxsat etilmagan.",
        "%(label)s: тип содержимого %(mime)s не разрешён.",
    ),
    "Subtitle files must be WebVTT (start with 'WEBVTT').": (
        "Subtitr fayllari WebVTT boʻlishi kerak ('WEBVTT' bilan boshlanadi).",
        "Файлы субтитров должны быть WebVTT (начинаться с 'WEBVTT').",
    ),
    "stories index page": ("hikoyalar sahifasi", "страница историй"),
    "displayed name": ("koʻrsatiladigan ism", "отображаемое имя"),
    "May be a pseudonym. Never a full name without written consent.": (
        "Taxallus boʻlishi mumkin. Yozma rozilik boʻlmasa, toʻliq ism koʻrsatilmaydi.",
        "Может быть псевдонимом. Полное имя — только с письменного согласия.",
    ),
    "diagnosis (short, plain words)": (
        "tashxis (qisqa, oddiy soʻzlar bilan)",
        "диагноз (кратко, простыми словами)",
    ),
    "Written by the editor, e.g. 'breast cancer, stage 1'.": (
        "Muharrir yozadi, masalan: 'koʻkrak bezi saratoni, 1-bosqich'.",
        "Пишет редактор, например: «рак молочной железы, 1 стадия».",
    ),
    "photo": ("surat", "фото"),
    "story": ("hikoya", "история"),
    "anonymised": ("anonimlashtirilgan", "анонимизировано"),
    "Name changed and identifying details removed.": (
        "Ism oʻzgartirilgan, shaxsni aniqlovchi maʼlumotlar olib tashlangan.",
        "Имя изменено, идентифицирующие детали удалены.",
    ),
    "written consent obtained": ("yozma rozilik olingan", "письменное согласие получено"),
    "Required before publishing.": (
        "Eʼlon qilishdan oldin talab qilinadi.",
        "Требуется перед публикацией.",
    ),
    "consent of the legal guardian (minors)": (
        "qonuniy vakil roziligi (voyaga yetmaganlar)",
        "согласие законного представителя (несовершеннолетние)",
    ),
    "Required for stories in the children's section.": (
        "Bolalar boʻlimidagi hikoyalar uchun talab qilinadi.",
        "Требуется для историй в детском разделе.",
    ),
    "consent document (private)": ("rozilik hujjati (maxfiy)", "документ согласия (приватный)"),
    "Scanned consent form. Stored as a private document, never public.": (
        "Skanerlangan rozilik shakli. Maxfiy hujjat sifatida saqlanadi, hech qachon ochiq emas.",
        "Скан формы согласия. Хранится как приватный документ, никогда не публикуется.",
    ),
    "Person": ("Shaxs", "Человек"),
    "Consent (required to publish)": (
        "Rozilik (eʼlon qilish uchun shart)",
        "Согласие (обязательно для публикации)",
    ),
    "patient story": ("bemor hikoyasi", "история пациента"),
    "patient stories": ("bemorlar hikoyalari", "истории пациентов"),
    "The story cannot be published without the person's written consent.": (
        "Hikoya insonning yozma roziligisiz eʼlon qilinishi mumkin emas.",
        "Историю нельзя опубликовать без письменного согласия человека.",
    ),
    "Stories of minors require the consent of the legal guardian.": (
        "Voyaga yetmaganlar hikoyalari uchun qonuniy vakil roziligi talab qilinadi.",
        "Для историй несовершеннолетних требуется согласие законного представителя.",
    ),
    "Patient story": ("Bemor hikoyasi", "История пациента"),
    "Published with the person's consent.": (
        "Insonning roziligi bilan eʼlon qilingan.",
        "Опубликовано с согласия человека.",
    ),
    "Name and details changed.": ("Ism va tafsilotlar oʻzgartirilgan.", "Имя и детали изменены."),
    "Filter by section": ("Boʻlim boʻyicha filtrlash", "Фильтр по разделу"),
    "Stories will appear here.": ("Hikoyalar shu yerda paydo boʻladi.", "Здесь появятся истории."),
}

# msgid: (uz forms, ru forms)  — uz has 1 plural form, ru has 3
P: dict[str, tuple[list[str], list[str]]] = {
    "%(minutes)s min read": (
        ["%(minutes)s daqiqa oʻqish"],
        ["%(minutes)s минута чтения", "%(minutes)s минуты чтения", "%(minutes)s минут чтения"],
    ),
    "%(counter)s result": (
        ["%(counter)s ta natija"],
        ["%(counter)s результат", "%(counter)s результата", "%(counter)s результатов"],
    ),
    "%(counter)s institution": (
        ["%(counter)s ta muassasa"],
        ["%(counter)s учреждение", "%(counter)s учреждения", "%(counter)s учреждений"],
    ),
}


def fill(lang: str, index: int) -> int:
    path = ROOT / "locale" / lang / "LC_MESSAGES" / "django.po"
    po = polib.pofile(str(path))
    filled = 0
    for entry in po:
        if entry.obsolete or entry.translated():
            continue
        if entry.msgid_plural and entry.msgid in P:
            forms = P[entry.msgid][index]
            entry.msgstr_plural = dict(enumerate(forms))
            filled += 1
        elif entry.msgid in T:
            entry.msgstr = T[entry.msgid][index]
            filled += 1
    po.metadata["Language"] = lang
    po.save(str(path))
    return filled


if __name__ == "__main__":
    for lang, index in (("uz", 0), ("ru", 1)):
        print(f"{lang}: filled {fill(lang, index)}")

# fuzzy entries created by makemessages (wrong guesses) — overwrite with correct text
F: dict[str, tuple[str, str]] = {
    "Column title": ("Ustun sarlavhasi", "Заголовок колонки"),
    "Image": ("Rasm", "Изображение"),
    "Explanation": ("Izoh", "Пояснение"),
    "Images": ("Rasmlar", "Изображения"),
    "Document": ("Hujjat", "Документ"),
    "Description": ("Tavsif", "Описание"),
    "Question": ("Savol", "Вопрос"),
    "Questions": ("Savollar", "Вопросы"),
    "Glossary terms": ("Lugʻat atamalari", "Термины глоссария"),
    "Role / organisation": ("Lavozim / tashkilot", "Роль / организация"),
    "hero image": ("asosiy rasm", "главное изображение"),
    "article": ("maqola", "статья"),
    "articles": ("maqolalar", "статьи"),
    "regions": ("viloyatlar", "регионы"),
    "sections": ("boʻlimlar", "разделы"),
    "external source": ("tashqi manba", "внешний источник"),
    "Location": ("Joylashuv", "Расположение"),
    "Both sections": ("Ikkala boʻlim", "Оба раздела"),
    "definition": ("taʼrif", "определение"),
    "section": ("boʻlim", "раздел"),
    "glossary term": ("lugʻat atamasi", "термин глоссария"),
    "glossary terms": ("lugʻat atamalari", "термины глоссария"),
    "hero title": ("asosiy sarlavha", "главный заголовок"),
    "hero subtitle": ("asosiy sarlavha osti", "подзаголовок"),
    "additional content": ("qoʻshimcha kontent", "дополнительное содержимое"),
    "home page": ("bosh sahifa", "главная страница"),
    "featured article": ("tanlangan maqola", "избранная статья"),
    "title": ("sarlavha", "заголовок"),
    "doctor's organisation": ("shifokor tashkiloti", "организация врача"),
    "renditions": ("versiyalar", "версии"),
    "Load content": ("Kontentni yuklash", "Загрузить содержимое"),
    "Erta aniqla — home": ("Erta aniqla — bosh sahifa", "Эрта аниқла — главная"),
    "Section": ("Boʻlim", "Раздел"),
    "Open section": ("Boʻlimni ochish", "Открыть раздел"),
    "Search: %(q)s": ("Qidiruv: %(q)s", "Поиск: %(q)s"),
}


def unfuzzy(lang: str, index: int) -> int:
    path = ROOT / "locale" / lang / "LC_MESSAGES" / "django.po"
    po = polib.pofile(str(path))
    fixed = 0
    for entry in po.fuzzy_entries():
        if entry.msgid_plural and entry.msgid in P:
            entry.msgstr_plural = dict(enumerate(P[entry.msgid][index]))
        elif entry.msgid in F or entry.msgid in T:
            entry.msgstr = (F.get(entry.msgid) or T[entry.msgid])[index]
        else:
            continue
        entry.flags = [f for f in entry.flags if f != "fuzzy"]
        fixed += 1
    po.save(str(path))
    return fixed


if __name__ == "__main__":
    for lang, index in (("uz", 0), ("ru", 1)):
        print(f"{lang}: unfuzzied {unfuzzy(lang, index)}")
