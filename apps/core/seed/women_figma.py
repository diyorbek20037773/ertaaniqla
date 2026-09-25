"""Women's section content from the designer's Figma file (M5d, DECISIONS D-064…D-068).

The Uzbek copy is the client's text as laid out in Figma «Erta aniqla» (frames 2408:194 …
2408:2489); breast-cancer «Xabardorlik» was read from the Figma layers, the other pages from the
PNG exports. It is medical content the developer did not write, so every page carries
`[[VERIFY: doctor]]` and stays unverified until the Medical review workflow approves it (D-041).
Figma has no Russian copy: Russian pages get translated headings and a translation placeholder
(D-068) instead of an unreviewed machine translation of medical text.
Where a Figma frame repeats another page's text by mistake (cervical «Sabablari» cards copied
from the breast page) the cards keep their design but get a copywriter placeholder.
"""

from __future__ import annotations

import re
from typing import Any

from apps.core.seed.tree import (
    TODO,
    VERIFY,
    Body,
    SeedContext,
    callout,
    cta,
    p,
    rich,
    t,
    todo_callout,
    ul,
)

RU_TODO = "[[TODO: перевод с узбекского — копирайтер]]"
_APOS = re.compile(r"(?<=[oOgG])['’`‘]|['’`‘]")


def uz(text: str) -> str:
    """Normalise Uzbek Latin apostrophes: oʻ/gʻ take U+02BB, every other one U+02BC."""
    return _APOS.sub(lambda m: "ʻ" if m.start() and text[m.start() - 1] in "oOgG" else "ʼ", text)


# ---------------------------------------------------------------------------------------------
# design blocks (JSON form of the StreamField values)
# ---------------------------------------------------------------------------------------------
def heading(text: str) -> dict[str, Any]:
    return {"type": "heading", "value": text}


def card(
    text_html: str,
    title: str = "",
    label: str = "",
    illustration: str = "",
    width: str = "full",
) -> dict[str, Any]:
    return {
        "label": label,
        "title": title,
        "text": text_html,
        "image": None,
        "illustration": illustration,
        "width": width,
    }


def text_card(text_html: str, **kwargs: str) -> dict[str, Any]:
    return {"type": "text_card", "value": card(text_html, **kwargs)}


def text_cards(cards: list[dict[str, Any]], columns: str = "2") -> dict[str, Any]:
    return {"type": "text_cards", "value": {"columns": columns, "cards": cards}}


def capsules(items: list[tuple[str, str, str]], arrows: bool = True) -> dict[str, Any]:
    """items: (number, title, text html)."""
    return {
        "type": "steps",
        "value": {
            "title": "",
            "layout": "capsules_arrows" if arrows else "capsules",
            "steps": [
                {
                    "number": number,
                    "title": title,
                    "text": text,
                    "deadline": "",
                    "link": {"page": None, "url": ""},
                }
                for number, title, text in items
            ],
        },
    }


def icon_tiles(items: list[tuple[str, str, str]]) -> dict[str, Any]:
    """items: (icon name from apps.articles.illustrations, title, text)."""
    return {
        "type": "cards_grid",
        "value": {
            "title": "",
            "layout": "icon_tiles",
            "cards": [
                {
                    "image": None,
                    "icon": icon,
                    "title": title,
                    "text": p(text),
                    "link": {"page": None, "url": ""},
                }
                for icon, title, text in items
            ],
        },
    }


def alert(text: str) -> dict[str, Any]:
    return callout("alert", "", p(text))


def appeal(lang: str, ctx: SeedContext) -> dict[str, Any]:
    """The design's closing «Murojaat qilish» pill → the «where to go» directory (D-064)."""
    return cta("", t(lang, "Murojaat qilish", "Обратиться"), ctx.page_id("women.directory", lang))


def verify_note(lang: str) -> dict[str, Any]:
    note = t(
        lang,
        "Matn buyurtmachining Figma maketidan olingan va shifokor tekshiruvini kutmoqda.",
        "Текст взят из макета заказчика и ожидает проверки врачом.",
    )
    return rich(p(f"<i>{note} {VERIFY}</i>"))


# ---------------------------------------------------------------------------------------------
# «Xabardorlik» — breast cancer (Figma 2408:194, text from the layers)
# ---------------------------------------------------------------------------------------------
DONT_PANIC = uz(
    "Agar siz shu kabi o'zgarishlardan birortasini sezsangiz — vahima qilmang, lekin shifokorga "
    "borishni kechiktirmang. Erta tashxis — to'liq sog'ayish imkoniyati demakdir."
)


