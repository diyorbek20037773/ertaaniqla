"""The complete TZ structure (docs/TZ_concept_ru.md §II, spec §2.2–2.3) as data.

Rules (AUTOPILOT rule 3): Russian bullets are copied verbatim from the TZ; Uzbek is a real
Latin-script translation of the headings/bullets; every body is tagged
`[[TODO: content — copywriter]]`, concrete medical facts `[[VERIFY: doctor]]`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

TODO = "[[TODO: content — copywriter]]"
VERIFY = "[[VERIFY: doctor]]"
VERIFY_PP402 = "[[VERIFY: PP-402 referral deadlines]]"

Lang = str
Body = list[dict[str, Any]]


class SeedContext:
    """Resolves cross-references while building bodies (page ids by key, term ids)."""

    def __init__(self) -> None:
        self.pages: dict[tuple[str, str], int] = {}
        self.terms: dict[str, list[int]] = {"uz": [], "ru": []}

    def page_id(self, key: str, lang: str) -> int | None:
        return self.pages.get((key, lang))


BodyBuilder = Callable[[Lang, SeedContext], Body]


@dataclass
class Node:
    key: str
    kind: str  # section | topic | article | directory
    title: dict[str, str]
    slug: dict[str, str]
    summary: dict[str, str] = field(default_factory=dict)
    body: BodyBuilder | None = None
    show_in_menus: bool = True
    children: list[Node] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# block helpers (JSON form of StreamField values)
# ---------------------------------------------------------------------------
def t(lang: str, uz: str, ru: str) -> str:
    return ru if lang == "ru" else uz


def ul(items: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{item}</li>" for item in items) + "</ul>"


def p(*paragraphs: str) -> str:
    return "".join(f"<p>{item}</p>" for item in paragraphs)


def rich(html: str) -> dict[str, Any]:
    return {"type": "rich_text", "value": html}


def callout(kind: str, title: str, html: str) -> dict[str, Any]:
    return {"type": "callout", "value": {"kind": kind, "title": title, "text": html}}


def todo_callout(lang: str, bullets_uz: list[str], bullets_ru: list[str]) -> dict[str, Any]:
    """Structured placeholder: the TZ bullets the copywriter must cover, in both languages."""
    title = t(
        lang, "Ushbu sahifada nima boʻlishi kerak (TZ)", "Что должно быть на этой странице (ТЗ)"
    )
    html = p(TODO) + ul(bullets_ru if lang == "ru" else bullets_uz)
    if lang == "uz":
        html += p("<i>ТЗ (ru):</i>") + ul(bullets_ru)
    return callout("info", title, html)


def columns(block_type: str, cols: list[tuple[str, list[str]]]) -> dict[str, Any]:
    return {
        "type": block_type,
        "value": {"columns": [{"title": title, "items": ul(items)} for title, items in cols]},
    }


def stat(value: str, label: str, source: str = VERIFY, year: int | None = None) -> dict[str, Any]:
    return {
        "type": "stat",
        "value": {"value": value, "label": label, "source": source, "year": year},
    }


def cards(title: str, items: list[tuple[str, str]], icon: str = "") -> dict[str, Any]:
    return {
        "type": "cards_grid",
        "value": {
            "title": title,
            "cards": [
                {
                    "image": None,
                    "icon": icon,
                    "title": card_title,
                    "text": p(text),
                    "link": {"page": None, "url": ""},
                }
                for card_title, text in items
            ],
        },
    }


def steps(title: str, items: list[tuple[str, str, str]]) -> dict[str, Any]:
    return {
        "type": "steps",
        "value": {
            "title": title,
            "steps": [
                {
                    "number": "",
                    "title": step_title,
                    "text": p(text),
                    "deadline": deadline,
                    "link": {"page": None, "url": ""},
                }
                for step_title, text, deadline in items
            ],
        },
    }


def cta(text: str, label: str, page_id: int | None) -> dict[str, Any]:
    """Empty dict when the target page does not exist yet (dropped by the builder in pass 1)."""
    if page_id is None:
        return {}
    return {
        "type": "cta",
        "value": {
            "text": p(text) if text else "",
            "button_label": label,
            "link": {"page": page_id, "url": ""},
            "style": "primary",
        },
    }


def symptoms(title: str, items: list[tuple[str, str, str]]) -> dict[str, Any]:
    return {
        "type": "symptom_list",
        "value": {
            "title": title,
            "symptoms": [
                {"symptom": name, "urgency": urgency, "explanation": p(explanation)}
                for name, urgency, explanation in items
            ],
        },
    }


def faq(title: str, items: list[tuple[str, str]]) -> dict[str, Any]:
    return {
        "type": "faq_accordion",
        "value": {"title": title, "items": [{"question": q, "answer": p(a)} for q, a in items]},
    }


def table(caption: str, headings: list[str], rows: list[list[str]]) -> dict[str, Any]:
    return {
        "type": "table",
        "value": {
            "caption": caption,
            "columns": [{"type": "text", "heading": h} for h in headings],
            "rows": [{"values": row} for row in rows],
        },
    }


# ---------------------------------------------------------------------------
# WOMEN — bodies
# ---------------------------------------------------------------------------
def body_w_what(lang: str, ctx: SeedContext) -> Body:
    return [
        todo_callout(
            lang,
            [
                "organizmda nima sodir boʻladi",
                "kasallik bosqichlari",
                "Oʻzbekiston boʻyicha statistika",
            ],
            ["что происходит в организме", "стадии", "статистика по Узбекистану"],
        ),
        stat(
            "—",
            t(lang, f"{TODO} Oʻzbekiston boʻyicha statistika", f"{TODO} статистика по Узбекистану"),
        ),
        stat("—", t(lang, f"{TODO} bosqichlar boʻyicha aniqlash", f"{TODO} выявление по стадиям")),
        stat(
            "—",
            t(lang, f"{TODO} erta aniqlashda tuzalish", f"{TODO} излечение при раннем выявлении"),
        ),
    ]


def body_w_risk(lang: str, ctx: SeedContext) -> Body:
    items = [
        (t(lang, "Yosh", "Возраст"), TODO),
        (t(lang, "Irsiyat", "Наследственность"), TODO),
        (t(lang, "Turmush tarzi", "Образ жизни"), TODO),
        (t(lang, "HPV infeksiyasi", "ВПЧ-инфекция"), TODO),
        (t(lang, "Boshqa omillar", "Другие факторы, о которых важно знать"), TODO),
    ]
    return [
        todo_callout(
            lang,
            [
                "yosh",
                "irsiyat",
                "turmush tarzi",
                "HPV infeksiyasi",
                "bilish muhim boʻlgan boshqa omillar",
            ],
            [
                "возраст",
                "наследственность",
                "образ жизни",
                "ВПЧ-инфекция",
                "другие факторы, о которых важно знать",
            ],
        ),
        cards(t(lang, "Xavf omillari", "Факторы риска"), items),
    ]


def body_w_symptoms(lang: str, ctx: SeedContext) -> Body:
    return [
        callout(
            "reassurance",
            t(lang, "Bu belgi har doim saraton degani emas", "Этот признак не всегда означает рак"),
            p(TODO),
        ),
        symptoms(
            t(
                lang,
                "Eʼtiborsiz qoldirib boʻlmaydigan belgilar",
                "Признаки, которые нельзя игнорировать",
            ),
            [
                (f"{TODO} 1", "urgent", VERIFY),
                (f"{TODO} 2", "soon", VERIFY),
                (f"{TODO} 3", "routine", VERIFY),
            ],
        ),
        steps(
            t(
                lang,
                "Koʻkrakni mustaqil tekshirish — bosqichma-bosqich qoʻllanma",
                "Самообследование груди — пошаговое руководство",
            ),
            [(f"{TODO} {t(lang, 'qadam', 'шаг')} {n}", VERIFY, "") for n in range(1, 6)],
        ),
        cta(
            t(lang, "Skrining kimga va qachon kerak?", "Кому и когда нужен скрининг?"),
            t(lang, "Skrining haqida", "О скрининге"),
            ctx.page_id("women.screening.who", lang),
        ),
    ]


def body_w_screening_who(lang: str, ctx: SeedContext) -> Body:
    return [
        table(
            t(lang, "Kimga va qanchalik tez-tez", "Кому и как часто") + f" {VERIFY}",
            [
                t(lang, "Tekshiruv", "Обследование"),
                t(lang, "Kimga", "Кому"),
                t(lang, "Qanchalik tez-tez", "Как часто"),
            ],
            [
                [
                    t(lang, "Mammografiya", "Маммография"),
                    t(lang, "45–65 yoshli ayollar", "женщины 45–65 лет"),
                    t(lang, "2 yilda bir marta", "раз в 2 года"),
                ],
                [
                    t(lang, "UTT", "УЗИ"),
                    t(lang, "45 yoshgacha boʻlgan ayollar", "женщины до 45 лет"),
                    t(lang, "2 yilda bir marta", "раз в 2 года"),
                ],
                [
                    t(lang, "HPV-test", "ВПЧ-тест"),
                    t(lang, "30–50 yoshli ayollar", "женщины 30–50 лет"),
                    VERIFY,
                ],
            ],
        ),
        todo_callout(
            lang,
            [
                "mammografiya: 45–65 yoshli ayollar, 2 yilda bir marta;",
                "UTT: 45 yoshgacha boʻlgan ayollar, 2 yilda bir marta;",
                "HPV-test: 30–50 yoshli ayollar;",
                "mustaqil tekshiruvga chaqiriqlar.",
            ],
            [
                "маммография: женщины 45–65 лет, раз в 2 года;",
                "УЗИ: женщины до 45 лет, раз в 2 года;",
                "ВПЧ-тест: женщины 30–50 лет.",
                "Призывы к самостоятельному обследованию.",
            ],
        ),
        cta(
            t(lang, "Skriningni qayerda oʻtish mumkin?", "Где пройти скрининг?"),
            t(lang, "Qayerda oʻtish mumkin", "Где пройти"),
            ctx.page_id("women.screening.where", lang),
        ),
    ]


def body_w_screening_where(lang: str, ctx: SeedContext) -> Body:
    return [
        todo_callout(
            lang,
            [
                "oilaviy shifokorlik punktlari;",
                "tuman poliklinikalari (onkologik ogohlik xonalari);",
                "Ona va bola salomatligi markazi va uning filiallari;",
                "davlat dasturi doirasida — bepul.",
            ],
            [
                "семейные врачебные пункты;",
                "районные поликлиники (кабинеты онконастороженности);",
                "Центр здоровья матери и ребенка и его филиалы;",
                "Бесплатно – в рамках государственной программы.",
            ],
        ),
        {
            "type": "institution_list",
            "value": {
                "title": t(
                    lang,
                    "Bepul skrining oʻtkaziladigan muassasalar",
                    "Учреждения с бесплатным скринингом",
                ),
                "region": "",
                "kind": "",
                "free_only": True,
                "limit": 20,
            },
        },
        cta(
            "",
            t(lang, "Barcha muassasalar va xarita", "Все учреждения и карта"),
            ctx.page_id("women.directory", lang),
        ),
    ]


def body_w_treatment(lang: str, ctx: SeedContext) -> Body:
    return [
        rich(
            p(
                t(
                    lang,
                    "Bemorning bosqichma-bosqich yoʻli — ilk belgilardan davolash boshlanishigacha. Xavotirni kamaytirish va qaror qabul qilishni tezlashtirish uchun aniq, tushunarli maʼlumot.",
                    "Пошаговый маршрут пациента — от первых симптомов до начала лечения. Ясная, доступная информация для снижения тревожности и ускорения принятия решений.",
                ),
                TODO,
            )
        ),
        steps(
            t(lang, "Bemor yoʻli", "Маршрут пациента"),
            [
                (
                    t(lang, "Birlamchi qabul", "Первичный прием"),
                    t(
                        lang,
                        "Ilk belgilar paydo boʻlganda yoki rejali tashrifda terapevt yoki ginekologga murojaat qiling.",
                        "Обратитесь к терапевту или гинекологу при первых признаках или при плановом визите.",
                    ),
                    "",
                ),
                (
                    t(lang, "Diagnostikaga yoʻllanma", "Направление на диагностику"),
                    t(
                        lang,
                        "UTT, mammografiya, tahlillar, «Onkologik ogohlik» xonasida qabul va boshqalar.",
                        "УЗИ, маммография, тесты, прием у кабинета «Онконастороженности» и др.",
                    ),
                    "",
                ),
                (
                    t(lang, "Onkolog / onkoginekolog", "Онколог / онкогинеколог"),
                    t(
                        lang,
                        "Tashxisga shubha qilinganda yoki u tasdiqlanganda — onkologiya markaziga yoʻllanma (PP-402 dagi muddatlarga muvofiq).",
                        "При подозрении или подтверждении диагноза — направление в онкологический центр (в соответствии с датами в ПП-402).",
                    ),
                    VERIFY_PP402,
                ),
                (
                    t(lang, "Davolash", "Лечение"),
                    t(
                        lang,
                        "Davolash bosqichlari haqida maʼlumot.",
                        "Информация об этапах лечения.",
                    ),
                    "",
                ),
            ],
        ),
        cta(
            t(lang, "Davolash davrida va undan keyin", "Во время лечения и после"),
            t(lang, "Parvarish va qoʻllab-quvvatlash", "Уход и поддержка"),
            ctx.page_id("women.care", lang),
        ),
        cta(
            "",
            t(lang, "Saratondan keyingi hayot", "Жизнь после рака"),
            ctx.page_id("women.after", lang),
        ),
    ]


def body_w_directory(lang: str, ctx: SeedContext) -> Body:
    return [
        callout(
            "info",
            t(lang, "Qayerga murojaat qilish", "Куда обратиться"),
            p(
                t(
                    lang,
                    "Muassasalar katalogi: xarita va roʻyxat, viloyat boʻyicha filtr.",
                    "Справочник учреждений: карта и список, фильтр по региону.",
                ),
                TODO,
            ),
        )
    ]


def body_w_state(lang: str, ctx: SeedContext) -> Body:
    return [
        todo_callout(
            lang,
            [
                "Davlat dasturi doirasida bepul skrining;",
                "«Onkologik ogohlik» xonalaridagi imkoniyatlar;",
                "Bemorlar va shifokorlarning huquq va majburiyatlari.",
            ],
            [
                "Бесплатный скрининг в рамках государственной программы;",
                "Возможности в кабинетах «Онконастороженности»;",
                "Права и обязанности пациентов и врачей.",
            ],
        ),
        cta(
            "",
            t(lang, "Parvarish va qoʻllab-quvvatlash", "Уход и поддержка"),
            ctx.page_id("women.care", lang),
        ),
    ]


def body_w_care(lang: str, ctx: SeedContext) -> Body:
    intro = t(
        lang,
        "Davolash davrida va undan keyin ayollar uchun amaliy maʼlumot va hissiy qoʻllab-quvvatlash — har bir bosqichda hayot sifatini saqlab qolish uchun.",
        "Практическая информация и эмоциональная поддержка для женщин во время и после лечения — чтобы сохранить качество жизни на каждом этапе.",
    )
    cols_ru = [
        (
            "Физическое здоровье",
            [
                "питание во время лечения;",
                "управление побочными эффектами;",
                "уход за кожей и волосами;",
                "физическая активность и реабилитация.",
            ],
        ),
        (
            "Эмоциональная поддержка",
            [
                "как справляться со страхом и тревогой;",
                "психологическая помощь: куда обратиться;",
                "поддержка близких и семьи;",
                "группы взаимопомощи пациентов.",
            ],
        ),
        (
            "Практические вопросы",
            [
                "больничный и трудовые права;",
                "финансовая поддержка и льготы;",
                "как помочь близкому человеку с диагнозом;",
                "вопросы, которые важно задать врачу.",
            ],
        ),
    ]
    cols_uz = [
        (
            "Jismoniy salomatlik",
            [
                "davolash davrida ovqatlanish;",
                "nojoʻya taʼsirlarni boshqarish;",
                "teri va soch parvarishi;",
                "jismoniy faollik va reabilitatsiya.",
            ],
        ),
        (
            "Hissiy qoʻllab-quvvatlash",
            [
                "qoʻrquv va xavotirni qanday yengish mumkin;",
                "psixologik yordam: qayerga murojaat qilish;",
                "yaqinlar va oila qoʻllab-quvvatlashi;",
                "bemorlarning oʻzaro yordam guruhlari.",
            ],
        ),
        (
            "Amaliy masalalar",
            [
                "kasallik varaqasi va mehnat huquqlari;",
                "moliyaviy qoʻllab-quvvatlash va imtiyozlar;",
                "tashxis qoʻyilgan yaqin insonga qanday yordam berish mumkin;",
                "shifokorga berish muhim boʻlgan savollar.",
            ],
        ),
    ]
    return [rich(p(intro, TODO)), columns("three_columns", cols_ru if lang == "ru" else cols_uz)]


def body_w_after(lang: str, ctx: SeedContext) -> Body:
    intro = t(
        lang,
        "Davolashning tugashi — bu yangi boshlanish. Ushbu boʻlim ayollarga toʻlaqonli hayotga qaytishga va koʻp yillar davomida salomatlikni saqlashga yordam beradi.",
        "Окончание лечения — это новое начало. Этот блок помогает женщинам вернуться к полноценной жизни и сохранить здоровье на долгие годы.",
    )
    cols_ru = [
        (
            "Наблюдение после лечения",
            [
                "график контрольных осмотров;",
                "поздние эффекты лечения;",
                "паспорт здоровья пациента.",
            ],
        ),
        (
            "Возвращение к жизни",
            [
                "возврат к работе и привычному ритму;",
                "физическая реабилитация;",
                "эмоциональное восстановление.",
            ],
        ),
        (
            "Долгосрочное здоровье",
            [
                "профилактика рецидива;",
                "репродуктивное здоровье после лечения;",
                "психологическое благополучие в долгосрочной перспективе.",
            ],
        ),
    ]
    cols_uz = [
        (
            "Davolashdan keyingi kuzatuv",
            [
                "nazorat koʻriklari jadvali;",
                "davolashning kechki taʼsirlari;",
                "bemorning salomatlik pasporti.",
            ],
        ),
        (
            "Hayotga qaytish",
            [
                "ishga va odatiy hayot tarziga qaytish;",
                "jismoniy reabilitatsiya;",
                "hissiy tiklanish.",
            ],
        ),
        (
            "Uzoq muddatli salomatlik",
            [
                "qaytalanish (retsidiv) profilaktikasi;",
                "davolashdan keyingi reproduktiv salomatlik;",
                "uzoq muddatli psixologik farovonlik.",
            ],
        ),
    ]
    return [rich(p(intro, TODO)), columns("three_columns", cols_ru if lang == "ru" else cols_uz)]


# ---------------------------------------------------------------------------
# CHILDREN — bodies
# ---------------------------------------------------------------------------
def body_c_types(lang: str, ctx: SeedContext) -> Body:
    items_ru = [
        ("Лейкозы", "Острый лимфобластный лейкоз (ОЛЛ); Острый миелолейкоз (ОМЛ)."),
        ("Лимфомы", "Лимфома Ходжкина; Неходжкинская лимфома. Поражают лимфатическую систему."),
        ("Опухоли мозга", "Медуллобластома; Астроцитома. Второй по частоте вид рака у детей."),
        ("Нейробластома", "Опухоль, возникающая из нервных клеток, чаще — надпочечников."),
        ("Саркомы", "Саркома мягких тканей и Юинга — поражают мышцы и кости."),
        ("Другие виды", "Опухоль Вилмса, ретинобластома, гепатобластома и другие редкие формы."),
    ]
    items_uz = [
        ("Leykozlar", "Oʻtkir limfoblast leykoz (OʻLL); Oʻtkir mieloleykoz (OʻML)."),
        (
            "Limfomalar",
            "Xodjkin limfomasi; Xodjkin boʻlmagan limfoma. Limfatik tizimni zararlaydi.",
        ),
        (
            "Miya oʻsmalari",
            "Medulloblastoma; Astrositoma. Bolalarda uchrash chastotasi boʻyicha ikkinchi saraton turi.",
        ),
        (
            "Neyroblastoma",
            "Nerv hujayralaridan, koʻpincha buyrak usti bezlaridan paydo boʻladigan oʻsma.",
        ),
        (
            "Sarkomalar",
            "Yumshoq toʻqima sarkomasi va Yuing sarkomasi — mushak va suyaklarni zararlaydi.",
        ),
        (
            "Boshqa turlari",
            "Vilms oʻsmasi, retinoblastoma, gepatoblastoma va boshqa kam uchraydigan shakllar.",
        ),
    ]
    items = [
        (title, f"{text} {VERIFY} {TODO}")
        for title, text in (items_ru if lang == "ru" else items_uz)
    ]
    return [
        cards(
            t(
                lang,
                "Bolalarda eng koʻp uchraydigan saraton turlari",
                "Наиболее распространённые виды рака у детей",
            ),
            items,
        ),
    ]


def body_c_team(lang: str, ctx: SeedContext) -> Body:
    roles = [
        (t(lang, "Pediatr", "Педиатр"), TODO),
        (t(lang, "Onkolog", "Онколог"), TODO),
        (t(lang, "Hamshira", "Медсестра"), TODO),
        (t(lang, "Psixolog", "Психолог"), TODO),
    ]
    return [
        todo_callout(
            lang,
            ["bolalar onkologik jamoasi qanday ishlaydi (pediatr, onkolog, hamshira, psixolog)"],
            ["как работает детская онкологическая команда (педиатр, онколог, медсестра, психолог)"],
        ),
        cards(t(lang, "Jamoa", "Команда"), roles),
    ]


def body_c_genetics(lang: str, ctx: SeedContext) -> Body:
    return [
        todo_callout(
            lang,
            ["irsiy xavf va genetik test: oilani qachon tekshirish kerak"],
            ["наследственный риск и генетическое тестирование: когда стоит проверить семью"],
        )
    ]


def body_c_stats(lang: str, ctx: SeedContext) -> Body:
    return [
        todo_callout(
            lang,
            [
                "Oʻzbekiston boʻyicha statistika: tarqalganlik, tendensiyalar (masalan, bolalarni pestitsidlardan asrash va h.k.)"
            ],
            [
                "статистика по Узбекистану: распространенность, тренды (к примеру, беречь детей от пестицидов и т.д.)"
            ],
        ),
        stat("—", t(lang, f"{TODO} tarqalganlik", f"{TODO} распространенность")),
        stat("—", t(lang, f"{TODO} tendensiyalar", f"{TODO} тренды")),
        stat("—", t(lang, f"{TODO} profilaktika", f"{TODO} профилактика")),
    ]


def body_c_diagnostics(lang: str, ctx: SeedContext) -> Body:
    terms = ctx.terms.get(lang, [])
    body: Body = [
        todo_callout(
            lang,
            [
                "laboratoriya tahlillari: ular nimani koʻrsatadi;",
                "KT, MRT, PET — nima uchun kerak va qanday oʻtkaziladi;",
                "biopsiya va gistologik tekshiruv;",
                "natijalarni qanday oʻqish kerak: ota-onalar uchun lugʻat;",
                "shifokorga berish muhim boʻlgan savollar.",
            ],
            [
                "лабораторные анализы: что они показывают;",
                "КТ, МРТ, ПЭТ — зачем нужны и как проходят;",
                "биопсия и гистологическое исследование;",
                "как читать результаты: словарь для родителей;",
                "вопросы, которые важно задать врачу.",
            ],
        ),
    ]
    if terms:
        body.append(
            {
                "type": "glossary_terms",
                "value": {
                    "title": t(
                        lang,
                        "Natijalarni qanday oʻqish kerak: ota-onalar uchun lugʻat",
                        "Как читать результаты: словарь для родителей",
                    ),
                    "terms": terms,
                },
            }
        )
    body.append(
        faq(
            t(
                lang,
                "Shifokorga berish muhim boʻlgan savollar",
                "Вопросы, которые важно задать врачу",
            ),
            [(f"{TODO} {t(lang, 'savol', 'вопрос')} {n}", VERIFY) for n in range(1, 4)],
        )
    )
    return body


def body_c_treatment(lang: str, ctx: SeedContext) -> Body:
    return [
        todo_callout(
            lang,
            [
                "kimyoterapiya: qanday ishlaydi, nojoʻya taʼsirlari",
                "bolalarda nur terapiyasi",
                "suyak iligi transplantatsiyasi",
                "immunoterapiya va nishonli (targetli) terapiya",
                "klinik sinovlar: bu nima va qanday qatnashish mumkin.",
            ],
            [
                "химиотерапия: как работает, побочные эффекты",
                "лучевая терапия у детей",
                "трансплантация костного мозга",
                "иммунотерапия и таргетная терапия",
                "клинические испытания: что это и как попасть.",
            ],
        )
    ]


def body_c_care(lang: str, ctx: SeedContext) -> Body:
    intro = t(
        lang,
        "Davolash davrida bolani parvarish qilish boʻyicha amaliy tavsiyalar — butun oilaning jismoniy va hissiy farovonligi.",
        "Практические рекомендации по уходу за ребенком во время лечения – физическое и эмоциональное благополучие всей семьи.",
    )
    cols_ru = [
        (
            "Физический уход",
            [
                "питание во время химиотерапии;",
                "управление болью;",
                "инфекционная безопасность;",
                "центральные венозные катетеры.",
            ],
        ),
        (
            "Эмоциональная поддержка",
            [
                "как говорить с ребенком о болезни;",
                "работа с тревогой у родителей",
                "поддержка братьев и сестер;",
                "психологические службы.",
            ],
        ),
        (
            "Практические вопросы",
            [
                "обучение в больнице;",
                "финансовая помощь семьям;",
                "права ребенка-пациента;",
                "группы поддержки.",
            ],
        ),
    ]
    cols_uz = [
        (
            "Jismoniy parvarish",
            [
                "kimyoterapiya davrida ovqatlanish;",
                "ogʻriqni boshqarish;",
                "infeksiya xavfsizligi;",
                "markaziy venoz kateterlar.",
            ],
        ),
        (
            "Hissiy qoʻllab-quvvatlash",
            [
                "bola bilan kasallik haqida qanday gaplashish kerak;",
                "ota-onalardagi xavotir bilan ishlash;",
                "aka-uka va opa-singillarni qoʻllab-quvvatlash;",
                "psixologik xizmatlar.",
            ],
        ),
        (
            "Amaliy masalalar",
            [
                "kasalxonada oʻqish;",
                "oilalarga moliyaviy yordam;",
                "bemor bolaning huquqlari;",
                "qoʻllab-quvvatlash guruhlari.",
            ],
        ),
    ]
    return [rich(p(intro, TODO)), columns("three_columns", cols_ru if lang == "ru" else cols_uz)]


def body_c_family(lang: str, ctx: SeedContext) -> Body:
    intro = t(
        lang,
        "Bolaning saratoni — butun oila uchun sinov. Boʻlim yaqinlarga kuch saqlab qolish, qoʻllab-quvvatlash topish va bola uchun haqiqiy jamoaga aylanishga yordam berishga qaratilgan.",
        "Информация о том, что рак ребенка – это испытание для всей семьи. Раздел направлен на предоставление вспомогательной помощи близким сохранить силы, найти поддержку и стать настоящей командой для ребенка.",
    )
    cols_ru = [
        (
            "Для родителей",
            [
                "как справляться с эмоциями и не выгореть;",
                "уход за собой во время лечения ребенка;",
                "как общаться с медицинской командой;",
                "совместное принятие решений о лечении;",
                "ресурсы юридической и финансовой помощи.",
            ],
        ),
        (
            "Для близких",
            [
                "как помочь, когда не знаешь, что сказать;",
                "практическая помощь: что реально нужно семье;",
                "поддержка братьев и сестер больного ребенка;",
                "разговоры с бабушками и дедушками;",
                "сообщество семей — группы взаимопомощи.",
            ],
        ),
    ]
    cols_uz = [
        (
            "Ota-onalar uchun",
            [
                "hissiyotlarni qanday boshqarish va kuyib bitmaslik;",
                "bolani davolash davrida oʻziga gʻamxoʻrlik qilish;",
                "tibbiy jamoa bilan qanday muloqot qilish;",
                "davolash boʻyicha qarorlarni birgalikda qabul qilish;",
                "yuridik va moliyaviy yordam resurslari.",
            ],
        ),
        (
            "Yaqinlar uchun",
            [
                "nima deyishni bilmaganda qanday yordam berish mumkin;",
                "amaliy yordam: oilaga aslida nima kerak;",
                "bemor bolaning aka-uka va opa-singillarini qoʻllab-quvvatlash;",
                "buvi va bobolar bilan suhbatlar;",
                "oilalar hamjamiyati — oʻzaro yordam guruhlari.",
            ],
        ),
    ]
    return [rich(p(intro, TODO)), columns("two_columns", cols_ru if lang == "ru" else cols_uz)]


def body_c_after(lang: str, ctx: SeedContext) -> Body:
    intro = t(
        lang,
        "Davolashning tugashi — bu yangi boshlanish. Ushbu boʻlim bolalar va ularning oilalariga onkologiyadan keyin toʻlaqonli hayotga oʻtishga yordam beradi.",
        "Окончание лечения – это новое начало. Этот блок помогает детям и их семьям перейти к полноценной жизни после онкологии.",
    )
    cols_ru = [
        (
            "Наблюдение после лечения",
            [
                "график контрольных осмотров;",
                "поздние эффекты терапии;",
                "паспорт здоровья выжившего.",
            ],
        ),
        (
            "Возвращение к жизни",
            [
                "возврат в школу и учеба;",
                "физическая реабилитация;",
                "эмоциональное восстановление.",
            ],
        ),
        (
            "Долгосрочное здоровье",
            ["рост и развитие;", "репродуктивное здоровье;", "профилактика рецидива."],
        ),
    ]
    cols_uz = [
        (
            "Davolashdan keyingi kuzatuv",
            [
                "nazorat koʻriklari jadvali;",
                "terapiyaning kechki taʼsirlari;",
                "omon qolgan bemorning salomatlik pasporti.",
            ],
        ),
        (
            "Hayotga qaytish",
            ["maktabga qaytish va oʻqish;", "jismoniy reabilitatsiya;", "hissiy tiklanish."],
        ),
        (
            "Uzoq muddatli salomatlik",
            ["oʻsish va rivojlanish;", "reproduktiv salomatlik;", "qaytalanish profilaktikasi."],
        ),
    ]
    return [rich(p(intro, TODO)), columns("three_columns", cols_ru if lang == "ru" else cols_uz)]


# ---------------------------------------------------------------------------
# Section intros
# ---------------------------------------------------------------------------
def intro_women(lang: str, ctx: SeedContext) -> Body:
    return [
        callout(
            "info",
            t(lang, "Boʻlimning asosiy maqsadi", "Ключевая цель раздела"),
            p(
                t(
                    lang,
                    "Ayollar va ularning yaqinlarining xabardorligini oshirish, onkologik kasalliklarning ilk belgilarini tanib olish va shifokorga tashrifni kechiktirmaslik.",
                    "Повысить осведомленность женщин и их близких, а также их распознавать первые признаки онкологических заболеваний и не откладывать визит к врачу.",
                ),
                TODO,
            ),
        )
    ]


def intro_children(lang: str, ctx: SeedContext) -> Body:
    return [
        callout(
            "info",
            t(lang, "Boʻlimning asosiy maqsadi", "Ключевая цель раздела"),
            p(
                t(
                    lang,
                    "Bolalar onkologiyasi kattalarnikidan farq qiladi — kasallik turlari boʻyicha ham, davolash yondashuvlari boʻyicha ham. Ushbu boʻlim oilalarga tashxisni tushunishga va dastlabki muhim kunlarda sarosimaga tushmaslikka yordam beradi.",
                    "Донести информацию, что Детская онкология отличается от взрослой — как по видам заболеваний, так и по подходам к лечению. Этот блок помогает семьям понять диагноз и не растеряться в первые критические дни.",
                ),
                t(
                    lang,
                    "Boʻlim tuzilmasi Sent-Jud universiteti (AQSH) va uning «Together» loyihasi tajribasi hamda PP-186 asosida yaratilgan.",
                    "Структура раздела создана на основе опыта университета Сент Джуд (США) и его проекта «Вместе», в соответствии с ПП-186.",
                ),
                TODO,
            ),
        )
    ]


# ---------------------------------------------------------------------------
# THE TREE
# ---------------------------------------------------------------------------
def _wf(name: str) -> BodyBuilder:
    """Body builder from `women_figma` resolved at call time (that module imports this one)."""

    def build(lang: Lang, ctx: SeedContext) -> Body:
        from apps.core.seed import women_figma

        body: Body = getattr(women_figma, name)(lang, ctx)
        return body

    build.__name__ = name
    return build


def _variants(key: str, breast: BodyBuilder, cervical: BodyBuilder) -> list[Node]:
    """Breast / cervical pages of one women's topic (Figma switch, D-066)."""
    return [
        Node(
            key=f"{key}.breast",
            kind="article",
            title={"uz": "Koʻkrak bezi saratoni", "ru": "Рак молочной железы"},
            slug={"uz": "kokrak-bezi-saratoni", "ru": "rak-molochnoy-zhelezy"},
            summary={
                "uz": "Koʻkrak bezi saratoni (KBS) haqida tushunarli maʼlumot.",
                "ru": "Понятная информация о раке молочной железы (РМЖ).",
            },
            body=breast,
        ),
        Node(
            key=f"{key}.cervical",
            kind="article",
            title={"uz": "Bachadon boʻyni saratoni", "ru": "Рак шейки матки"},
            slug={"uz": "bachadon-boyni-saratoni", "ru": "rak-sheyki-matki"},
            summary={
                "uz": "Bachadon boʻyni saratoni (BBS) haqida tushunarli maʼlumot.",
                "ru": "Понятная информация о раке шейки матки (РШМ).",
            },
            body=cervical,
        ),
    ]


