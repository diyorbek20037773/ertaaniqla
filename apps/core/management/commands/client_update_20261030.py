"""One-off: the expert review of 2026-10-26 and the doctor's «Читка» (D-106). Run once after the
deploy (`--dry-run` first lists what would change):

    python manage.py client_update_20261030 [--dry-run]

Texts (uz and ru, wherever they appear on a live page):
* cervical screening: the PQ-402 cohorts (30, 40 and 50-year-olds, not «every year from 30 to
  50»), the 10-year interval, «HPV positive is not a diagnosis»; ultrasound for 30–44;
* breast treatment: no «radiotherapy after menopause, chemotherapy before» rule, how treatment is
  chosen instead of the unsourced «metastases in the first 3–5 years»; «oncologist or
  mammologist-oncologist»; the empty «Muddat:» field goes;
* cervical awareness: «glandular epithelium» instead of «bezi jigarrang», persistent high-risk HPV
  as the cause, ectopy («erosion») is not a precancer; the cervical FAQ quotes the cervical
  programme, not the breast one;
* «Biz haqimizda» and the home page say the children's section is planned, not open.

Structure:
* cervical awareness: infections and vitamin deficiency move to a group of their own under
  «Mahalliy immunitet pasayishi sabablari» (the doctor's «Читка»);
* breast screening: the state programme (the expert's text over the TZ table) first, a «do not
  wait for screening» note, then the international recommendations under their own title;
* cervical screening: «Natija olingandan keyin» after the screening route.

The same FAQ answers on the «Shifokorga savol» page (`Question` rows). Institutions: the
registry's broken quotes become «».

Pages with an unpublished draft are skipped (an editor's work is never published by this
command); a second run changes nothing.
"""

from __future__ import annotations

import json
from typing import Any

from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction

PLAIN_FIELDS = ("summary", "search_description", "directions_note")

# the live texts the expert flagged (seeded before D-106)
OLD_BBS_UZ = (
    "<b>Bachadon boʻyni saratoni (BBS):</b> 30–50 yoshdagi ayollar har yili inson papilloma "
    "virusi (HPV)ni aniqlash uchun PCR-testi va suyuq asosli sitologiya yordamida skriningdan "
    "oʻtadilar. Natija manfiy boʻlsa, keyingi tekshiruv 10 yildan soʻng oʻtkaziladi. Natija "
    "ijobiy boʻlsa, qoʻshimcha tekshiruvga yoʻllanma beriladi."
)
OLD_BBS_RU = (
    "<b>Рак шейки матки (РШМ):</b> женщины 30–50 лет ежегодно проходят скрининг с помощью "
    "ПЦР-теста на вирус папилломы человека (ВПЧ) и жидкостной цитологии. При отрицательном "
    "результате следующее обследование проводится через 10 лет. При положительном результате "
    "выдается направление на дополнительное обследование."
)
OLD_TODO = "<p>[[TODO: content — copywriter]] [[VERIFY: doctor]]</p>"
OLD_KBS_UZ = (
    "<b>Koʻkrak bezi saratoni (KBS):</b> 30–65 yoshdagi ayollar har 2 yilda bir marta tibbiyot "
    "xodimlari tomonidan dastlabki koʻrikdan oʻtadilar. 45 yoshgacha boʻlgan ayollarda koʻkrak "
    "bezlari UZI orqali, 45–65 yoshda esa mammografiya orqali tekshiriladi."
)
OLD_KBS_RU = (
    "<b>Рак молочной железы (РМЖ):</b> женщины 30–65 лет один раз в 2 года проходят первичный "
    "осмотр у медицинских работников. Молочные железы у женщин до 45 лет обследуют с помощью "
    "УЗИ, а в 45–65 лет — с помощью маммографии."
)
OLD_METASTASES_UZ = (
    "Operatsiyadan keyin organizmning xususiyatlariga, davolash sifatiga, kasallikning "
    "bosqichiga qarab, bemorlarning bir qismi bir necha yil, baʼzilari esa keksalikka qadar "
    "yashaydi. Statistikaga koʻra, operatsiyadan keyingi yangi metastazlar birinchi 3-5 yil "
    "ichida paydo boʻladi, keyinchalik yangi shakllanish xavfi keskin kamayadi."
)
OLD_METASTASES_RU = (
    "После операции, в зависимости от особенностей организма, качества лечения и стадии "
    "заболевания, часть пациенток живет несколько лет, а некоторые — до преклонного возраста. "
    "По статистике, новые метастазы после операции появляются в течение первых 3–5 лет, затем "
    "риск появления новых очагов резко снижается."
)
OLD_FAQ_BREAST_UZ = (
    "45 yoshgacha boʻlgan ayollarda sut bezlari ultratovush tekshiruvi, 45 yoshdan 65 yoshgacha"
)
OLD_FAQ_BREAST_RU = "Женщинам до 45 лет проводится ультразвуковое исследование молочных желез"
OLD_FAQ_CERVICAL_UZ = (
    "Oʻzbekiston Respublikasi Prezidentining 2024-yil 22-noyabrdagi PQ-402-son qaroriga "
    "muvofiq, 30 yoshdan 65 yoshgacha boʻlgan ayollarni har ikki yilda bir marta tekshiruvdan "
    "oʻtkazish koʻzda tutilgan. Bachadon boʻynidagi oʻzgarishlarni aniqlash uchun maxsus "
    "tekshiruv, jumladan, belgilangan tartibda OPV (odam papillomavirusi) testi oʻtkaziladi. "
    "Tekshiruv joyi va muddatlarini oilaviy poliklinikadan aniqlash mumkin."
)
OLD_FAQ_CERVICAL_RU = (
    "Согласно Постановлению Президента Республики Узбекистан от 22 ноября 2024 года № ПП-402, "
    "предусмотрено обследование женщин в возрасте от 30 до 65 лет один раз в два года. Для "
    "выявления изменений шейки матки проводится специальное обследование, в том числе в "
    "установленном порядке — тест на ВПЧ (вирус папилломы человека). Место и сроки обследования "
    "можно уточнить в семейной поликлинике."
)