def body_breast_awareness(lang: str, ctx: SeedContext) -> Body:
    if lang != "uz":
        body = _ru_skeleton(
            lang,
            ctx,
            [
                "Что такое рак молочной железы?",
                "Стадии рака молочной железы",
                "Причины рака молочной железы",
                "Признаки рака молочной железы",
                "Осмотр у врача",
                "Самообследование груди",
            ],
        )
        return [*body[:-1], todo_callout(lang, TZ_AWARENESS_UZ, TZ_AWARENESS_RU), body[-1]]
    stages = [
        (
            "0",
            "",
            p(
                uz(
                    "invaziv bo'lmagan ko'krak saratoni (karsinoma in situ) – sut bezi kanallarini "
                    "o'rab turgan to'qimalariga tarqalmagan bo'ladi. Invaziv bo'lmagan ko'krak "
                    "saratoni odatda mammografiya paytida aniqlanadi va kamdan-kam hollarda "
                    "ko'krakdagi qattiqlik shaklida namoyon bo'ladi."
                )
            ),
        ),
        (
            "1",
            "",
            p(
                uz(
                    "invaziv bo'lmagan ko'krak saratoni. Saraton o'simta yaqinida joylashgan "
                    "to'qimalarga ta'sir qiladi. O'simtaning kattaligi 2 sm dan oshmaydi. Limfa "
                    "bezlari normal holatda bo'ladi."
                )
            ),
        ),
        (
            "2",
            "",
            p(
                uz(
                    "invaziv saraton. Saraton hujayralari kanallarning qoplamasi orqali atrofdagi "
                    "ko'krak to'qimalariga tarqaladi. O'simtaning diametri 2 dan 5 sm gacha, "
                    "qo'ltiq ostidagi limfa tugunlari o'simta tomonidan zararlanadi. Bu ko'krak "
                    "saratonining eng keng tarqalgan turi hisoblanadi."
                )
            ),
        ),
        (
            "3",
            "",
            p(
                uz(
                    "A bosqich. O'simtaning diametri 5 sm dan ortiq bo'lib, limfa tugunlari juda "
                    "kattalashgan. Ular bir-biriga va atrofdagi to'qimalarga yopishgan bo'ladi."
                )
            ),
        ),
        (
            "3",
            "",
            p(
                uz(
                    "B bosqich. Ushbu turga yallig'lanish saratoni, infiltrativ kanal saratoni "
                    "kiradi. 3-bosqichning xarakterli belgilari terining qizarishi, apelsin "
                    "terining paydo bo'lishidir. O'simta har xil hajmda bo'lishi mumkin. Bu "
                    "bosqichda ko'krak terisi, ichki ko'krak limfa tugunlari yoki ko'krak devori "
                    "zararlanadi."
                )
            ),
        ),
        (
            "4",
            "",
            p(
                uz(
                    "O'simta ichki limfa tugunlariga ta'sir qiladi, qo'ltiq ostigacha yetib boradi "
                    "va o'mrov, limfa tugunlari, jigar, o'pka va miya ham ta'sirlanadi. 4-bosqich "
                    "saratoni tashxisi ko'pincha BRCA-1 va BRCA-2 genlaridagi mutatsiyaga ega "
                    "bo'lgan ayollarga qo'yiladi."
                )
            ),
        ),
    ]
    causes = [
        (
            "women",
            "Ayollar",
            "Erkaklarga qaraganda ko'krak bezi saratoni bilan kasallanish ehtimoli ko'proq",
        ),
        (
            "age",
            "Ulg'aygan yosh",
            "Ko'krak bezi saratoni xavfi yoshga qarab ortadi (ko'pincha 35 yoshdan keyin)",
        ),
        (
            "breast-disease",
            "Ko'krak kasalliklari",
            "Shaxsiy anamnezda ko'krak kasalligi bilan og'rish (lobulyar karsinoma in situ, atipik "
            "ko'krak giperplaziyasini aniqlaydigan ko'krak biopsiyasi)",
        ),
        (
            "other-disease",
            "Boshqa kasalliklar",
            "Bepushtlik, jinsiy a'zolarning yallig'lanishi, laktatsiyaning buzilishi",
        ),
        (
            "genes",
            "Irsiy genlar",
            "Ko'krak saratoni xavfini oshiradigan ba'zi gen mutatsiyalari ota-onadan bolaga o'tishi "
            "mumkin. Eng ko'p uchraydigan gen mutatsiyalari BRCA1 va BRCA2.",
        ),
        (
            "radiation",
            "Radiatsiya ta'siri",
            "Agar siz bolaligingiz yoki yoshligingizda ko'krak qafasidagi nur terapiyasini olgan "
            "bo'lsangiz, ko'krak saratoni xavfi ortadi.",
        ),
        (
            "chronic",
            "Boshqa kasalliklar",
            "Qandli diabet, semizlik, ateroskleroz, immunitet tanqisligi",
        ),
        (
            "late-birth",
            "Kech tug'ish",
            "Birinchi farzandini 30 yoshdan keyin dunyoga keltirgan ayollarda ko'krak bezi saratoni "
            "xavfi ortishi mumkin",
        ),
        (
            "hormone",
            "Gormon terapiyasi",
            "Klimaks belgilari va alomatlarini davolash uchun estrogen va progesteronni "
            "birlashtirgan gormon terapiyasi dori-darmonlarini qabul qilish",
        ),
        ("habits", "Zararli odatlar", "spirtli ichimliklar ichish, zaharlanish, chekish"),
    ]
    signs = [
        card(
            p(
                uz(
                    "Ko'pchilik hollarda bu o'sma yaxshi sifatli bo'ladi, lekin ba'zi belgilar saraton ehtimolini oshiradi:"
                )
            )
            + ul(
                [
                    uz("o'sma juda zich, “toshdek qattiq”;"),
                    uz("teri ostida yomon siljiydi;"),
                    uz("qirralari notekis, g'adir-budir;"),
                    uz("odatda og'riqsiz."),
                ]
            )
            + p(
                "<i>"
                + uz(
                    "Ba'zan o'smani qo'l bilan sezish mumkin, hatto mammografiya uni ko'rsatmasa "
                    "ham. Shu sababli har qanday tekshiruvdan oldin shifokor ko'rigi zarur."
                )
                + "</i>"
            ),
            title=uz("Ko'krakdagi qattiqlik yoki “shish” paydo bo'lishi"),
        ),
        card(
            p(
                uz(
                    "Saraton faqat o'sma bilan emas, balki ko'krak terisi o'zgarishlari bilan ham namoyon bo'lishi mumkin:"
                )
            )
            + ul(
                [
                    uz("qizarish yoki sababsiz ko'karish;"),
                    uz("shish, terining qalinlashishi yoki zichlashishi;"),
                    uz("terining yoki so'rg'ichning tortilishi (ichkariga kirib ketishi);"),
                    uz("quruqlik, toshma, tuzalmas yaralar;"),
                    uz("so'rg'ich yoki areola sohasida yara yoki ekzema."),
                ]
            )
            + p("<i>" + uz("Bu belgilar o'sma teriga yaqin joylashganda paydo bo'ladi.") + "</i>"),
            title=uz("Teri o'zgarishlari"),
        ),
        card(
            p(
                uz(
                    "Ajralmalar har doim ham saratonni anglatmaydi. Ko'pincha ular yaxshi sifatli "
                    "o'zgarishlar — papilloma, yallig'lanish yoki vaqtinchalik holatlardir. Ammo "
                    "quyidagi belgilar bo'lsa, ehtiyot bo'lish kerak:"
                )
            )
            + ul(
                [
                    uz("ajralmalar o'z-o'zidan, bosmasdan paydo bo'ladi;"),
                    uz("faqat bitta so'rg'ichdan chiqadi;"),
                    uz("faqat bitta nuqtadan (bitta kanal) tomchi ajraladi;"),
                    uz("ajralmalar qon aralash bo'ladi."),
                ]
            )
            + p(
                "<i>"
                + uz("Bunday hollarda shifokorga murojaat qilib, tekshiruvdan o'tish lozim.")
                + "</i>"
            ),
            title=uz("So'rg'ichdan ajralmalar"),
        ),
        card(
            p(
                uz(
                    "Saraton qo'ltiq osti, o'mrov usti yoki osti limfa tugunlarining kattalashuvi "
                    "bilan ham namoyon bo'lishi mumkin."
                )
            )
            + p(
                uz(
                    "Odatda bu tugunlar bilinmaydi, lekin kasallikda ular kattalashib, harakatda "
                    "noqulaylik yoki shish hissini keltirib chiqaradi."
                )
            )
            + p(
                uz(
                    "Har doim ham limfa tugunining kattalashishi saraton belgisi emas — bu "
                    "infektsiyaga javob bo'lishi ham mumkin. Aniqlik kiritish uchun biopsiya "
                    "o'tkaziladi: shifokor to'qimadan kichik namunani olib, laboratoriyada tekshiradi."
                )
            ),
            title=uz("Limfa tugunlaridagi belgilar"),
        ),
    ]
    self_exam = [
        card(
            p(
                uz(
                    "Avval oynaga qarab, qo'llaringizni pastga tushirib turing. Ko'krak shakliga, simmetriyasiga, teri va so'rg'ich holatiga e'tibor bering."
                )
            ),
            title="1-bosqich",
            illustration="selfexam-1",
        ),
        card(
            p(
                uz(
                    "So'ng qo'llaringizni bosh orqasiga qo'yib, yana ko'kragingizni ko'rib chiqing. Ko'krak shakliga, simmetriyasiga, teri va so'rg'ich holatiga e'tibor bering."
                )
            ),
            title="2-bosqich",
            illustration="selfexam-2",
        ),
        card(
            p(
                uz(
                    "Paypaslab tekshirish. Eng qulay holat — yotgan holda, chunki bu paytda ko'krak "
                    "to'qimasi bir tekis tarqaladi va teri tuzilishini yaxshiroq sezish mumkin. "
                    "Tekshiruvni dushda, qo'l va ko'krak terisini sovunlab, barmoqlarni osonroq "
                    "harakatlantirish uchun ham bajarish mumkin. Barmoqlaringiz uchlari bilan "
                    "yumshoq bosib, ko'krakning barcha qismlarini birma-bir tekshiring. Buni "
                    "yuqoridan pastga, aylana shaklida yoki markazdan tashqariga qarab amalga "
                    "oshirish mumkin — go'yo ko'krakni bir nechta sektorlarga bo'layotgandek."
                )
            ),
            title="3-bosqich",
            illustration="selfexam-3",
        ),
        card(
            p(
                uz(
                    "Shundan so'ng ehtiyotlik bilan so'rg'ichni bosing va suyuqlik bor yoki yo'qligini tekshirib ko'ring. Keyin qo'ltiq osti sohasini paypaslab chiqing."
                )
            )
            + p(
                uz(
                    "O'z-o'zini tekshirish professional skrining o'rnini bosa olmaydi, lekin o'z "
                    "tanangizni yaxshiroq bilishga yordam beradi. Agar siz o'z tanangizning normal "
                    "holatini bilsangiz, har qanday o'zgarishni erta payqaysiz va o'z vaqtida "
                    "shifokorga murojaat qilasiz."
                )
            ),
            title="4-bosqich",
            illustration="selfexam-4",
        ),
    ]
    return [
        heading(uz("Ko'krak bezi saratoni nima?")),
        text_card(
            p(
                uz(
                    "Ko'krak bezi saratoni (KBS) – ayollar orasida eng ko'p uchraydigan onkologik "
                    "kasallikdir. KBS bu – ko'krak hujayralarining saraton hujayralariga aylanishi "
                    "natijasida yuzaga keladigan kasallik. Ko'krak saratoni o'pka saratonidan keyin "
                    "ikkinchi eng keng tarqalgan saraton turi bo'lib, ayollar orasida birinchi "
                    "o'rinda turadi. JSST ma'lumotlariga ko'ra, har yili 1,5 million ayolga ko'krak "
                    "bezi saratoni tashxisi qo'yiladi. Ushbu kasallik 13 yoshdan 90 yoshgacha "
                    "bo'lgan ayollarning taxminan 10 foizida uchraydi. Erkaklar ushbu kasallikka "
                    "kamroq chalinadilar (1%). Kasallikdan o'lim holatlari taxminan 50% ni tashkil "
                    "qiladi."
                )
            )
            + p(
                uz(
                    "Saraton o'simtasi xavfsiz o'smadan farqli o'laroq tezroq o'sadi va metastaz "
                    "yo'li bilan boshqa organlarga juda faol tarqaladi hamda limfa tugunlariga ham "
                    "ta'sir qiladi."
                )
            )
        ),
        uz_statistics(),
        heading(uz("Ko'krak bezi saratoni bosqichlari")),
        capsules(stages),
        heading(uz("Ko'krak bezi saratoni sabablari")),
        icon_tiles([(icon, uz(title), uz(text)) for icon, title, text in causes]),
        heading(uz("Ko'krak bezi saratoni belgilari")),
        text_cards(signs),
        alert(DONT_PANIC),
        appeal(lang, ctx),
        heading(uz("Shifokor ko'rigi")),
        text_card(
            p(
                uz(
                    "Qabul vaqtida shifokor (ginekolog, mammolog yoki onkolog) sizdan quyidagilar "
                    "haqida so'raydi: yaqin qarindoshlaringizda ko'krak bezi saratoni bo'lganmi, "
                    "hayz qachon boshlangan va tugagan, oxirgi hayz qachon bo'lgan, homiladorlik va "
                    "emizish qanday o'tgan, hozirda qanday dori vositalari qabul qilinmoqda. Bu "
                    "ma'lumotlar shifokorga xavf omillarini baholashda yordam beradi."
                )
            )
            + p(
                uz(
                    "Agar siz ko'kragingizda o'zgarishlarni sezsangiz, bu haqda shifokorga albatta "
                    "xabar bering. Ayniqsa, bu o'zgarishlar hayz davri bilan bog'liqligini, ya'ni "
                    "ma'lum kunlarda kuchayishi yoki o'tib ketishini aniqlashtirish muhim."
                )
            )
            + p(
                uz(
                    "Ko'rik vaqtida shifokor ko'krakni va qo'ltiq osti sohasini diqqat bilan ko'zdan "
                    "kechiradi va paypaslab tekshiradi. Kattalashgan limfa tugunlari yallig'lanish "
                    "yoki o'smaning tarqalganini ko'rsatishi mumkin va qo'shimcha tekshiruvni talab "
                    "qiladi."
                )
            )
            + p(
                uz(
                    "Aniqroq natijaga erishish uchun shifokor sizdan turish, o'tirish yoki yotish "
                    "holatida bo'lishingizni so'rashi mumkin. Agar tekshiruv paytida og'riq yoki "
                    "noqulaylik sezsangiz, bu haqida darhol shifokorga ayting."
                )
            )
        ),
        heading(uz("Ko'krakni o'z-o'zini tekshirish")),
        text_card(
            p("<b>" + uz("O'z-o'zini tekshirish kerakmi?") + "</b>")
            + p(
                uz(
                    "O'z-o'zini tekshirish ko'krak bezi saratonini erta aniqlash usuli "
                    "hisoblanmaydi. Shunga qaramay, bu usul foydali bo'lishi mumkin: u sizga "
                    "ko'kragingizning holatini yaxshiroq bilishga va o'zgarishlarni erta payqashga "
                    "yordam beradi."
                )
            )
        ),
        text_card(
            p("<b>" + uz("O'z-o'zini tekshirishni qanday bajarish kerak?") + "</b>")
            + p(
                uz(
                    "Ko'krak to'qimasi hayz sikli bosqichlariga qarab o'zgaradi, shuning uchun eng "
                    "qulay vaqt hayz boshlanganidan 5–7 kundan keyingi kun hisoblanadi. "
                    "Menopauzadagi ayollar har oyda bir xil sanani tanlab, shu kuni tekshiruvni "
                    "o'tkazishlari tavsiya etiladi."
                )
            )
        ),
        text_cards(self_exam),
        text_card(
            p(
                uz(
                    "Agar o'z-o'zini tekshirish vaqtida quyidagi o'zgarishlardan birini sezsangiz, "
                    "shifokorga murojaat qilishni kechiktirmang:"
                )
            )
            + ul(
                [
                    uz("ko'krak shakli yoki hajmining o'zgarishi;"),
                    uz("qattiqlik yoki shish paydo bo'lishi;"),
                    uz("teri holatining o'zgarishi — ichkariga tortilish, qizarish, quruqlashish;"),
                    uz("so'rg'ichning tortilishi yoki joyining o'zgarishi;"),
                    uz("so'rg'ichdan suyuqlik chiqishi."),
                ]
            ),
            title=uz("Qachon shifokorga murojaat qilish kerak?"),
            width="narrow",
        ),
        alert(DONT_PANIC),
        appeal(lang, ctx),
        verify_note(lang),
    ]