def _women_topic(
    key: str,
    title: dict[str, str],
    slug: dict[str, str],
    summary: dict[str, str],
    breast: BodyBuilder,
    cervical: BodyBuilder,
) -> Node:
    return Node(
        key=key,
        kind="topic",
        title=title,
        slug=slug,
        summary=summary,
        children=_variants(key, breast, cervical),
        extra={"fields": {"is_variant_group": True}},
    )


# Figma navigation (D-064): five tabs, each with a breast / cervical page; the TZ «Куда
# обратиться» directory is the target of every «Murojaat qilish» button, «Государственная
# поддержка» and «Уход и поддержка» live on «Qoʻllab-quvvatlash».
WOMEN = Node(
    key="women",
    kind="section",
    title={"uz": "Ayollar saratoni", "ru": "Женский рак"},
    slug={"uz": "ayollar", "ru": "zhenskiy"},
    summary={
        "uz": "Koʻkrak bezi va bachadon boʻyni saratoni: xabardorlik, skrining, davolash",
        "ru": "Рак молочной железы и рак шейки матки: осведомленность, скрининг, лечение",
    },
    body=intro_women,
    extra={"section_key": "women", "icon": "ribbon-women", "fields": {"open_first_topic": True}},
    children=[
        _women_topic(
            "women.awareness",
            {"uz": "Xabardorlik", "ru": "Осведомленность"},
            {"uz": "ogohlik", "ru": "osvedomlennost"},
            {
                "uz": "Kasallik nima, bosqichlari, sabablari, belgilari va oʻz-oʻzini tekshirish",
                "ru": "Что это за болезнь, стадии, причины, признаки и самообследование",
            },
            _wf("body_breast_awareness"),
            _wf("body_cervical_awareness"),
        ),
        _women_topic(
            "women.screening",
            {"uz": "Skrining", "ru": "Скрининг"},
            {"uz": "skrining", "ru": "skrining"},
            {
                "uz": "Skrining nima, usullari, kimga va qanchalik tez-tez, qayerda — bepul",
                "ru": "Что такое скрининг, методы, кому и как часто, где — бесплатно",
            },
            _wf("body_breast_screening"),
            _wf("body_cervical_screening"),
        ),
        _women_topic(
            "women.treatment",
            {"uz": "Davolashni tashkil etish", "ru": "Организация лечения"},
            {"uz": "davolash", "ru": "organizatsiya-lecheniya"},
            {
                "uz": "Bemorning bosqichma-bosqich yoʻli — ilk belgilardan davolash boshlanishigacha.",
                "ru": "Пошаговый маршрут пациента — от первых симптомов до начала лечения.",
            },
            _wf("body_breast_treatment"),
            _wf("body_cervical_treatment"),
        ),
        _women_topic(
            "women.support",
            {"uz": "Qoʻllab-quvvatlash", "ru": "Поддержка"},
            {"uz": "qollab-quvvatlash", "ru": "podderzhka"},
            {
                "uz": "Bepul skrining, onkologik hushyorlik xonalari, huquq va majburiyatlar, parvarish.",
                "ru": "Бесплатный скрининг, кабинеты онконастороженности, права и обязанности, уход.",
            },
            _wf("body_support"),
            _wf("body_support"),
        ),
        _women_topic(
            "women.after",
            {"uz": "Kasallikdan keyingi hayot", "ru": "Жизнь после рака"},
            {"uz": "saratondan-keyingi-hayot", "ru": "zhizn-posle-raka"},
            {
                "uz": "Davolashning tugashi — bu yangi boshlanish.",
                "ru": "Окончание лечения — это новое начало.",
            },
            _wf("body_after"),
            _wf("body_after"),
        ),
        Node(
            key="women.directory",
            kind="directory",
            title={"uz": "Qayerga murojaat qilish", "ru": "Куда обратиться"},
            slug={"uz": "qayerga-murojaat", "ru": "kuda-obratitsya"},
            summary={
                "uz": "Muassasalar katalogi: xarita va roʻyxat, viloyat boʻyicha filtr",
                "ru": "Справочник учреждений: карта и список, фильтр по региону",
            },
            body=body_w_directory,
            show_in_menus=False,
        ),
    ],
)

