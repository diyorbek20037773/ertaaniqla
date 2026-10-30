"""Expert review of 2026-10-26 and the doctor's «Читка» (D-106): the seed carries the corrected
texts, and the one-off command turns the live pages of before into exactly what the seed builds."""

from __future__ import annotations

import json
from typing import Any

import pytest
from django.core.management import call_command
from django.test import Client
from wagtail.models import Page

from apps.core.management.commands import client_update_20261030 as update
from apps.core.seed import ru_translate, women_figma
from apps.directory.models import Institution, InstitutionKind, Region
from apps.directory.services import tidy_quotes
from apps.faq.models import Question

pytestmark = pytest.mark.django_db

AWARENESS = "/ayollar/ogohlik/bachadon-boyni-saratoni/"
SCREENING_BREAST = "/ayollar/skrining/kokrak-bezi-saratoni/"
SCREENING_CERVICAL = "/ayollar/skrining/bachadon-boyni-saratoni/"
TREATMENT_BREAST = "/ayollar/davolash/kokrak-bezi-saratoni/"
DEADLINE = "[[VERIFY: PP-402 referral deadlines]]"
GONE = [  # what the expert flagged, in both languages
    "JIGARRANG",
    "eroziyasi",
    "Эрозия и дисплазия",
    "klimaks davridan",
    "наступила менопауза",
    "3-5 yil ichida",
    "первых 3–5 лет",
    "har yili inson papilloma",
    "30–50 лет ежегодно",
    "UTT: 45 yoshgacha",
    "УЗИ: женщины до 45 лет",
    "Onkolog / onkoginekolog",
    "mahalliy immunitetni pasaytirishi mumkin",
    "могут снижать местный иммунитет",
]


def _pages(suffix: str) -> list[Any]:
    """The uz page and its Russian translation."""
    page = Page.objects.get(url_path__endswith=suffix, locale__language_code="uz")
    return [p.specific for p in page.get_translations(inclusive=True)]


def _no_ids(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _no_ids(v) for k, v in value.items() if k != "id"}
    if isinstance(value, list):
        return [_no_ids(v) for v in value]
    return value


def _lang(page: Any) -> str:
    return page.locale.language_code


def _ru(value: Any) -> Any:
    missing: list[str] = []
    return ru_translate.translate(value, ru_translate.dictionary(), missing)


def _value(block: dict[str, Any]) -> dict[str, Any]:
    value = block.get("value")
    return value if isinstance(value, dict) else {}


def _old_structure(page: Any, body: list[Any]) -> list[Any]:
    """Undo the structural edits of D-106 on a seeded body (what live sites had before)."""
    for blocks in update._block_lists(body):
        for i, block in enumerate(blocks):
            icons = [c.get("icon") for c in _value(block).get("cards", [])]
            if block.get("type") == "cards_grid" and icons[:2] == list(update.IMMUNITY_ICONS):
                main = blocks[i - 2]
                main["value"]["cards"] = block["value"]["cards"] + main["value"]["cards"]
                del blocks[i - 1 : i + 1]
                break
    url = page.url_path
    if url.endswith(update.SCREENING_BREAST):
        title = update._tr(page, women_figma.uz(women_figma.BREAST_PROGRAMME_TITLE))
        index = next(i for i, b in enumerate(body) if _value(b).get("title") == title)
        del body[index : index + 2]  # the programme card and the «do not wait» callout
        rules = women_figma._tz_screening_rules("uz")
        rules = _ru(rules) if _lang(page) == "ru" else rules
        international = index
        body[international]["value"]["title"] = ""
        body.insert(international + 1, rules)
    if url.endswith(update.SCREENING_CERVICAL):
        title = update._tr(page, women_figma.uz(women_figma.CERVICAL_RESULTS_TITLE))
        body[:] = [b for b in body if _value(b).get("title") != title]
    for block in body:
        if block.get("type") == "steps" and url.endswith(
            ("/davolash/kokrak-bezi-saratoni/", "/organizatsiya-lecheniya/rak-molochnoy-zhelezy/")
        ):
            block["value"]["steps"][2]["deadline"] = DEADLINE
    return body


def _old_text(text: str) -> str:
    for old, new in reversed(update.replacements()):
        if new != '"deadline": ""':
            text = text.replace(new, old)
    return text


def _snapshot(pages: list[Any]) -> dict[int, Any]:
    return {
        p.pk: _no_ids(
            [
                list(p.body.raw_data) if hasattr(p, "body") else None,
                list(p.directions.raw_data) if hasattr(p, "directions") else None,
                p.summary if hasattr(p, "summary") else None,
            ]
        )
        for p in pages
    }


@pytest.mark.parametrize("lang", ["uz", "ru"])
def test_the_seeded_pages_say_what_the_expert_asked(seeded, client: Client, lang: str) -> None:
    for suffix in (AWARENESS, SCREENING_BREAST, SCREENING_CERVICAL, TREATMENT_BREAST):
        page = next(p for p in _pages(suffix) if _lang(p) == lang)
        html = client.get(page.url).content.decode()
        found = [phrase for phrase in GONE if phrase in html]
        assert not found, (page.url, found)
    awareness = next(p for p in _pages(AWARENESS) if _lang(p) == lang)
    html = client.get(awareness.url).content.decode()
    assert ("Mahalliy immunitet pasayishi" if lang == "uz" else "местного иммунитета") in html
    treatment = next(p for p in _pages(TREATMENT_BREAST) if _lang(p) == lang)
    assert "steps__deadline" not in client.get(treatment.url).content.decode()  # no «Muddat:»