# ---------------------------------------------------------------------------------------------
# Russian skeleton: same rhythm, translated headings, translation placeholder (D-068)
# ---------------------------------------------------------------------------------------------
# TZ «Осведомленность» (what / risk / symptoms), verbatim — kept on the awareness pages (D-068)
TZ_AWARENESS_RU = [
    "что происходит в организме",
    "стадии",
    "статистика по Узбекистану",
    "Возраст",
    "Наследственность",
    "Образ жизни",
    "ВПЧ-инфекция",
    "Другие факторы, о которых важно знать",
    "Самообследование груди — пошаговое руководство",
    "Признаки, которые нельзя игнорировать; этот признак не всегда означает рак",
]
TZ_AWARENESS_UZ = [
    "organizmda nima sodir boʻladi",
    "kasallik bosqichlari",
    "Oʻzbekiston boʻyicha statistika",
    "Yosh",
    "Irsiyat",
    "Turmush tarzi",
    "HPV infeksiyasi",
    "Bilish muhim boʻlgan boshqa omillar",
    "Koʻkrakni mustaqil tekshirish — bosqichma-bosqich qoʻllanma",
    "Eʼtiborsiz qoldirib boʻlmaydigan belgilar; bu belgi har doim saraton degani emas",
]


def uz_statistics() -> dict[str, Any]:
    """TZ «статистика по Узбекистану» — no Figma layer carries it; a card for the copywriter."""
    return text_card(p(f"{TODO} {VERIFY}"), title=uz("O'zbekiston bo'yicha statistika"))


def _ru_skeleton(lang: str, ctx: SeedContext, headings: list[str]) -> Body:
    body: Body = []
    for title in headings:
        body.append(heading(title))
        body.append(text_card(p(RU_TODO) + p(VERIFY)))
    body.append(appeal(lang, ctx))
    return body


# ---------------------------------------------------------------------------------------------
# «Xabardorlik» — cervical cancer (Figma 2408:2489, from the PNG export)
# ---------------------------------------------------------------------------------------------
def _lines(*lines: str) -> str:
    return "".join(p(uz(line)) for line in lines)