# Pages of the pre-Figma women's tree (M1…M5b), removed by the seeder with a permanent redirect
# from their old URL to the page that now carries their content (D-064).
RETIRED: list[dict[str, Any]] = [
    {
        "parent": "women.awareness",
        "slug": {"uz": "saraton-nima", "ru": "chto-takoe-rmzh-i-rshm"},
        "to": "women.awareness.breast",
    },
    {
        "parent": "women.awareness",
        "slug": {"uz": "xavf-omillari", "ru": "faktory-riska"},
        "to": "women.awareness.breast",
    },
    {
        "parent": "women.awareness",
        "slug": {"uz": "belgilar", "ru": "simptomy"},
        "to": "women.awareness.breast",
    },
    {
        "parent": "women.screening",
        "slug": {"uz": "kimga-va-qachon", "ru": "komu-i-kak-chasto"},
        "to": "women.screening.breast",
    },
    {
        "parent": "women.screening",
        "slug": {"uz": "qayerda", "ru": "gde-proyti"},
        "to": "women.screening.breast",
    },
    {
        "parent": "women",
        "slug": {"uz": "davolash", "ru": "organizatsiya-lecheniya"},
        "kind": "article",
        "to": "women.treatment.breast",
    },
    {
        "parent": "women",
        "slug": {"uz": "davlat-yordami", "ru": "gosudarstvennaya-podderzhka"},
        "to": "women.support.breast",
    },
    {
        "parent": "women",
        "slug": {"uz": "parvarish", "ru": "uhod-i-podderzhka"},
        "to": "women.support.breast",
    },
    {
        "parent": "women",
        "slug": {"uz": "saratondan-keyingi-hayot", "ru": "zhizn-posle-raka"},
        "kind": "article",
        "to": "women.after.breast",
    },
]

