# ruff: noqa: E501 — the client's text is kept verbatim, line by line
"""«Savol-javob» tab of the women's section (D-084): the questions and answers the client sent in
`docs/FAQ.docx` (2026-10-13), verbatim — medical text from the client, not written here.
One accordion per disease; every answer is one text card. Russian: translator placeholder.

The same entries feed the question page (/uz/savol-javob/) through `apps.faq.design`.
"""

from __future__ import annotations

from apps.core.seed.tree import VERIFY, Body, SeedContext, cta, p
from apps.core.seed.women_figma import RU_TODO, acc_item, accordion, heading, text_card, uz

# (category, question, answer paragraphs, page key of the «full article» link)
BREAST: list[tuple[str, str, list[str], str]] = [
    (
        "general",
        "Ko‘krak bezi saratoni nima?",
        [
            "Ko‘krak bezi saratoni – sut bezi to‘qimasi hujayralarining nazoratsiz ko‘payishi "
            "oqibatida xavfli o‘sma hosil bo‘ladigan kasallik. Bu kasallik ko‘proq ayollarda "
            "uchraydi, ammo kamdan-kam hollarda erkaklarda ham uchrashi mumkin. Ko‘krak bezi "
            "saratoni har doim ham og‘riq bilan kechmaydi, shu sababli muntazam tekshiruvlardan "
            "o‘tib turish va ko‘krakdagi o‘zgarishlarga e’tibor qaratish muhimdir. Kasallik erta "
            "aniqlansa, uni muvaffaqiyatli davolash ehtimoli yuqori bo‘ladi."
        ],
        "women.awareness.breast",
    ),
    (
        "screening",
        "Ko‘krak bezi saratoni skriningi nima uchun kerak?",
        [
            "Skrining – bu Ko‘krak bezi saratonini ilk bosqichda, hali alomatlar paydo "
            "bo‘lmasdanoq aniqlashga yordam beradigan tekshiruv. Og‘riq yoki hech qanday shikoyat "
            "bo‘lmasa ham ko‘krakni tekshiruvdan o‘tkazib turish muhim. Kasallik qanchalik erta "
            "aniqlansa, uni muvaffaqiyatli davolash imkoniyati yuqori bo‘ladi."
        ],
        "women.screening.breast",
    ),
    (
        "screening",
        "Skriningni qaysi yoshda o‘tish kerak?",
        [
            "O‘zbekiston Respublikasi Prezidentning PQ-402-son qaroriga muvofiq, 30 yoshdan 65 "
            "yoshgacha bo‘lgan ayollarning har ikki yilda bir marta skriningdan o‘tishi ko‘zda "
            "tutilgan. Birinchi bosqichda tibbiyot xodimi tomonidan ko‘rik o‘tkaziladi. 45 "
            "yoshgacha bo‘lgan ayollarda sut bezlari ultratovush tekshiruvi, 45 yoshdan 65 "
            "yoshgacha bo‘lgan ayollarda esa mammografiya yordamida tekshiriladi."
        ],
        "women.screening.breast",
    ),
    (
        "signs",
        "Qaysi belgilar ko‘krak bezi saratonidan darak berishi mumkin?",
        [
            "Agar ko‘krakda qattiqlashish (tugun), uning o‘lchami yoki shakli o‘zgarishi, ko‘krak "
            "uchi ichkariga tortilishi, teridagi o‘zgarishlar yoki ko‘krak uchidan g‘ayritabiiy, "
            "ayniqsa qonli ajralmalar kelishini sezsangiz, tezkor shifokorga murojaat qiling. "
            "Og‘riq bo‘lmasligi mumkin, shuning uchun og‘riqning yo‘qligi hammasi joyida degani "
            "emas.",
            "<b>BU MUHIM:</b> qattiqlashish har doim ham saratonni anglatmaydi – sababini shifokor "
            "aniqlashi kerak.",
        ],
        "women.awareness.breast",
    ),
    (
        "screening",
        "Agar tekshiruv saratonga shubha borligini ko‘rsatsa, keyin nima qilish kerak?",
        [
            "Sarosimaga tushmang, ammo keyingi tekshiruvlarni ham kechiktirmang. Skrining natijasi "
            "hali sizda saraton bor degani emas. Shifokor qo‘shimcha tekshiruvlar, masalan, UTT, "
            "mammografiya yoki biopsiya – tahlil uchun kichik to‘qima namunasini olishni tayinlashi "
            "mumkin. Aynan to‘qimani tekshirish tashxisni tasdiqlash yoki inkor etish imkonini "
            "beradi."
        ],
        "women.treatment.breast",
    ),
    (
        "treatment",
        "Ko‘krak bezi saratonini davolash mumkinmi va ko‘krakni olib tashlash shartmi?",
        [
            "Ha, ko‘krak bezi saratonini davolash mumkin, kasallik erta aniqlanganda muvaffaqiyatli "
            "davolanish imkoniyati oshadi. Davolash usuli o‘sma turiga va kasallik bosqichiga "
            "bog‘liq. Ayrim hollarda ko‘krakning katta qismini saqlab qolgan holda faqat o‘smani "
            "olib tashlash kifoya qilsa, boshqa hollarda butun ko‘krak bezini olib tashlash talab "
            "etiladi. Shuningdek, dori-darmon terapiyasi va nur terapiyasi ham qo‘llanilishi "
            "mumkin. Davolash rejasini shifokor har bir bemor uchun individual tarzda belgilaydi."
        ],
        "women.treatment.breast",
    ),
]