def body_cervical_awareness(lang: str, ctx: SeedContext) -> Body:
    if lang != "uz":
        body = _ru_skeleton(
            lang,
            ctx,
            [
                "Что такое рак шейки матки?",
                "Формы рака шейки матки",
                "Стадии рака шейки матки",
                "Причины рака шейки матки",
            ],
        )
        return [*body[:-1], todo_callout(lang, TZ_AWARENESS_UZ, TZ_AWARENESS_RU), body[-1]]
    forms = [
        (
            "1",
            uz("YASSI EPITELIYDAN RIVOJLANGAN O'SIMTALAR"),
            ul(
                [
                    uz("HPV bilan bog'liq yassi hujayrali saraton;"),
                    uz("HPV bilan bog'liq bo'lmagan yassi hujayrali saraton;"),
                    uz("Noaniq (nonspetsifik) yassi hujayrali saraton."),
                ]
            ),
        ),
        (
            "2",
            uz("BEZI JIGARRANG EPITELIYDAN RIVOJLANGAN O'SIMTALAR"),
            ul(
                [
                    uz("HPV bilan bog'liq adenokarsinoma;"),
                    uz(
                        "HPV bilan bog'liq bo'lmagan adenokarsinoma (oshqozon, yorug' hujayrali, mezonefrik turlari);"
                    ),
                    uz("Endometrioid adenokarsinoma;"),
                    uz("Karsinosarkoma."),
                ]
            ),
        ),
        (
            "3",
            uz("NOYOB SHAKLLAR"),
            ul(
                [
                    uz("Aralash epitelial va mezenximal o'simtalar;"),
                    uz("Germinogen o'simtalar;"),
                    uz("Neyroendokrin o'simtalar."),
                ]
            ),
        ),
    ]
    grades = [
        (
            "1",
            uz("PAST MALIGNLIK"),
            p("<i>" + uz("Hujayralar sog'lom hujayralarga o'xshaydi, o'sish sekin;") + "</i>"),
        ),
        ("2", uz("O'RTACHA"), p("<i>" + uz("o'rtacha farq, o'sish tezlashgan;") + "</i>")),
        (
            "3",
            uz("YUQORI MALIGNLIK"),
            p("<i>" + uz("hujayralar keskin o'zgargan, o'sma tez o'sadi va tarqaladi.") + "</i>"),
        ),
    ]
    stages = [
        (
            "1",
            "",
            _lines(
                "40% ayollarda shu bosqichda aniqlanadi. O'simta bachadon bo'yni ichida joylashgan.",
                "IA — saraton faqat mikroskop ostida aniqlanadi, o'simta chuqurligi 5 mm dan oshmaydi:",
                "IA1 — 3 mm gacha",
                "IA2 — 3–5 mm",
                "IB — chuqurligi 5 mm dan ortiq:",
                "IB1 — 2 sm gacha",
                "IB2 — 2–4 sm",
                "IB3 — 4 sm dan katta",
            ),
        ),
        (
            "2",
            "",
            _lines(
                "20% bemorlarda aniqlanadi. O'simta bachadon bo'ynidan tashqariga chiqqan, ammo tos "
                "devorlariga yoki qinning pastki uchdan bir qismiga yetmagan bo'ladi.",
                "IIA — o'simta qinning yuqori ikki uchdan bir qismini qamrab oladi,",
                "IIA1 — 4 sm gacha",
                "IIA2 — 4 sm dan katta",
                "IIB — o'simta bachadon atrofidagi parametriyga tarqalgan, lekin tos devorlariga yetmagan.",
            ),
        ),
        (
            "3",
            "",
            _lines(
                "30% holatlarda uchraydi. O'simta qinning pastki qismini, tos devorlarini va/yoki "
                "limfa tugunlarini zararlaydi.",
                "IIIA — faqat qinning pastki uchdan bir qismi zararlangan",
                "IIIB — o'simta tos devorlariga tarqalgan yoki siydik yo'lini bosib, buyrakda "
                "gidronefroz chaqirgan",
                "IIIC — o'simta limfa tugunlariga metastaz bergan, o'lchamidan qat'i nazar:",
                "IIIC1 — faqat tos limfa tugunlari zararlangan",
                "IIIC2 — paraaortal limfa tugunlari zararlangan",
            ),
        ),
        (
            "4",
            "",
            _lines(
                "Eng og'ir bosqich bo'lib, taxminan 10% ayollarda aniqlanadi.",
                "IVA — o'simta siydik pufagi, to'g'ri ichak yoki boshqa yaqin organlarga o'tgan",
                "IVB — metastazlar uzoq joylarga — qo'ltiqosti, bo'yin usti limfa tugunlariga, "
                "o'pka, jigar yoki suyaklarga tarqalgan",
            ),
        ),
    ]
    # Figma repeats the breast-cancer cards here by mistake; the TZ risk factors keep the layout.
    risks = [
        ("virus", uz("HPV infeksiyasi"), f"{TODO} {VERIFY}"),
        ("age", uz("Yosh"), f"{TODO} {VERIFY}"),
        ("genes", uz("Irsiyat"), f"{TODO} {VERIFY}"),
        ("habits", uz("Turmush tarzi"), f"{TODO} {VERIFY}"),
        ("other-disease", uz("Boshqa omillar"), f"{TODO} {VERIFY}"),
    ]
    return [
        heading(uz("Bachadon bo'yni saratoni nima?")),
        text_card(
            _lines(
                "Bachadon bo'yni saratoni xavfli o'sma bo'lib, bachadon bo'yni sohasida paydo "
                "bo'ladi. Ushbu patologiya ayollar reproduktiv tizimining barcha o'sma "
                "shikastlanishlarining taxminan 15% ni tashkil qiladi. Bachadon bo'yni raki "
                "tarqalganligi jihatidan endometriy raki bilan sut bezi rakidan keyin uchinchi "
                "o'rinda turadi. Kasallik yetarlicha oson tashxislanishiga qaramasdan, "
                "bemorlarning 40% da u kechki bosqichlarda aniqlanadi."
            )
        ),
        heading(uz("Bachadon bo'yni saratoni shakllari")),
        capsules(forms),
        text_card(
            _lines(
                "HPV bilan bog'liq bo'lmagan saraton odatda tezroq rivojlanadi va prognozi "
                "yomonroq bo'ladi. Shu sababli, bugungi kunda HPV maqomi (statusi) davolash "
                "rejasini tanlashda muhim omil hisoblanadi.",
            )
            + p("<b>" + uz("Hujayralar differensiyalanish darajasi") + "</b>")
            + _lines(
                "Differensiyalanish — bu o'simta hujayralari sog'lom hujayralardan qanchalik farq "
                "qilishini bildiradi. Qanchalik farq katta bo'lsa, o'simta shunchalik tez o'sadi "
                "va tarqalish xavfi yuqori bo'ladi.",
                "Uchta daraja mavjud:",
            )
        ),
        capsules(grades),
        text_card(
            ul(
                [
                    uz(
                        "Yassi hujayrali saraton — barcha holatlarning taxminan 80 foizini tashkil "
                        "etadi. Skrining tufayli ko'pincha erta bosqichda aniqlanadi va "
                        "muvaffaqiyatli davolanadi (jarrohlik, nur yoki kimyonur terapiyasi)."
                    ),
                    uz(
                        "Adenokarsinoma — 10–20 foiz hollarda uchraydi, o'tishi yassi hujayrali "
                        "shaklga o'xshash. Davolash taktikasi bosqichga bog'liq."
                    ),
                    uz(
                        "Neyroendokrin karsinoma — kam uchraydigan (1%) lekin agressiv tur. U "
                        "tezda metastaz beradi va ko'pincha jarrohlik, kimyo va nur terapiyasining "
                        "kombinatsiyasi bilan davolanadi."
                    ),
                    uz(
                        "Germinogen o'simtalar — juda kam uchraydi, lekin o'tkir kechadi. Asosiy "
                        "davolash usuli — jarrohlik yo'li bilan olib tashlash."
                    ),
                ]
            )
            + p("<b><i>" + uz("Metastatik jarayonlarda") + "</i></b>")
            + p(
                "<i>"
                + uz(
                    "Asosiy davolash — tizimli terapiya (kimyoterapiya, nishonli yoki "
                    "immunoterapiya). Ayrim hollarda mahalliy usullar — metastazni jarrohlik yo'li "
                    "bilan olib tashlash yoki nur terapiyasi — qo'shimcha sifatida qo'llaniladi."
                )
                + "</i>"
            )
            + p("<b><i>" + uz("Asosiysi") + "</i></b>")
            + p(
                "<i>"
                + uz(
                    "Bachadon bo'yni saratonining ikki asosiy shakli mavjud: yassi hujayrali va "
                    "adenokarsinoma. HPV holatini aniqlash shifokorga eng to'g'ri davolash rejasini "
                    "tanlashga yordam beradi. Muntazam skrining, erta tashxis va o'z vaqtida "
                    "davolash kasallikni boshlang'ich bosqichda aniqlash imkonini beradi va to'liq "
                    "sog'ayish ehtimolini sezilarli darajada oshiradi."
                )
                + "</i>"
            ),
            title=uz("Eng ko'p uchraydigan shakllar"),
        ),
        uz_statistics(),
        heading(uz("Bachadon bo'yni saratoni bosqichlari")),
        text_card(
            _lines(
                "Bachadon bo'yni saratoni, ayollar reproduktiv tizimining boshqa xavfli o'simtalari "
                "kabi, xalqaro TNM va FIGO (Xalqaro akusherlik va ginekologiya federatsiyasi) "
                "tizimlariga ko'ra tasniflanadi. Bu tizimlar shifokorlarga o'simta qanchalik "
                "rivojlanganini baholash va eng samarali davolash yo'lini tanlash imkonini beradi.",
                "Bosqich — bu o'simta bachadon bo'yni chegarasidan chiqib ketganmi, yaqin "
                "atrofdagi a'zolarga yoki limfa tugunlariga tarqalganmi, yoki uzoq metastazlar "
                "paydo bo'lganmi, degan savollarga javob beradi. Aynan bosqich to'g'ri davolash "
                "taktikasini tanlashda asosiy mezon hisoblanadi.",
                "Bachadon bo'yni saratoni to'rt bosqichga bo'linadi va har biri o'z ichida kichik "
                "guruhlarga ega.",
            )
        ),
        capsules(stages),
        text_card(
            p("<b>" + uz("Prognoz va kasallik kechishi") + "</b>")
            + _lines(
                "Bachadon bo'yni saratonining prognozi bosqichga, o'simtaning agressivligiga va "
                "hujayra tuzilishiga bog'liq. Kasallik qanchalik erta aniqlansa, to'liq sog'ayish "
                "ehtimoli shunchalik yuqori bo'ladi. Shuningdek, ayolning umumiy sog'lig'i va "
                "boshqa kasalliklari ham davolash tanloviga ta'sir qiladi.",
                "Ba'zan hatto og'ir bosqichlarda ham natijalar kutilganidan yaxshiroq bo'lishi "
                "mumkin. Zamonaviy usullar, xususan immunoterapiya, bemorlarning umrini uzaytiradi "
                "va hayot sifatini yaxshilaydi.",
            )
            + p("<b>" + uz("Asosiysi") + "</b>")
            + _lines(
                "Bachadon bo'yni saratoni bosqichi o'simtaning qanchalik tarqalganini ko'rsatadi. "
                "To'g'ri bosqichni aniqlash — to'g'ri davolash va sog'ayish imkonini belgilovchi "
                "eng muhim qadamlardan biridir. Kasallik qanchalik erta tashxislansa, sog'ayish "
                "ehtimoli shunchalik yuqori bo'ladi."
            )
        ),
        heading(uz("Bachadon bo'yni saratoni sabablari")),
        text_card(
            _lines(
                "Bachadon bo'yni rakining asosiy sababi papillomavirus infeksiyasi, ayniqsa OPV 16 "
                "va 18 serotiplaridir. IPV 16 yassi hujayrali saraton bilan, IPV 18 esa "
                "adenokarsinoma bilan assotsiatsiyalanadi.",
                "Xavf omillari quyidagilardan iborat:",
            )
        ),
        icon_tiles(risks),
        alert(DONT_PANIC),
        appeal(lang, ctx),
        verify_note(lang),
    ]