CHILDREN = Node(
    key="children",
    kind="section",
    title={"uz": "Bolalar saratoni", "ru": "Детский рак"},
    slug={"uz": "bolalar", "ru": "detskiy"},
    summary={
        "uz": "Bolalardagi onkologik kasalliklar: ilk belgilar, turlari, diagnostika, davolash, saratondan keyingi hayot",
        "ru": "Онкологические заболевания у детей: первые симптомы, виды, диагностика, лечение, жизнь после рака",
    },
    body=intro_children,
    extra={"section_key": "children", "icon": "ribbon-children"},
    children=[
        Node(
            key="children.about",
            kind="topic",
            title={
                "uz": "Bolalardagi onkologik kasalliklar haqida",
                "ru": "Об онкозаболеваниях у детей",
            },
            slug={"uz": "onkologiya-haqida", "ru": "ob-onkozabolevaniyah-u-detey"},
            summary={
                "uz": "Bolalar onkologiyasi kattalarnikidan farq qiladi — kasallik turlari boʻyicha ham, davolash yondashuvlari boʻyicha ham.",
                "ru": "Детская онкология отличается от взрослой — как по видам заболеваний, так и по подходам к лечению.",
            },
            children=[
                Node(
                    key="children.about.types",
                    kind="article",
                    title={
                        "uz": "Eng koʻp uchraydigan turlari",
                        "ru": "Наиболее распространённые виды",
                    },
                    slug={"uz": "keng-tarqalgan-turlari", "ru": "rasprostranennye-vidy"},
                    summary={
                        "uz": "Leykozlar, limfomalar, miya oʻsmalari, neyroblastoma, sarkomalar va boshqa turlari.",
                        "ru": "Лейкозы, лимфомы, опухоли мозга, нейробластома, саркомы и другие виды.",
                    },
                    body=body_c_types,
                ),
                Node(
                    key="children.about.team",
                    kind="article",
                    title={
                        "uz": "Bolalar onkologik jamoasi qanday ishlaydi",
                        "ru": "Как работает детская онкокоманда",
                    },
                    slug={"uz": "onkojamoa", "ru": "onkokomanda"},
                    summary={
                        "uz": "Pediatr, onkolog, hamshira, psixolog — kim nima uchun javob beradi.",
                        "ru": "Педиатр, онколог, медсестра, психолог — кто за что отвечает.",
                    },
                    body=body_c_team,
                ),
                Node(
                    key="children.about.genetics",
                    kind="article",
                    title={
                        "uz": "Irsiy xavf va genetik test",
                        "ru": "Наследственный риск и генетическое тестирование",
                    },
                    slug={"uz": "irsiy-xavf", "ru": "nasledstvennyy-risk"},
                    summary={
                        "uz": "Oilani qachon tekshirish kerak.",
                        "ru": "Когда стоит проверить семью.",
                    },
                    body=body_c_genetics,
                ),
                Node(
                    key="children.about.stats",
                    kind="article",
                    title={
                        "uz": "Oʻzbekiston boʻyicha statistika",
                        "ru": "Статистика по Узбекистану",
                    },
                    slug={"uz": "statistika", "ru": "statistika"},
                    summary={
                        "uz": "Tarqalganlik, tendensiyalar, profilaktika.",
                        "ru": "Распространенность, тренды, профилактика.",
                    },
                    body=body_c_stats,
                ),
            ],
        ),
        Node(
            key="children.diagnosis",
            kind="topic",
            title={"uz": "Diagnostika va davolash", "ru": "Диагностика и лечение"},
            slug={"uz": "diagnostika-va-davolash", "ru": "diagnostika-i-lechenie"},
            summary={
                "uz": "Bolalar onkologik kasalliklarini tashxislash va davolashning barcha bosqichlarining tushunarli izohi — ota-onalar va bolaning yaqinlari uchun.",
                "ru": "Понятное объяснение всех этапов диагностики и лечения детских онкологических заболеваний — для родителей и близких ребенка.",
            },
            children=[
                Node(
                    key="children.diagnosis.diagnostics",
                    kind="article",
                    title={"uz": "Diagnostika", "ru": "Диагностика"},
                    slug={"uz": "diagnostika", "ru": "diagnostika"},
                    summary={
                        "uz": "Tahlillar, KT/MRT/PET, biopsiya, natijalarni oʻqish, shifokorga savollar.",
                        "ru": "Анализы, КТ/МРТ/ПЭТ, биопсия, чтение результатов, вопросы врачу.",
                    },
                    body=body_c_diagnostics,
                ),
                Node(
                    key="children.diagnosis.treatment",
                    kind="article",
                    title={"uz": "Davolash", "ru": "Лечение"},
                    slug={"uz": "davolash", "ru": "lechenie"},
                    summary={
                        "uz": "Kimyoterapiya, nur terapiyasi, suyak iligi transplantatsiyasi, immunoterapiya, klinik sinovlar.",
                        "ru": "Химиотерапия, лучевая терапия, трансплантация костного мозга, иммунотерапия, клинические испытания.",
                    },
                    body=body_c_treatment,
                ),
            ],
        ),
        Node(
            key="children.care",
            kind="article",
            title={"uz": "Parvarish va qoʻllab-quvvatlash", "ru": "Уход и поддержка"},
            slug={"uz": "parvarish", "ru": "uhod-i-podderzhka"},
            summary={
                "uz": "Davolash davrida bolani parvarish qilish boʻyicha amaliy tavsiyalar.",
                "ru": "Практические рекомендации по уходу за ребенком во время лечения.",
            },
            body=body_c_care,
        ),
        Node(
            key="children.family",
            kind="article",
            title={"uz": "Oila uchun maʼlumot", "ru": "Информация для семьи"},
            slug={"uz": "oila-uchun", "ru": "informatsiya-dlya-semi"},
            summary={
                "uz": "Bolaning saratoni — butun oila uchun sinov. Ota-onalar va yaqinlar uchun.",
                "ru": "Рак ребенка – это испытание для всей семьи. Для родителей и близких.",
            },
            body=body_c_family,
        ),
        Node(
            key="children.after",
            kind="article",
            title={"uz": "Saratondan keyingi hayot", "ru": "Жизнь после рака"},
            slug={"uz": "saratondan-keyingi-hayot", "ru": "zhizn-posle-raka"},
            summary={
                "uz": "Davolashning tugashi — bu yangi boshlanish.",
                "ru": "Окончание лечения – это новое начало.",
            },
            body=body_c_after,
        ),
    ],
)