def test_the_live_update_turns_the_old_pages_into_the_seed(seeded) -> None:
    pages = [p.specific for p in Page.objects.live().specific()]
    expected = _snapshot(pages)
    answers = {q.pk: q.answer for q in Question.objects.exclude(answer="")}
    for page in pages:  # back to what live sites had before D-106
        raw = list(page.body.raw_data) if hasattr(page, "body") else None
        if raw is not None:
            page.body = json.loads(
                _old_text(json.dumps(_old_structure(page, raw), ensure_ascii=False))
            )
        if hasattr(page, "directions"):
            raw = json.dumps(list(page.directions.raw_data), ensure_ascii=False)
            page.directions = json.loads(_old_text(raw))
        if hasattr(page, "summary"):
            page.summary = _old_text(page.summary)
        page.save_revision().publish()
    for question in Question.objects.exclude(answer=""):
        question.answer = _old_text(question.answer)
        question.save()
    old = _snapshot([p.specific for p in Page.objects.live().specific()])
    assert old != expected

    call_command("client_update_20261030", "--dry-run")
    assert _snapshot([p.specific for p in Page.objects.live().specific()]) == old

    call_command("client_update_20261030")
    assert _snapshot([p.specific for p in Page.objects.live().specific()]) == expected
    assert {q.pk: q.answer for q in Question.objects.exclude(answer="")} == answers

    call_command("client_update_20261030")  # a second run changes nothing
    assert _snapshot([p.specific for p in Page.objects.live().specific()]) == expected


def test_a_pair_that_contains_its_old_text_is_applied_once() -> None:
    pairs = update.replacements()
    old = "Dastlabki alomatlar, diagnostika, parvarish va kasallikdan keyingi hayot."
    once, found = update.apply(old, pairs)
    assert once.startswith("Ishlab chiqish rejasida. Dastlabki") and found == {old}
    assert update.apply(once, pairs) == (once, set())


def test_the_live_update_never_publishes_an_editors_draft(seeded) -> None:
    page = next(p for p in _pages(TREATMENT_BREAST) if _lang(p) == "uz")
    raw = json.dumps(list(page.body.raw_data), ensure_ascii=False)
    page.body = json.loads(_old_text(raw))
    page.save_revision().publish()
    page.title = "Muharrir qoralamasi"
    page.save_revision()  # a draft, not published
    call_command("client_update_20261030")
    page.refresh_from_db()
    assert page.title != "Muharrir qoralamasi"
    assert "klimaks davridan" in json.dumps(list(page.body.raw_data), ensure_ascii=False)


@pytest.mark.parametrize(
    ("raw", "tidy"),
    [
        ('"Kelovchi" oilaviy shifokor punkti"', "«Kelovchi» oilaviy shifokor punkti"),
        ('"26- OP "Uyrot"', "26- OP «Uyrot»"),
        ('Forish tumani MFY"Uxum", Eski Forish"', "Forish tumani MFY «Uxum», Eski Forish"),
        ('"Kesakli"oilaviy shifokor punkti"', "«Kesakli» oilaviy shifokor punkti"),
        (
            '"Yunusobod tumani,"Amir Temur" kuchasi, 117 uy"',
            "Yunusobod tumani, «Amir Temur» kuchasi, 117 uy",
        ),
        (
            '"Mirzaobod tumani, QFY"Nurafshon","Beruniy" qishlogʻi"',
            "Mirzaobod tumani, QFY «Nurafshon», «Beruniy» qishlogʻi",
        ),
        ('"Boʻka tumani"Jagʻalbayli" MFY"', "Boʻka tumani «Jagʻalbayli» MFY"),
        ('" ОФЙ"Қораўзак"', "ОФЙ «Қораўзак»"),
        ('"ОШПУСМОН НОСИР" НОМЛИ"', "«ОШПУСМОН НОСИР» НОМЛИ"),
        ('" OFY"A. Dosnazarov»"', "OFY «A. Dosnazarov»"),
        (
            'Jizzax shahar,Toʻkimachilar"koʻchasi, 62-uy',
            "Jizzax shahar,Toʻkimachilar koʻchasi, 62-uy",
        ),
        ("Toshkent shahar 2–son klinik shifoxonasi", "Toshkent shahar 2–son klinik shifoxonasi"),
        ("«Sogʻlom» poliklinikasi", "«Sogʻlom» poliklinikasi"),
    ],
)
def test_registry_quotes_are_tidied(raw: str, tidy: str) -> None:
    assert tidy_quotes(raw) == tidy
    assert tidy_quotes(tidy) == tidy  # a second pass changes nothing


def test_the_card_does_not_repeat_the_district(client: Client, seeded) -> None:
    region = Region.objects.get(code="tashkent-city")
    institution = Institution.objects.create(
        name_uz='"Olmazor" 5-oilaviy poliklinika"',
        name_ru="Олмазор 5-поликлиника",
        kind=InstitutionKind.POLYCLINIC,
        region=region,
        district_uz="Olmazor tumani",
        district_ru="Олмазор тумани",
        address_uz="Olmazor tumani, Olmazor koʻchasi, 351 uy",
        address_ru="Олмазор тумани, Олмазор кўчаси, 351 уй",
    )
    assert institution.location_for("uz") == (
        f"{region.name_uz}, Olmazor tumani, Olmazor koʻchasi, 351 uy"
    )
    institution.address_uz = "Navoiy koʻchasi, 5"
    assert institution.location_for("uz") == f"{region.name_uz}, Olmazor tumani, Navoiy koʻchasi, 5"
    call_command("client_update_20261030")
    institution.refresh_from_db()
    assert institution.name_uz == "«Olmazor» 5-oilaviy poliklinika"
    html = client.get(
        "/uz/ayollar/qayerga-murojaat/", {"region": "tashkent-city", "kind": "polyclinic"}
    ).content.decode()
    assert "Maʼlumotlar aniqlashtirilmoqda" in html  # not verified yet