# ---------------------------------------------------------------------------------------------
# «Skrining» (Figma 2408:940)
# ---------------------------------------------------------------------------------------------
def _screening_intro() -> Body:
    return [
        heading(uz("Skrining nima?")),
        text_card(
            _lines(
                "Skrining – kasalliklarni (jumladan, saraton) aniq belgilari namoyon bo'lgunga "
                "qadar erta aniqlash dasturidir. U hech qanday shikoyati bo'lmagan odamlarning "
                "katta qismi uchun o'tkaziladi. Tekshiruvdan o'tganlarning aksariyati sog'lom "
                "bo'ladi. Biroq, agar shubhali o'zgarishlar aniqlansa, odam qo'shimcha "
                "tekshiruvdan o'tishi kerak bo'ladi.",
                "Skrining yordamida kasallikni davolash eng samarali bo'lgan erta bosqichda "
                "“ushlashga” urinadi. Ushbu bosqichda o'simta hali organdan tashqariga "
                "tarqalmagan yoki yoqimsiz simptomlarni keltirib chiqarmagan.",
            )
        ),
        heading(uz("Skrining profilaktikadan qanday farq qiladi?")),
        text_card(
            _lines(
                "Profilaktika – bu kasallikning rivojlanish xavfini yoki mavjud holatning "
                "asoratlarini kamaytirishga qaratilgan chora-tadbirlar majmui. Masalan, qon tomir "
                "kasalliklarini oldini olish uchun ratsiondan qizarib pishgan va yog'li "
                "ovqatlarni chiqarib tashlash. Yoki teri saratoni rivojlanish ehtimolini "
                "kamaytirish uchun quyoshdan himoyalovchi kremlardan foydalanish va quyoshga "
                "ta'sir qilishni cheklash. Demak, oldini olish insonning kelajakdagi farovonligi "
                "uchun rioya qiladigan aniq qoidalar sifatida belgilanadi. Uning maqsadi saraton "
                "rivojlanishining oldini olishdir.",
                "Boshqa tomondan, skrining har bir kasallik uchun maxsus testlarni o'tkazishni o'z "
                "ichiga oladi: ko'krak bezi saratoni uchun mammografiya, yo'g'on ichak saratoni "
                "uchun najasda yashirin qon tekshiruvi va boshqalar. Maqsad saratonni erta "
                "bosqichda, uni samarali davolash mumkin bo'lgan vaqtda aniqlash va kasallikdan "
                "o'lim darajasini kamaytirishdir.",
            )
        ),
    ]


def _where_to_screen(lang: str) -> dict[str, Any]:
    """TZ «Где пройти» bullets, verbatim (TZ §2.1)."""
    return text_card(
        ul(
            [
                t(lang, "oilaviy shifokorlik punktlari;", "семейные врачебные пункты;"),
                t(
                    lang,
                    "tuman poliklinikalari (onkologik ogohlik xonalari);",
                    "районные поликлиники (кабинеты онконастороженности);",
                ),
                t(
                    lang,
                    "Ona va bola salomatligi markazi va uning filiallari;",
                    "Центр здоровья матери и ребенка и его филиалы;",
                ),
                t(
                    lang,
                    "davlat dasturi doirasida — bepul.",
                    "Бесплатно – в рамках государственной программы.",
                ),
            ]
        ),
        title=t(lang, "Qayerda o'tish mumkin", "Где пройти"),
    )


def _tz_screening_rules(lang: str) -> dict[str, Any]:
    """TZ screening table, verbatim (TZ §2.1 «Кому и как часто») — the rules the tools use."""
    return text_card(
        ul(
            [
                t(
                    lang,
                    "mammografiya: 45–65 yoshdagi ayollar, 2 yilda bir marta;",
                    "маммография: женщины 45–65 лет, раз в 2 года;",
                ),
                t(
                    lang,
                    "UTT: 45 yoshgacha bo'lgan ayollar, 2 yilda bir marta;",
                    "УЗИ: женщины до 45 лет, раз в 2 года;",
                ),
                t(lang, "HPV-test: 30–50 yoshdagi ayollar;", "ВПЧ-тест: женщины 30–50 лет;"),
                t(
                    lang,
                    "o'z-o'zini tekshirishga chaqiriq.",
                    "Призывы к самостоятельному обследованию.",
                ),
            ]
        )
        + p(VERIFY),
        title=t(
            lang, "Davlat dasturi: kimga va qanchalik tez-tez", "Госпрограмма: кому и как часто"
        ),
    )