def intro_stories(lang: str, ctx: SeedContext) -> Body:
    return [
        callout(
            "info",
            t(lang, "Haqiqiy bemorlar hikoyalari", "Истории реальных пациентов"),
            p(
                t(
                    lang,
                    "Har bir hikoya faqat inson (voyaga yetmaganlar uchun — qonuniy vakili) yozma roziligi bilan eʼlon qilinadi.",
                    "Каждая история публикуется только с письменного согласия человека (для несовершеннолетних — законного представителя).",
                ),
                TODO,
            ),
        )
    ]


STORIES = Node(
    key="stories",
    kind="stories",
    title={"uz": "Bemorlar hikoyalari", "ru": "Истории пациентов"},
    slug={"uz": "hikoyalar", "ru": "istorii"},
    summary={
        "uz": "Haqiqiy bemorlar hikoyalari — rozilik bilan",
        "ru": "Истории реальных пациентов — с согласия",
    },
    body=intro_stories,
)


# ---------------------------------------------------------------------------
# Tools (A1, A2), FAQ (A3), feedback (F5), glossary (F14) — root-level pages
# ---------------------------------------------------------------------------
PLACEHOLDER_HTML = f"<p>{TODO} {VERIFY}</p>"


def _where_page(lang: str, ctx: SeedContext) -> int | None:
    return ctx.page_id("women.directory", lang)