# pages built from tree.py / apps.home.design (not translated through ru_women.json)
PORTAL_PAGES = [
    (
        "«Erta aniqla» onkologik hushyorlik portali — ikki asosiy boʻlimni birlashtirgan "
        "axborot-taʼlim platformasi: koʻkrak bezi va bachadon boʻyni saratoni hamda bolalar "
        "saratoni.",
        "«Erta aniqla» onkologik hushyorlik portali — axborot-taʼlim platformasi. Hozir portalda "
        "koʻkrak bezi va bachadon boʻyni saratoni boʻlimi ishlaydi; bolalar saratoni boʻlimi "
        "ishlab chiqish rejasida.",
    ),
    (
        "Портал настороженности «Эрта аниқла» — это информационно-образовательная платформа, "
        "объединяющая два ключевых раздела: РМЖ/РШМ и детский рак.",
        "Портал настороженности «Эрта аниқла» — это информационно-образовательная платформа. "
        "Сейчас на портале работает раздел о раке молочной железы и шейки матки; раздел о "
        "детском раке находится в плане разработки.",
    ),
    (
        "онкологических заболеваний по двум направлениям, содействия",
        "онкологических заболеваний, содействия",
    ),
    (
        "Dastlabki alomatlar, diagnostika, parvarish va kasallikdan keyingi hayot.",
        "Ishlab chiqish rejasida. Dastlabki alomatlar, diagnostika, parvarish va kasallikdan "
        "keyingi hayot.",
    ),
    (
        "Первые признаки, диагностика, уход и жизнь после болезни.",
        "В плане разработки. Первые признаки, диагностика, уход и жизнь после болезни.",
    ),
    (
        "(mammografiya 45–65, UTT 45 gacha, HPV 30–50)",
        "(mammografiya 45–65, UTT 30–44, HPV 30, 40 va 50 yoshda)",
    ),
    (
        "(маммография 45–65, УЗИ до 45, ВПЧ 30–50)",
        "(маммография 45–65, УЗИ 30–44, ВПЧ в 30, 40 и 50 лет)",
    ),
    (
        "<b>Bezi (jigarrang) epiteliydan rivojlangan oʻsimtalar:</b>",
        "<b>Bezli epiteliydan rivojlanadigan oʻsimtalar:</b>",
    ),
]

SCREENING_BREAST = ("/skrining/kokrak-bezi-saratoni/", "/skrining/rak-molochnoy-zhelezy/")
SCREENING_CERVICAL = ("/skrining/bachadon-boyni-saratoni/", "/skrining/rak-sheyki-matki/")
PROGRAMME_TITLES = ("Davlat dasturi: kimga va qanchalik tez-tez", "Госпрограмма: кому и как часто")
INTERNATIONAL_STARTS = ("<ul><li>40 yoshdan 75 yoshgacha", "<ul><li>Женщинам от 40 до 75 лет")
IMMUNITY_ICONS = ("c-virus", "c-vitamin")