PQ402_URL = "https://lex.uz/docs/7232845"


def _pq402_programme(lang: str) -> dict[str, Any]:
    """Client answer of 2026-09-25 (D-071): the free-screening sentence cites PQ-402 in full and
    the whole paragraph links to the resolution on lex.uz."""
    text = t(
        lang,
        uz(
            "30, 40 va 50 yoshdagi ayollarda odam papilloma virusini hamda suyuqlik sitologiyasi "
            "usuli yordamida bachadon bo'yni saratonini aniqlash skriningi bepul amalga "
            "oshiriladi – “Bachadon bo'yni va ko'krak bezi saratonini nazorat qilish dasturi” "
            "(O'zbekiston Respublikasi Prezidentining PQ-402-sonli qarori)."
        ),
        "Женщинам в возрасте 30, 40 и 50 лет бесплатно проводится скрининг для выявления рака "
        "шейки матки — тест на вирус папилломы человека и жидкостная цитология — «Программа "
        "контроля рака шейки матки и молочной железы» (Постановление Президента Республики "
        "Узбекистан ПП-402).",
    )
    return text_card(p(f'<a href="{PQ402_URL}">{text}</a>'))


def body_breast_screening(lang: str, ctx: SeedContext) -> Body:
    if lang != "uz":
        body = _ru_skeleton(
            lang,
            ctx,
            ["Что такое скрининг?", "Чем скрининг отличается от профилактики?", "Методы скрининга"],
        )
        return [
            *body[:-1],
            _tz_screening_rules(lang),
            _pq402_programme(lang),
            _where_to_screen(lang),
            body[-1],
        ]
    return [
        *_screening_intro(),
        heading(uz("Skrining usullari")),
        text_card(
            p(
                uz(
                    "Bugungi kunda shifokorlar sut bezlarini tekshirish uchun uchta asosiy usuldan foydalanadilar:"
                )
            )
            + ul(
                [
                    uz("Mammografiya;"),
                    uz("Ultratovush tekshiruvi (UTT);"),
                    uz("Magnit-rezonans tomografiya."),
                ]
            )
        ),
        text_card(
            _lines(
                "Mammografiya — “oltin standart”",
                "Mammografiya sut bezi saratonini erta aniqlashning asosiy usuli. Bu past dozalarda "
                "rentgen nuri yordamida olingan ko'krak suratidir. Jarayon 10–15 daqiqa davom etadi "
                "va ikki yo'nalishda — to'g'ridan-to'g'ri va yon tomondan o'tkaziladi. "
                "Tekshiruvdan oldin kiyim va zargarlik buyumlarini beldan yuqorisigacha yechish "
                "kerak. Har bir sut bezi apparat plastinalari orasiga joylashtiriladi va biroz "
                "siqiladi. Bu qisqa vaqt davom etadi, xavfsiz va odatda og'riqsiz.",
                "Mammografiya homiladorlik yoki emizish davrida o'tkazilmaydi. 40 yoshgacha bo'lgan "
                "ayollarda bu usul kamroq samara berishi mumkin, chunki ularning sut bezlari "
                "to'qimasi zichroq bo'ladi.",
                "Cheklovlariga qaramay, mammografiya butun dunyoda eng samarali skrining usuli deb "
                "tan olingan. Aynan shu tekshiruv yordamida sut bezi saratonidan o'lim darajasi "
                "kamaydi.",
            ),
            label="Mammografiya",
            illustration="mammography",
        ),
        text_card(
            _lines(
                "UTT yordamida sut bezlari va u bilan bog'liq limfa tugunlari tekshiriladi. Jarayon "
                "og'riqsiz, nurlanishsiz va taxminan 15 daqiqa davom etadi.",
                "Ayol yotgan holatda bo'ladi, shifokor maxsus gel surtadi va datchik yordamida "
                "ko'krak to'qimalarini turli burchaklardan ko'radi. UTT natijalari mammografiyani "
                "to'ldiradi va shubhali joylarni aniqlashga yordam beradi.",
            ),
            label="UTT",
            illustration="ultrasound",
        ),
        text_card(
            _lines(
                "MRT sut bezlarining uch o'lchamli tasvirini olish imkonini beradi. Bu zamonaviy, "
                "ammo hamma uchun mo'ljallanmagan usul. U asosan yuqori xavf guruhidagi ayollar "
                "uchun, masalan, irsiy moyilligi bor bemorlar uchun qo'llaniladi.",
                "Jarayon magnit tomografda o'tkaziladi. Bemor qorniga yotadi va 30–40 daqiqa "
                "davomida harakatsiz qoladi. Agar yurak stimulyatori yoki metall implantlar "
                "bo'lsa, bu haqda oldindan shifokorga aytish kerak.",
                "MRT ba'zan saraton bilan bog'liq bo'lmagan sohalarni ham ko'rsatishi mumkin, bu "
                "esa ortiqcha tashxis qo'yish yoki keraksiz biopsiyalarga olib keladi. Shu sababli "
                "bu usul faqat shifokor tavsiyasiga binoan qo'llaniladi.",
            ),
            label="MRT",
            illustration="mri",
        ),
        heading(uz("Kimlarga skrining tavsiya etiladi")),
        text_card(
            ul(
                [
                    uz(
                        "40 yoshdan 75 yoshgacha bo'lgan ayollar — mammografiya har ikki yilda bir "
                        "marta. Bu sut bezi saratonini erta aniqlashning eng ishonchli usuli."
                    ),
                    uz(
                        "40 yoshgacha bo'lgan ayollar — har oyda muntazam ko'krakni o'z-o'zini "
                        "tekshirish tavsiya etiladi. Eng yaxshi vaqt — hayz ko'rish boshlanganidan "
                        "5–7 kun o'tib. O'z-o'zini tekshirish o'zgarishlarni erta payqash va "
                        "shifokorga o'z vaqtida murojaat qilishga yordam beradi."
                    ),
                    uz(
                        "Agar irsiy moyillik (yaqin qarindoshlarda ko'krak yoki tuxumdon saratoni) "
                        "yoki boshqa xavf omillari mavjud bo'lsa, shifokor 25–30 yoshdan boshlab "
                        "sut bezlarining UTT tekshiruvini tavsiya qilishi mumkin."
                    ),
                    uz(
                        "75 yoshdan keyin mammografiyaning zarurligi sog'liq holati va shifokor "
                        "tavsiyasiga qarab belgilanadi."
                    ),
                ]
            )
            # The Figma ages differ from the TZ screening table (45–65 / under 45): doctor decides.
            + p(f"{VERIFY} [[VERIFY: TZ — mammografiya 45–65, UTT 45 yoshgacha]]")
        ),
        _tz_screening_rules(lang),
        alert(
            uz(
                "Skrining saratonning oldini olmaydi, ammo uni mumkin qadar erta aniqlash imkonini "
                "beradi. Bu sog'liqni, ko'krakni va hayotni saqlab qolish imkonidir."
            )
        ),
        _pq402_programme(lang),
        _where_to_screen(lang),
        appeal(lang, ctx),
        verify_note(lang),
    ]


def body_cervical_screening(lang: str, ctx: SeedContext) -> Body:
    """No Figma frame: the generic screening copy, the TZ rules and the Figma state-programme
    text for cervical cancer (from the «Qo'llab-quvvatlash» frame)."""
    if lang != "uz":
        body = _ru_skeleton(lang, ctx, ["Что такое скрининг?", "Скрининг рака шейки матки"])
        return [*body[:-1], _tz_screening_rules(lang), _where_to_screen(lang), body[-1]]
    return [
        *_screening_intro(),
        heading(uz("Bachadon bo'yni saratoni skriningi")),
        text_card(
            p("<b>" + uz("Bachadon bo'yni saratoni (BBS):") + "</b> " + uz(BBS_PROGRAMME))
            + p(f"{TODO} {VERIFY}")
        ),
        _tz_screening_rules(lang),
        _where_to_screen(lang),
        appeal(lang, ctx),
        verify_note(lang),
    ]