def intro_tools(lang: str, ctx: SeedContext) -> Body:
    return [
        callout(
            "info",
            t(lang, "Bu asboblar tashxis qoʻymaydi", "Эти инструменты не ставят диагноз"),
            p(
                t(
                    lang,
                    "Ular faqat keyingi qadamni tanlashga yordam beradi: qachon skriningga borish, shifokorga qachon murojaat qilish. Hech narsa saqlanmaydi.",
                    "Они лишь помогают выбрать следующий шаг: когда идти на скрининг, когда обратиться к врачу. Ничего не сохраняется.",
                ),
                TODO,
            ),
        )
    ]


def selfcheck_items(lang: str, ctx: SeedContext) -> Body:
    """Placeholder checklist items — doctors define the real signs (never written by us)."""
    labels = {
        "uz": ["belgi", "belgi", "belgi"],
        "ru": ["признак", "признак", "признак"],
    }[lang if lang in ("uz", "ru") else "uz"]
    return [
        {
            "type": "item",
            "value": {"text": f"{TODO} {labels[i]} {i + 1} {VERIFY}", "urgency": urgency},
        }
        for i, urgency in enumerate(["urgent", "soon", "routine"])
    ]


SCREENING_FIELDS = {
    "text_due": PLACEHOLDER_HTML,
    "text_ok": PLACEHOLDER_HTML,
    "text_not_applicable": PLACEHOLDER_HTML,
    "text_hpv_interval": PLACEHOLDER_HTML,
    "disclaimer": "",
    "where_page_id": _where_page,
}
SELFCHECK_FIELDS = {
    "result_none": PLACEHOLDER_HTML,
    "result_routine": PLACEHOLDER_HTML,
    "result_soon": PLACEHOLDER_HTML,
    "result_urgent": PLACEHOLDER_HTML,
    "disclaimer": "",
    "where_page_id": _where_page,
}