CERVICAL: list[tuple[str, str, list[str], str]] = [
    (
        "general",
        "Bachadon bo‘yni saratoni nima?",
        [
            "Bachadon bo‘yni saratoni – bu bachadon bo‘yni hujayralarining nazoratsiz ko‘payishi "
            "natijasida xavfli o‘sma hosil bo‘ladigan kasallik. Aksariyat hollarda bu kasallik odam "
            "papilloma virusi (OPV) organizmda uzoq vaqt saqlanib qolishi bilan bog‘liq bo‘ladi. "
            "Bachadon bo‘yni saratoni asta-sekin rivojlanishi mumkin, shu sababli muntazam "
            "tekshiruvlar xavfli o‘zgarishlar paydo bo‘lmasdanoq aniqlashga yordam beradi."
        ],
        "women.awareness.cervical",
    ),
    (
        "screening",
        "Bachadon bo‘yni saratoni skriningi nima uchun kerak?",
        [
            "Skrining – bu saratonoldi o‘zgarishlarini yoki kasallik belgilarini alomatlar paydo "
            "bo‘lishidan oldin aniqlashga yordam beradigan tekshiruv. U o‘zgarishlarni erta "
            "bosqichda aniqlash va davolashni o‘z vaqtida boshlash imkonini beradi. Ayol o‘zini "
            "yaxshi his qilsa va unda hech qanday shikoyatlar bo‘lmasa ham, shifokor tavsiyalariga "
            "muvofiq tekshiruvdan o‘tib turishi muhimdir."
        ],
        "women.screening.cervical",
    ),
    (
        "screening",
        "Skriningdan o‘tish kimlarga tavsiya qilinadi?",
        [
            "O‘zbekiston Respublikasi Prezidentining 2024-yil 22-noyabrdagi PQ-402-son qaroriga "
            "muvofiq, 30 yoshdan 65 yoshgacha bo‘lgan ayollarni har ikki yilda bir marta "
            "tekshiruvdan o‘tkazish ko‘zda tutilgan. Bachadon bo‘ynidagi o‘zgarishlarni aniqlash "
            "uchun maxsus tekshiruv, jumladan, belgilangan tartibda OPV (odam papillomavirusi) "
            "testi o‘tkaziladi. Tekshiruv joyi va muddatlarini oilaviy poliklinikadan aniqlash "
            "mumkin."
        ],
        "women.screening.cervical",
    ),
    (
        "signs",
        "Qanday belgilar bachadon bo‘yni saratonidan darak berishi mumkin?",
        [
            "Jinsiy aloqadan keyingi qonli ajralmalar, hayz sikllari oralig‘idagi yoki "
            "menopauzadan keyingi qon ketishlar, shuningdek, noodatiy ajralmalar ehtimoliy "
            "muammolarga ishora qilishi mumkin. Qorinning pastki qismidagi og‘riq turli "
            "kasalliklarda yuzaga kelishi mumkin va bu o‘z-o‘zidan saraton belgisi degani emas. "
            "Ilk bosqichlarda bachadon bo‘yni saratoni ko‘pincha alomatlarsiz kechadi, shu sababli "
            "hech narsa bezovta qilmagan taqdirda ham skriningdan o‘tish muhim."
        ],
        "women.awareness.cervical",
    ),
    (
        "screening",
        "Agar tekshiruv shubhali natija ko‘rsatsa, nima qilish kerak?",
        [
            "Vahimaga tushmang: OPV bo‘yicha musbat test yoki skrining natijasidagi o‘zgarishlar "
            "sizda saraton bor degani emas. Shifokor qo‘shimcha tekshiruvlarni, masalan, "
            "kolposkopiya – bachadon bo‘ynini kattalashtirib ko‘rish, yoki tahlil uchun to‘qimaning "
            "kichik namunasi olinadigan biopsiyani tayinlashi mumkin. Tekshiruv natijalariga ko‘ra "
            "shifokor davolanish zarur yoki yo‘qligini va aynan qanday muolaja kerakligini "
            "belgilaydi."
        ],
        "women.treatment.cervical",
    ),
    (
        "treatment",
        "Bachadon bo‘yni saratonini davolash mumkinmi?",
        [
            "Ha, bachadon bo‘yni saratoni davolanadi, ayniqsa u erta bosqichda aniqlangan bo‘lsa. "
            "Kasallik bosqichiga qarab jarrohlik amaliyoti, nur terapiyasi va dori-darmonlar bilan "
            "davolash usullari qo‘llanishi mumkin. Saraton rivojlanish xavfini kamaytirish uchun "
            "saratonoldi o‘zgarishlarini ham davolash mumkin. Kasallik qanchalik erta aniqlansa, "
            "uni muvaffaqiyatli davolash imkoniyati shunchalik yuqori bo‘ladi."
        ],
        "women.treatment.cervical",
    ),
    (
        "general",
        "Emlash orqali bachadon bo‘yni saratonidan himoyalanish mumkinmi?",
        [
            "Ha. Odam papillomavirusiga (OPV) qarshi emlash bachadon bo‘yni saratonini eng ko‘p "
            "keltirib chiqaradigan virus turlaridan himoyalanishga yordam beradi. O‘zbekistonda "
            "OPVga qarshi emlash 9 yoshli qizlar uchun milliy profilaktik emlashlar taqvimiga "
            "kiritilgan. Emlash virus bilan to‘qnash kelgunga qadar eng yuqori samara beradi. Shu "
            "bilan birga, emlash skrining o‘rnini bosmaydi: ayollarning yoshiga va shifokor "
            "tavsiyalariga muvofiq tekshiruvlardan o‘tib turishi muhim."
        ],
        "women.awareness.cervical",
    ),
]