# ---------------------------------------------------------------------------------------------
# «Davolashni tashkil etish» (Figma 2408:1396) — the TZ 4-step patient route
# ---------------------------------------------------------------------------------------------
def _route(lang: str) -> dict[str, Any]:
    items = [
        (
            "1",
            t(lang, "Birlamchi qabul", "Первичный прием"),
            p(
                t(
                    lang,
                    uz(
                        "Birinchi belgilar paydo bo'lganda yoki rejalashtirilgan tashrif vaqtida "
                        "terapevt yoki ginekologga murojaat qiling."
                    ),
                    "Обратитесь к терапевту или гинекологу при первых признаках или при плановом визите.",
                )
            ),
        ),
        (
            "2",
            t(lang, uz("Diagnostikaga yo'llanma"), "Направление на диагностику"),
            p(
                t(
                    lang,
                    uz(
                        "UZI, mammografiya, testlar, «Onkologik ogohlik» xonasidagi qabul va boshqalar."
                    ),
                    "УЗИ, маммография, тесты, прием у кабинета «Онконастороженности» и др.",
                )
            ),
        ),
        (
            "3",
            t(lang, "Onkolog / onkoginekolog", "Онколог / онкогинеколог"),
            p(
                t(
                    lang,
                    uz(
                        "Shubha yoki tashxis tasdiqlanganda — onkologiya markaziga yo'llanma "
                        "(PQ-402dagi muddatlarga muvofiq)."
                    ),
                    "При подозрении или подтверждении диагноза — направление в онкологический "
                    "центр (в соответствии с датами в ПП-402).",
                )
            ),
        ),
        (
            "4",
            t(lang, "Davolash", "Лечение"),
            p(
                t(
                    lang,
                    uz("Shifokor ko'rsatmasi bilan amalga oshiriladi."),
                    "Информация об этапах лечения.",
                )
            ),
        ),
    ]
    block = capsules(items)
    # TZ: the referral deadline of step 3 is a field of its own (spec §2.2)
    block["value"]["steps"][2]["deadline"] = "[[VERIFY: PP-402 referral deadlines]]"
    return block


def _route_intro(lang: str) -> dict[str, Any]:
    return text_card(
        p(
            t(
                lang,
                uz(
                    "Bemorning dastlabki alomatlardan davolashni boshlashgacha bo'lgan "
                    "bosqichma-bosqich yo'nalishi. Xavotirni kamaytirish va qaror qabul qilishni "
                    "tezlashtirish uchun aniq va tushunarli ma'lumotlar."
                ),
                "Пошаговый маршрут пациента — от первых симптомов до начала лечения. Ясная, "
                "доступная информация для снижения тревожности и ускорения принятия решений.",
            )
        )
        + p(
            t(
                lang,
                uz("Quyidagi bosqichma-bosqich ma'lumotlar aks ettiriladi:"),
                "Будет отражаться следующая пошаговая информация:",
            )
        )
    )


def body_breast_treatment(lang: str, ctx: SeedContext) -> Body:
    head = [
        heading(t(lang, "Davolashni tashkil etish", "Организация лечения")),
        _route_intro(lang),
        _route(lang),
    ]
    if lang != "uz":
        return [*head, heading("Лечение"), text_card(p(RU_TODO) + p(VERIFY)), appeal(lang, ctx)]
    return [
        *head,
        heading("Davolash"),
        text_card(
            _lines(
                "Davolash usulini tanlash ko'plab omillarga bog'liq: kasallikning bosqichi, "
                "ayolning yoshi, o'simtaning tuzilishi va hajmi, o'sish tezligi. Davolashning "
                "zamonaviy usullari jarrohlik, radiatsiya va kimyoterapiya usullarining eng maqbul "
                "kombinatsiyasidan, ya'ni kompleks yondashuvdan foydalanadi. Terapiyada "
                "mutaxassislar har bir bemorga individual yondashishlari kerak. Mutaxassislar "
                "guruhi ayolga davolashning onkologik va estetik nuqtai nazardan muvaffaqiyatli "
                "bo'lishi uchun o'ziga xos davolash usullarini taklif qilishi kerak."
            )
        ),
        text_card(
            p(
                uz(
                    "Bugungi kunda ko'krak bezi saratonini davolashning eng samarali usullari quyidagilardir:"
                )
            )
            + ul(
                [
                    uz("lampektomiya (o'smaning o'zini olib tashlashni o'z ichiga oladi);"),
                    uz(
                        "mastektomiya (ko'krak va boshqa to'qimalarni to'liq olib tashlashni o'z ichiga oladi);"
                    ),
                    uz(
                        "radiatsion terapiya (agar bemor klimaks davridan o'tgan bo'lsa) – saraton "
                        "radioaktiv nurlanish bilan nurlanadi;"
                    ),
                    uz(
                        "kimyoterapiya (agar bemor klimaks davridan o'tmagan bo'lsa) – saraton "
                        "hujayralarining o'limini ta'minlaydigan sitostatiklar qo'llaniladi;"
                    ),
                    uz(
                        "gormon terapiyasi – o'simtaning gormonlarga sezuvchanligini blokirovka "
                        "qiluvchi dorilar qo'llaniladi;"
                    ),
                    uz("immunoterapiya."),
                ]
            )
        ),
        text_card(
            _lines(
                "Operatsiyadan keyin organizmning xususiyatlariga, davolash sifatiga, kasallikning "
                "bosqichiga qarab, bemorlarning bir qismi bir necha yil, ba'zilari esa keksalikka "
                "qadar yashaydi. Statistikaga ko'ra, operatsiyadan keyingi yangi metastazlar "
                "birinchi 3-5 yil ichida paydo bo'ladi, keyinchalik yangi shakllanish xavfi "
                "keskin kamayadi."
            )
        ),
        alert(
            uz(
                "Ko'krak bezi saratonini xalq tabobati bilan davolash samarasizdir. Dorivor "
                "giyohlar va xalq retseptlari saraton bilan samarali kurasha olmaydi. O'zboshimchalik "
                "bilan davolanish odatda shifokorga tashrifni kechiktiradi va bemorning umrini "
                "qisqartiradi."
            )
        ),
        appeal(lang, ctx),
        verify_note(lang),
    ]


def body_cervical_treatment(lang: str, ctx: SeedContext) -> Body:
    return [
        heading(t(lang, "Davolashni tashkil etish", "Организация лечения")),
        _route_intro(lang),
        _route(lang),
        heading(t(lang, "Davolash", "Лечение")),
        text_card(p(TODO if lang == "uz" else RU_TODO) + p(VERIFY)),
        appeal(lang, ctx),
    ]


# ---------------------------------------------------------------------------------------------
# «Qo'llab-quvvatlash» (Figma 2408:1794) — TZ «Государственная поддержка» + «Уход и поддержка»
# ---------------------------------------------------------------------------------------------
KBS_PROGRAMME = (
    "30–65 yoshdagi ayollar har 2 yilda bir marta tibbiyot xodimlari tomonidan dastlabki "
    "ko'rikdan o'tadilar. 45 yoshgacha bo'lgan ayollarda ko'krak bezlari UZI orqali, 45–65 "
    "yoshda esa mammografiya orqali tekshiriladi."
)
BBS_PROGRAMME = (
    "30–50 yoshdagi ayollar har yili inson papilloma virusi (HPV)ni aniqlash uchun PCR-testi va "
    "suyuq asosli sitologiya yordamida skriningdan o'tadilar. Natija manfiy bo'lsa, keyingi "
    "tekshiruv 10 yildan so'ng o'tkaziladi. Natija ijobiy bo'lsa, qo'shimcha tekshiruvga "
    "yo'llanma beriladi."
)