def _ru(uz_segment: str) -> str:
    from apps.core.seed.ru_translate import dictionary

    return dictionary()[uz_segment]


def _p(*segments: str) -> str:
    return "".join(f"<p>{segment}</p>" for segment in segments)


def replacements() -> list[tuple[str, str]]:
    """(old, new) pairs, applied in order to the JSON of every live page's text."""
    from apps.core.seed import women_faq
    from apps.core.seed import women_figma as w

    uz = w.uz
    screening_uz = [uz(text) for text in w.CERVICAL_SCREENING]
    new_bbs_uz = "<b>Bachadon boʻyni saratoni (BBS):</b> " + uz(w.BBS_PROGRAMME)
    new_kbs_uz = "<b>Koʻkrak bezi saratoni (KBS):</b> " + uz(w.KBS_PROGRAMME)
    new_faq_cervical_uz = next(
        a for _c, _q, answers, _k in women_faq.CERVICAL for a in answers if "30, 40 va 50" in a
    )
    pairs = [
        # the cervical screening page: the expert's text in place of the programme + placeholder
        (_p(OLD_BBS_UZ) + OLD_TODO, _p(*screening_uz)),
        (_p(OLD_BBS_RU) + OLD_TODO, _p(*[_ru(text) for text in screening_uz])),
        # the «Qo'llab-quvvatlash» pages
        (OLD_BBS_UZ, new_bbs_uz),
        (OLD_BBS_RU, _ru(new_bbs_uz)),
        (OLD_KBS_UZ, new_kbs_uz),
        (OLD_KBS_RU, _ru(new_kbs_uz)),
        # the programme list on the screening pages
        (
            "UTT: 45 yoshgacha bo'lgan ayollar, 2 yilda bir marta;",
            "UTT: 30–44 yoshdagi ayollar, 2 yilda bir marta;",
        ),
        ("УЗИ: женщины до 45 лет, раз в 2 года;", "УЗИ: женщины 30–44 лет, раз в 2 года;"),
        (
            "HPV-test: 30–50 yoshdagi ayollar;",
            uz(
                "HPV-test: 30, 40 va 50 yoshdagi ayollar (natija manfiy bo'lsa — keyingisi 10 "
                "yildan keyin);"
            ),
        ),
        (
            "ВПЧ-тест: женщины 30–50 лет;",
            "ВПЧ-тест: женщины 30, 40 и 50 лет (при отрицательном результате — следующий через "
            "10 лет);",
        ),
        ("o'z-o'zini tekshirishga chaqiriq.", "oʻz-oʻzini tekshirishga chaqiriq."),
        # cervical awareness
        ("BEZI JIGARRANG EPITELIYDAN RIVOJLANGAN OʻSIMTALAR", uz(w.GLANDULAR_FORMS)),
        (
            "Bachadon boʻyni rakining asosiy sababi papillomavirus infeksiyasi, ayniqsa OPV 16 va "
            "18 serotiplaridir. IPV 16 yassi hujayrali saraton bilan, IPV 18 esa adenokarsinoma "
            "bilan assotsiatsiyalanadi.",
            uz(w.HPV_CAUSE),
        ),
        (
            "Основная причина рака шейки матки — папилломавирусная инфекция, особенно ВПЧ 16-го "
            "и 18-го типов. ВПЧ 16 ассоциирован с плоскоклеточным раком, а ВПЧ 18 — с "
            "аденокарциномой.",
            _ru(uz(w.HPV_CAUSE)),
        ),
        ("Bachadon boʻyni eroziyasi va displaziyasi.", uz(w.CERVIX_CHANGES)),
        ("Эрозия и дисплазия шейки матки.", _ru(uz(w.CERVIX_CHANGES))),
        (
            "OIV, genital gerpes, xlamidioz. Bu infeksiyalar mahalliy immunitetni pasaytirishi "
            "mumkin.",
            "OIV, genital gerpes, xlamidioz.",
        ),
        (
            "ВИЧ, генитальный герпес, хламидиоз. Эти инфекции могут снижать местный иммунитет.",
            "ВИЧ, генитальный герпес, хламидиоз.",
        ),
        # breast treatment
        ("Onkolog / onkoginekolog", "Onkolog yoki mammolog-onkolog"),
        ("Онколог / онкогинеколог", "Онколог или маммолог-онколог"),
        ('"deadline": "[[VERIFY: PP-402 referral deadlines]]"', '"deadline": ""'),
        (
            "radiatsion terapiya (agar bemor klimaks davridan oʻtgan boʻlsa) – ",
            "radiatsion terapiya – ",
        ),
        ("kimyoterapiya (agar bemor klimaks davridan oʻtmagan boʻlsa) – ", "kimyoterapiya – "),
        ("лучевая терапия (если у пациентки уже наступила менопауза) — ", "лучевая терапия — "),
        ("химиотерапия (если менопауза у пациентки ещё не наступила) — ", "химиотерапия — "),
        (OLD_METASTASES_UZ, uz(w.BREAST_TREATMENT_CHOICE)),
        (OLD_METASTASES_RU, _ru(uz(w.BREAST_TREATMENT_CHOICE))),
        # FAQ
        (
            OLD_FAQ_BREAST_UZ,
            "30–44 yoshdagi ayollarda sut bezlari ultratovush tekshiruvi, 45 yoshdan 65 yoshgacha",
        ),
        (
            OLD_FAQ_BREAST_RU,
            "Женщинам 30–44 лет проводится ультразвуковое исследование молочных желез",
        ),
        (OLD_FAQ_CERVICAL_UZ, new_faq_cervical_uz),
        (OLD_FAQ_CERVICAL_RU, _ru(new_faq_cervical_uz)),
        *PORTAL_PAGES,
    ]
    return pairs