TOOLS = Node(
    key="tools",
    kind="tools",
    title={"uz": "Foydali asboblar", "ru": "Полезные инструменты"},
    slug={"uz": "vositalar", "ru": "instrumenty"},
    summary={
        "uz": "Skrining kerakmi? Belgilarni tekshirish — keyingi qadamni tanlashga yordam",
        "ru": "Пора ли на скрининг? Проверка признаков — помощь в выборе следующего шага",
    },
    body=intro_tools,
    children=[
        Node(
            key="tools.screening",
            kind="screening",
            title={"uz": "Menga skrining kerakmi?", "ru": "Пора ли мне на скрининг?"},
            slug={"uz": "skrining", "ru": "skrining"},
            summary={
                "uz": "Yoshingiz va oxirgi tekshiruvlaringizga qarab — qaysi test va qachon (mammografiya 45–65, UTT 45 gacha, HPV 30–50).",
                "ru": "По возрасту и дате последних обследований — какой тест и когда (маммография 45–65, УЗИ до 45, ВПЧ 30–50).",
            },
            extra={"fields": SCREENING_FIELDS},
        ),
        Node(
            key="tools.selfcheck_women",
            kind="selfcheck",
            title={"uz": "Belgilarni oʻzim tekshiraman", "ru": "Проверить симптомы"},
            slug={"uz": "oz-tekshiruv", "ru": "samoproverka"},
            summary={
                "uz": "Ayollar uchun belgilar roʻyxati: nimani sezganingizni belgilang — shifokorga qachon borishni bilib oling.",
                "ru": "Чек-лист симптомов для женщин: отметьте, что заметили — узнайте, когда идти к врачу.",
            },
            extra={
                "fields": {**SELFCHECK_FIELDS, "kind": "women"},
                "streams": {"items": selfcheck_items},
            },
        ),
        Node(
            key="tools.selfcheck_children",
            kind="selfcheck",
            title={"uz": "Bolalardagi xavotirli belgilar", "ru": "Тревожные признаки у ребёнка"},
            slug={"uz": "bolalar-belgilari", "ru": "priznaki-u-detey"},
            summary={
                "uz": "Ota-onalar uchun roʻyxat: bolangizda sezgan belgilarni belgilang.",
                "ru": "Чек-лист для родителей: отметьте признаки, которые заметили у ребёнка.",
            },
            extra={
                "fields": {**SELFCHECK_FIELDS, "kind": "children"},
                "streams": {"items": selfcheck_items},
            },
        ),
    ],
)