# the Word file writes oʻ / gʻ with U+2018 and the apostrophe with U+2019: uz() turns them into
# the site's spelling (oʻ U+02BB, ʼ U+02BC), once, for the pages and the question page alike
Entry = tuple[str, str, list[str], str]


def _normalise(rows: list[Entry]) -> list[Entry]:
    return [(c, uz(q), [uz(a) for a in answers], key) for c, q, answers, key in rows]


BREAST = _normalise(BREAST)
CERVICAL = _normalise(CERVICAL)
TOPICS = {"breast": BREAST, "cervical": CERVICAL}


def _body(entries: list[tuple[str, str, list[str], str]], lang: str, ctx: SeedContext) -> Body:
    ask = cta(
        "Javob topmadingizmi? Savolingizni shifokorga yuboring." if lang == "uz" else RU_TODO,
        "Savol berish" if lang == "uz" else "Задать вопрос",
        ctx.page_id("faq", lang),
    )
    if lang != "uz":
        return [heading("Вопросы и ответы"), text_card(p(RU_TODO) + p(VERIFY)), ask]
    items = [
        acc_item(question, f"savol-{number}", [text_card(p(*answer))])
        for number, (_category, question, answer, _key) in enumerate(entries, start=1)
    ]
    return [heading("Savol-javob"), accordion(items), ask]


def body_breast_faq(lang: str, ctx: SeedContext) -> Body:
    return _body(BREAST, lang, ctx)


def body_cervical_faq(lang: str, ctx: SeedContext) -> Body:
    return _body(CERVICAL, lang, ctx)


def entries() -> list[tuple[str, str, str, list[str], str]]:
    """(topic, category, question, answer paragraphs, page key) for the question page."""
    return [(topic, *entry) for topic, rows in TOPICS.items() for entry in rows]