def body_support(lang: str, ctx: SeedContext) -> Body:
    from apps.core.seed.tree import body_w_care

    care_columns = body_w_care(lang, ctx)[1]  # TZ «Уход и поддержка» three columns, verbatim
    if lang != "uz":
        return [
            heading("Бесплатный скрининг в рамках государственной программы"),
            text_card(p(RU_TODO) + p(VERIFY)),
            heading("Возможности в кабинетах «Онконастороженности»"),
            text_card(p(RU_TODO) + p(VERIFY)),
            heading("Права и обязанности пациентов и врачей"),
            text_card(p(RU_TODO) + p(VERIFY)),
            heading("Уход и поддержка"),
            care_columns,
            appeal(lang, ctx),
        ]
    rights = [
        (
            "1",
            "",
            p(
                uz(
                    "Tushunarli ma'lumot olish huquqi: tashxis, davolash usullari, xavflar va "
                    "muqobil variantlar haqida to'liq va tushunarli ma'lumot olish, shuningdek, har "
                    "qanday muolajadan oldin ongli ravishda rozilik berish. Bemor davolash bo'yicha "
                    "qaror qabul qilishda ishtirok etishi uchun xavflar, afzalliklar, cheklovlar va "
                    "muqobil usullar haqida zarur ma'lumotlarni olish huquqiga ega."
                )
            ),
        ),
        (
            "2",
            "",
            p(
                uz(
                    "Tibbiy ma'lumotlarning maxfiyligi va o'z tibbiy hujjatlari bilan tanishish huquqi."
                )
            ),
        ),
        (
            "3",
            "",
            p(
                uz(
                    "Ikkinchi tibbiy xulosani olish huquqi: davolash bo'yicha qaror qabul qilishdan "
                    "oldin boshqa mutaxassisning fikrini olish."
                )
            ),
        ),
        (
            "4",
            "",
            p(
                uz(
                    "Davolanish yoki yo'llanmadan voz kechish huquqi: bunday qarorning mumkin "
                    "bo'lgan oqibatlari haqida xabardor qilingan holda davolanishdan yoki berilgan "
                    "yo'llanmadan voz kechish."
                )
            ),
        ),
        (
            "5",
            "",
            p(
                uz(
                    "Hurmat va munosib munosabatga ega bo'lish: kamsitishlarsiz, hurmat bilan munosabatda bo'lish."
                )
            ),
        ),
    ]
    duties = [
        card(
            p(uz("Shifokor qabulidagi bemorlar quyidagi majburiyatlarga ega:"))
            + ul(
                [
                    uz(
                        "Shifokorga o'z salomatligi haqida to'liq va haqqoniy ma'lumot berish, "
                        "jumladan, qabul qilayotgan dori vositalari va ma'lum bo'lgan allergiyalari "
                        "haqida xabar berish."
                    ),
                    uz(
                        "Kelishilgan tekshiruv va davolash rejasiga rioya qilish, agar uni "
                        "o'zgartirish istagi bo'lsa, bu haqda shifokorga o'z vaqtida xabar berish."
                    ),
                    uz(
                        "Qaror haqiqatan ham ongli ravishda qabul qilinishi uchun savollar berish va "
                        "tushunarsiz jihatlarni aniqlashtirish."
                    ),
                ]
            ),
            title=uz("Bemorning majburiyatlari"),
        ),
        card(
            p(
                uz(
                    "Shifokorlar esa quyidagilarni mas'uliyat bilan bajarishi uning majburiyatiga kiradi:"
                )
            )
            + ul(
                [
                    uz(
                        "Bemorga tashxis, kasallik prognozi va davolash usullari haqida to'liq, "
                        "tushunarli va o'z vaqtida ma'lumot berish."
                    ),
                    uz(
                        "Diagnostik yoki davolash muolajalarini boshlashdan oldin bemorning ongli roziligini olish."
                    ),
                    uz(
                        "Bemorning ma'lumotlari maxfiyligini ta'minlash va uning shaxsiy hayot "
                        "daxlsizligiga bo'lgan huquqini hurmat qilish."
                    ),
                ]
            ),
            title=uz("Shifokor majburiyatlari"),
        ),
    ]
    return [
        heading(uz("Davlat dasturi doirasida bepul skrining")),
        text_card(
            p("<b>" + uz("Ko'krak bezi saratoni (KBS):") + "</b> " + uz(KBS_PROGRAMME))
            + p("<b>" + uz("Bachadon bo'yni saratoni (BBS):") + "</b> " + uz(BBS_PROGRAMME))
        ),
        heading(uz("«Onkologik hushyorlik» xonalarida mavjud imkoniyatlar")),
        text_card(
            ul(
                [
                    uz(
                        "Ushbu xonalar akusher-ginekolog shifokor lavozimi mavjud bo'lgan ko'p "
                        "tarmoqli tuman (shahar) poliklinikalarida tashkil etiladi."
                    ),
                    uz(
                        "Agar skrining natijasida o'zgarishlar, masalan, HPV testi ijobiy natijasi "
                        "yoki sitologik tekshiruvda o'zgarishlar aniqlansa, ushbu xonada "
                        "kolposkopiya tekshiruvi tashkil etiladi."
                    ),
                    uz(
                        "Bemorning yo'nalishi: ko'p tarmoqli tuman (shahar) poliklinikasi "
                        "(«Onkologik hushyorlik» xonasi) → saratonoldi holati aniqlanganda — "
                        "Respublika ixtisoslashtirilgan ona va bola salomatligini muhofaza qilish "
                        "ilmiy-amaliy tibbiyot markazi yoki uning hududiy filialiga ambulator "
                        "davolanish uchun yo'llanma → onkologik kasallikka shubha qilinganda yoki "
                        "tashxis tasdiqlanganda — onkologiya markaziga (Respublika "
                        "ixtisoslashtirilgan onkologiya va radiologiya ilmiy-amaliy tibbiyot markazi "
                        "yoki uning hududiy filialiga) yo'llanma beriladi."
                    ),
                ]
            )
        ),
        heading(uz("Bemorlar va shifokorlarning huquq va majburiyatlari")),
        rich(f"<h3>{uz('Bemor quyidagi huquqlarga ega:')}</h3>"),
        capsules(rights, arrows=False),
        text_cards(duties),
        heading(uz("Parvarish va qo'llab-quvvatlash")),
        text_card(
            _lines(
                "Davolanish vaqtida va undan keyin ayollar uchun amaliy ma'lumotlar va ruhiy "
                "qo'llab-quvvatlash — har bir bosqichda hayot sifatini saqlab qolish uchun xizmat "
                "qiladi."
            )
        ),
        care_columns,
        appeal(lang, ctx),
        verify_note(lang),
    ]


# ---------------------------------------------------------------------------------------------
# «Kasallikdan keyingi hayot» (Figma 2408:2128) — the TZ three columns
# ---------------------------------------------------------------------------------------------
def body_after(lang: str, ctx: SeedContext) -> Body:
    if lang != "uz":
        from apps.core.seed.tree import body_w_after

        return [heading("Жизнь после рака"), *body_w_after(lang, ctx), appeal(lang, ctx)]
    columns = [
        (
            "Davolanishdan keyingi kuzatuv",
            [
                "Nazorat ko'riklar jadvali;",
                "Davolanishning kechki ta'sirlari;",
                "Bemorning sog'liq pasporti.",
            ],
        ),
        (
            "Hayotga qaytish",
            [
                "Ishga va odatiy hayot ritmiga qaytish;",
                "Jismoniy reabilitatsiya;",
                "Ruhiy tiklanish.",
            ],
        ),
        (
            "Uzoq muddatli salomatlik",
            [
                "Qaytalanishning oldini olish;",
                "Davolanishdan keyingi reproduktiv salomatlik;",
                "Uzoq muddatli istiqbolda psixologik farovonlik",
            ],
        ),
    ]
    return [
        heading(uz("Saraton kasalligidan keyingi hayot")),
        text_card(
            _lines(
                "Davolanishning yakunlanishi — yangi boshlanish. Ushbu bo'lim ayollarga to'laqonli "
                "hayotga qaytish va uzoq yillar davomida sog'lig'ini saqlashga yordam beradi."
            )
        ),
        text_cards(
            [card(ul([uz(i) for i in items]), title=uz(title)) for title, items in columns],
            columns="3",
        ),
        appeal(lang, ctx),
    ]