FAQ = Node(
    key="faq",
    kind="faq",
    title={"uz": "Shifokorga savol", "ru": "Вопрос врачу"},
    slug={"uz": "savol-javob", "ru": "voprosy-otvety"},
    summary={
        "uz": "Savol bering — shifokorlar javob beradi. Javoblar anonim eʼlon qilinadi.",
        "ru": "Задайте вопрос — ответят врачи. Ответы публикуются анонимно.",
    },
    extra={
        "fields": {
            "form_intro": f"<p>{TODO}</p>",
            "thanks_text": lambda lang, ctx: p(
                t(
                    lang,
                    "Rahmat! Shifokorlar javobini tayyorlagach, u (roziligingiz bilan) shu sahifada anonim eʼlon qilinadi.",
                    "Спасибо! Когда врачи подготовят ответ, он (с вашего согласия) будет анонимно опубликован на этой странице.",
                ),
                TODO,
            ),
        }
    },
)

FEEDBACK = Node(
    key="feedback",
    kind="feedback",
    title={"uz": "Qayta aloqa", "ru": "Обратная связь"},
    slug={"uz": "qayta-aloqa", "ru": "obratnaya-svyaz"},
    summary={
        "uz": "Sayt haqida fikr, xatolik yoki hamkorlik taklifi",
        "ru": "Отзыв о сайте, ошибка или предложение о сотрудничестве",
    },
    extra={"fields": {"thanks_text": f"<p>{TODO}</p>"}},
)

GLOSSARY = Node(
    key="glossary",
    kind="glossary",
    title={"uz": "Lugʻat", "ru": "Словарь"},
    slug={"uz": "lugat", "ru": "slovar"},
    summary={
        "uz": "Tibbiy atamalar oddiy tilda — ota-onalar va bemorlar uchun",
        "ru": "Медицинские термины простыми словами — для родителей и пациентов",
    },
)

MATERIALS = Node(
    key="materials",
    kind="materials",
    title={"uz": "Tarqatish uchun materiallar", "ru": "Материалы для распространения"},
    slug={"uz": "materiallar", "ru": "materialy"},
    summary={
        "uz": "Bloger-koʻngillilar, oila aʼzolari va klinikalar uchun infografika, qisqa videolar, tayyor matnlar va xeshteglar",
        "ru": "Инфографика, короткие видео, готовые подписи и хэштеги для блогеров-волонтёров, семей и клиник",
    },
    body=lambda lang, ctx: [
        callout(
            "info",
            t(lang, "Bu materiallardan erkin foydalaning", "Используйте эти материалы свободно"),
            p(
                t(
                    lang,
                    "Yuklab oling, ijtimoiy tarmoqlarda tarqating, klinikada chop eting. Manba: ertaaniqla.uz.",
                    "Скачивайте, распространяйте в соцсетях, печатайте в клинике. Источник: ertaaniqla.uz.",
                ),
                TODO,
            ),
        )
    ],
)

TREE: list[Node] = [WOMEN, CHILDREN, STORIES, TOOLS, FAQ, FEEDBACK, GLOSSARY, MATERIALS]

HOME = {
    "title": {"uz": "Erta aniqla", "ru": "Эрта аниқла"},
    "slug": {"uz": "erta-aniqla", "ru": "erta-aniqla"},
    "hero_title": {"uz": "Erta aniqla", "ru": "Эрта аниқла"},
    "hero_subtitle": {
        "uz": f"Portalning asosiy gʻoyasi — erta aniqlash. Tushunarli tilda ishonchli tibbiy maʼlumotlar. {TODO}",
        "ru": f"Ключевая идея портала — раннее выявление. Достоверная медицинская информация на понятном языке. {TODO}",
    },
    # <meta name="description"> of the home page (site description, not medical content)
    "search_description": {
        "uz": "Ayollar va bolalar saratonini erta aniqlash haqida ishonchli maʼlumot: belgilar, skrining, bemor yoʻli, qayerga murojaat qilish.",
        "ru": "Достоверная информация о раннем выявлении женского и детского рака: симптомы, скрининг, маршрут пациента, куда обратиться.",
    },
}

GLOSSARY_TERMS = [
    {"uz": ("Biopsiya", "biopsiya, биопсия"), "ru": ("Биопсия", "biopsiya")},
    {
        "uz": ("Gistologiya", "gistologik tekshiruv, гистология"),
        "ru": ("Гистология", "gistologiya"),
    },
    {"uz": ("Remissiya", "ремиссия"), "ru": ("Ремиссия", "remissiya")},
]

# short URLs from spec §4.4 → seeded page keys (Wagtail redirects)
REDIRECTS = {
    "women.directory": {"uz": "/uz/qayerga-murojaat/", "ru": "/ru/kuda-obratitsya/"},
}


def iter_nodes(nodes: list[Node] | None = None) -> list[Node]:
    result: list[Node] = []
    for node in nodes if nodes is not None else TREE:
        result.append(node)
        result.extend(iter_nodes(node.children))
    return result