def _language(page: Any) -> str:
    return "ru" if page.locale.language_code == "ru" else "uz"


def _tr(page: Any, uz_text: str) -> str:
    return _ru(uz_text) if _language(page) == "ru" else uz_text


def _block(block_type: str, value: dict[str, Any]) -> dict[str, Any]:
    return {"type": block_type, "value": value}


def _card(text: str, title: str = "") -> dict[str, Any]:
    from apps.core.seed.women_figma import card

    return _block("text_card", card(text, title=title))


def _block_lists(blocks: list[Any]) -> list[list[Any]]:
    """The body and every accordion item's body: the lists blocks can be moved within."""
    found = [blocks]
    for block in blocks:
        if block.get("type") == "accordion":
            for item in (block.get("value") or {}).get("items", []):
                found += _block_lists(item.get("body", []))
    return found


class Command(BaseCommand):
    help = "Expert review of 2026-10-26 and the doctor's «Читка» (D-106)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--dry-run", action="store_true", help="Report, change nothing.")

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        from wagtail.fields import StreamField
        from wagtail.models import Page

        dry_run = options["dry_run"]
        pairs = replacements()
        used: set[str] = set()
        for page in Page.objects.live().specific().order_by("path"):
            streams = [f.name for f in page._meta.get_fields() if isinstance(f, StreamField)]
            changes: list[str] = []
            for name in streams:
                raw = list(getattr(page, name).raw_data)
                text = json.dumps(raw, ensure_ascii=False)
                for old, new in pairs:
                    if old in text:
                        text = text.replace(old, new)
                        used.add(old)
                        changes.append("text")
                raw = json.loads(text)
                if name == "body":
                    changes += self._restructure(page, raw)
                if changes:
                    setattr(page, name, raw)
            for name in PLAIN_FIELDS:
                value = getattr(page, name, None)
                if not isinstance(value, str):
                    continue
                for old, new in pairs:
                    if old in value:
                        value = value.replace(old, new)
                        used.add(old)
                        changes.append(name)
                setattr(page, name, value)
            if not changes:
                continue
            if page.has_unpublished_changes:
                self.stdout.write(f"skipped (unpublished draft): {page.url_path}")
                continue
            summary = ", ".join(sorted(set(changes)))
            if not dry_run:
                page.save_revision(log_action=True).publish()
            self.stdout.write(
                f"{'would update' if dry_run else 'updated'}: {page.url_path} ({summary})"
            )
        for old, _new in pairs:
            if old not in used:
                self.stdout.write(f"not found (already changed or edited in the CMS): {old[:70]}")
        self._questions(pairs, dry_run)
        self._institutions(dry_run)
        if dry_run:
            transaction.set_rollback(True)

    def _restructure(self, page: Any, body: list[Any]) -> list[str]:
        done: list[str] = []
        url = page.url_path
        for blocks in _block_lists(body):
            if self._split_immunity(page, blocks):
                done.append("local immunity group")
        if url.endswith(SCREENING_BREAST) and self._breast_programme(page, body):
            done.append("breast programme first")
        if url.endswith(SCREENING_CERVICAL) and self._cervical_results(page, body):
            done.append("results note")
        return done

    def _split_immunity(self, page: Any, blocks: list[Any]) -> bool:
        from apps.core.seed import women_figma as w

        for index, block in enumerate(blocks):
            if block.get("type") != "cards_grid":
                continue
            cards = block["value"].get("cards", [])
            icons = [card.get("icon") for card in cards]
            if not set(IMMUNITY_ICONS) <= set(icons) or len(cards) <= len(IMMUNITY_ICONS):
                continue
            moved = [card for card in cards if card.get("icon") in IMMUNITY_ICONS]
            block["value"]["cards"] = [c for c in cards if c.get("icon") not in IMMUNITY_ICONS]
            intro = _card(_p(_tr(page, "<b>" + w.uz(w.LOCAL_IMMUNITY) + "</b>")))
            group = _block("cards_grid", {**block["value"], "cards": moved})
            blocks[index + 1 : index + 1] = [intro, group]
            return True
        return False

    def _breast_programme(self, page: Any, body: list[Any]) -> bool:
        from apps.core.seed import women_figma as w
        from apps.core.seed.tree import callout

        programme = next(
            (
                i
                for i, b in enumerate(body)
                if b.get("type") == "text_card" and b["value"].get("title") in PROGRAMME_TITLES
            ),
            None,
        )
        international = next(
            (
                i
                for i, b in enumerate(body)
                if b.get("type") == "text_card"
                and str(b["value"].get("text", "")).startswith(INTERNATIONAL_STARTS)
            ),
            None,
        )
        if programme is None or international is None:
            return False
        body[international]["value"]["title"] = _tr(page, w.INTERNATIONAL_TITLE)
        rules = body.pop(programme)["value"]["text"]  # the TZ table, already corrected
        new = [
            _card(
                _p(_tr(page, w.uz(w.BREAST_PROGRAMME))) + rules,
                title=_tr(page, w.uz(w.BREAST_PROGRAMME_TITLE)),
            ),
            callout("warning", "", _p(_tr(page, w.uz(w.BREAST_SYMPTOMS)))),
        ]
        body[international:international] = new
        return True

    def _cervical_results(self, page: Any, body: list[Any]) -> bool:
        from apps.core.seed import women_figma as w

        title = _tr(page, w.uz(w.CERVICAL_RESULTS_TITLE))
        if any(b.get("type") == "text_card" and b["value"].get("title") == title for b in body):
            return False
        route = next((i for i, b in enumerate(body) if b.get("type") == "screening_route"), None)
        if route is None:
            return False
        text = _p(_tr(page, w.uz(w.CERVICAL_RESULTS)))
        body.insert(route + 1, _card(text, title=title))
        return True

    def _questions(self, pairs: list[tuple[str, str]], dry_run: bool) -> None:
        """The «Shifokorga savol» page shows the same FAQ answers from `Question` rows."""
        from apps.faq.models import Question

        changed = 0
        for question in Question.objects.exclude(answer=""):
            answer = question.answer
            for old, new in pairs:
                answer = answer.replace(old, new)
            if answer == question.answer:
                continue
            changed += 1
            if not dry_run:
                question.answer = answer
                question.save(update_fields=["answer", "updated_at"])
        self.stdout.write(f"answered questions updated: {changed}")

    def _institutions(self, dry_run: bool) -> None:
        from apps.directory.models import Institution
        from apps.directory.services import TIDY_FIELDS, tidy_quotes

        changed = 0
        for institution in Institution.objects.all().iterator():
            fields = [
                name
                for name in TIDY_FIELDS
                if tidy_quotes(getattr(institution, name)) != getattr(institution, name)
            ]
            if not fields:
                continue
            changed += 1
            if not dry_run:
                for name in fields:
                    setattr(institution, name, tidy_quotes(getattr(institution, name)))
                institution.save(update_fields=fields)
        self.stdout.write(f"institutions with quotes tidied: {changed}")
