"""`seed_content` builds the complete TZ tree (spec §2.2–2.3) in uz + ru, idempotently,
and every seeded page answers 200 in both languages (M1 gate)."""

from __future__ import annotations

import re

import pytest
from django.core.management import call_command
from django.test import Client
from django.utils.html import strip_tags
from wagtail.models import Locale, Page, Site

from apps.core.seed import tree
from apps.core.seed.builder import Seeder
from apps.home.models import HomePage

pytestmark = pytest.mark.django_db


def page_for(key: str, lang: str) -> Page:
    node = next(n for n in tree.iter_nodes() if n.key == key)
    locale = Locale.objects.get(language_code=lang)
    model = Seeder().model_for(node.kind)
    candidates = model.objects.filter(locale=locale, slug=node.slug[lang], live=True)
    parent_key = key.rpartition(".")[0]
    if any(n.key == parent_key for n in tree.iter_nodes()):
        # variant articles share their slugs across topics (D-066): narrow by the parent
        candidates = candidates.child_of(page_for(parent_key, lang))
    section_key = key.split(".")[0]
    for page in candidates:
        section = page.specific.get_section()
        if section is None or section.section_key == section_key:
            return page.specific
    raise AssertionError(f"page {key} ({lang}) not found")


def body_text(page: Page) -> str:
    field = page.body if hasattr(page, "body") else page.intro
    return re.sub(r"\s+", " ", strip_tags(str(field)))


# ---------------------------------------------------------------------------
# structure
# ---------------------------------------------------------------------------
def test_home_is_site_root_in_both_languages(seeded) -> None:
    site = Site.objects.get(is_default_site=True)
    home = site.root_page.specific
    assert isinstance(home, HomePage)
    assert home.locale.language_code == "uz"
    ru = home.get_translation(Locale.objects.get(language_code="ru"))
    assert ru.live
    assert not Page.objects.filter(title="Welcome to your new Wagtail site!").exists()


def test_every_node_exists_live_in_both_languages(seeded) -> None:
    for node in tree.iter_nodes():
        for lang in ("uz", "ru"):
            page = page_for(node.key, lang)
            assert page.live
            assert page.title == node.title[lang]
            assert page.show_in_menus is node.show_in_menus


def test_translations_are_linked(seeded) -> None:
    ru = Locale.objects.get(language_code="ru")
    for node in tree.iter_nodes():
        uz_page = page_for(node.key, "uz")
        assert uz_page.get_translation(ru).slug == node.slug["ru"]


def test_women_menu_has_the_five_figma_tabs(seeded) -> None:
    section = page_for("women", "ru")
    titles = [p.title for p in section.get_menu_items()]
    # D-064: the Figma tabs replace the TZ menu; «Куда обратиться» stays as a CTA target
    assert titles == [
        "Осведомленность",
        "Скрининг",
        "Организация лечения",
        "Поддержка",
        "Жизнь после рака",
    ]
    all_titles = [p.title for p in section.get_subsections()]
    assert "Куда обратиться" in all_titles


def test_women_topics_are_breast_and_cervical_variant_groups(seeded) -> None:
    for topic in ("awareness", "screening", "treatment", "support", "after"):
        for lang in ("uz", "ru"):
            page = page_for(f"women.{topic}", lang)
            assert page.is_variant_group
            children = [c.slug for c in page.get_children()]
            assert children[:2] == [
                page_for(f"women.{topic}.breast", lang).slug,
                page_for(f"women.{topic}.cervical", lang).slug,
            ]


def test_children_menu_has_the_five_tz_items(seeded) -> None:
    section = page_for("children", "ru")
    titles = [p.title for p in section.get_menu_items()]
    assert titles == [
        "Об онкозаболеваниях у детей",
        "Диагностика и лечение",
        "Уход и поддержка",
        "Информация для семьи",
        "Жизнь после рака",
    ]


def test_section_urls_match_spec(seeded) -> None:
    assert page_for("women", "uz").url == "/uz/ayollar/"
    assert page_for("women", "ru").url == "/ru/zhenskiy/"
    assert page_for("children", "uz").url == "/uz/bolalar/"
    assert page_for("children", "ru").url == "/ru/detskiy/"


# ---------------------------------------------------------------------------
# TZ content verbatim (ru) — every table cell and bullet
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("key", "snippets"),
    [
        (
            "women.awareness.breast",
            [
                "что происходит в организме",
                "стадии",
                "статистика по Узбекистану",
                "Возраст",
                "Наследственность",
                "Образ жизни",
                "ВПЧ-инфекция",
                "Самообследование груди",
                "не всегда означает рак",
            ],
        ),
        (
            "women.screening.breast",
            [
                "маммография: женщины 45–65 лет, раз в 2 года",
                "УЗИ: женщины до 45 лет, раз в 2 года",
                "ВПЧ-тест: женщины 30–50 лет",
                "Призывы к самостоятельному обследованию",
                "[[VERIFY: doctor]]",
                "семейные врачебные пункты",
                "районные поликлиники (кабинеты онконастороженности)",
                "Центр здоровья матери и ребенка и его филиалы",
                "Бесплатно – в рамках государственной программы",
            ],
        ),
        (
            "women.treatment.breast",
            [
                "Первичный прием",
                "Обратитесь к терапевту или гинекологу при первых признаках или при плановом визите.",
                "Направление на диагностику",
                "УЗИ, маммография, тесты, прием у кабинета «Онконастороженности» и др.",
                "Онколог / онкогинеколог",
                "направление в онкологический центр (в соответствии с датами в ПП-402)",
                "[[VERIFY: PP-402 referral deadlines]]",
                "Лечение",
                "Информация об этапах лечения.",
            ],
        ),
        (
            "women.support.breast",
            [
                "Бесплатный скрининг в рамках государственной программы",
                "Возможности в кабинетах «Онконастороженности»",
                "Права и обязанности пациентов и врачей",
                "Физическое здоровье",
                "питание во время лечения",
                "управление побочными эффектами",
                "уход за кожей и волосами",
                "физическая активность и реабилитация",
                "Эмоциональная поддержка",
                "как справляться со страхом и тревогой",
                "психологическая помощь: куда обратиться",
                "поддержка близких и семьи",
                "группы взаимопомощи пациентов",
                "Практические вопросы",
                "больничный и трудовые права",
                "финансовая поддержка и льготы",
                "как помочь близкому человеку с диагнозом",
                "вопросы, которые важно задать врачу",
            ],
        ),
        (
            "women.after.breast",
            [
                "Наблюдение после лечения",
                "график контрольных осмотров",
                "поздние эффекты лечения",
                "паспорт здоровья пациента",
                "Возвращение к жизни",
                "возврат к работе и привычному ритму",
                "физическая реабилитация",
                "эмоциональное восстановление",
                "Долгосрочное здоровье",
                "профилактика рецидива",
                "репродуктивное здоровье после лечения",
                "психологическое благополучие в долгосрочной перспективе",
            ],
        ),
        (
            "women.awareness.cervical",
            [
                "что происходит в организме",
                "стадии",
                "статистика по Узбекистану",
                "Возраст",
                "Наследственность",
                "Образ жизни",
                "ВПЧ-инфекция",
                "Самообследование груди",
                "не всегда означает рак",
            ],
        ),
        (
            "women.screening.cervical",
            [
                "маммография: женщины 45–65 лет, раз в 2 года",
                "УЗИ: женщины до 45 лет, раз в 2 года",
                "ВПЧ-тест: женщины 30–50 лет",
                "Призывы к самостоятельному обследованию",
                "[[VERIFY: doctor]]",
                "семейные врачебные пункты",
                "районные поликлиники (кабинеты онконастороженности)",
                "Центр здоровья матери и ребенка и его филиалы",
                "Бесплатно – в рамках государственной программы",
            ],
        ),
        (
            "women.treatment.cervical",
            [
                "Первичный прием",
                "Обратитесь к терапевту или гинекологу при первых признаках или при плановом визите.",
                "Направление на диагностику",
                "УЗИ, маммография, тесты, прием у кабинета «Онконастороженности» и др.",
                "Онколог / онкогинеколог",
                "направление в онкологический центр (в соответствии с датами в ПП-402)",
                "[[VERIFY: PP-402 referral deadlines]]",
                "Лечение",
                "Информация об этапах лечения.",
            ],
        ),
        (
            "women.support.cervical",
            [
                "Бесплатный скрининг в рамках государственной программы",
                "Возможности в кабинетах «Онконастороженности»",
                "Права и обязанности пациентов и врачей",
                "Физическое здоровье",
                "питание во время лечения",
                "управление побочными эффектами",
                "уход за кожей и волосами",
                "физическая активность и реабилитация",
                "Эмоциональная поддержка",
                "как справляться со страхом и тревогой",
                "психологическая помощь: куда обратиться",
                "поддержка близких и семьи",
                "группы взаимопомощи пациентов",
                "Практические вопросы",
                "больничный и трудовые права",
                "финансовая поддержка и льготы",
                "как помочь близкому человеку с диагнозом",
                "вопросы, которые важно задать врачу",
            ],
        ),
        (
            "women.after.cervical",
            [
                "Наблюдение после лечения",
                "график контрольных осмотров",
                "поздние эффекты лечения",
                "паспорт здоровья пациента",
                "Возвращение к жизни",
                "возврат к работе и привычному ритму",
                "физическая реабилитация",
                "эмоциональное восстановление",
                "Долгосрочное здоровье",
                "профилактика рецидива",
                "репродуктивное здоровье после лечения",
                "психологическое благополучие в долгосрочной перспективе",
            ],
        ),
        (
            "children.about.types",
            [
                "Лейкозы",
                "Острый лимфобластный лейкоз (ОЛЛ)",
                "Острый миелолейкоз (ОМЛ)",
                "Лимфомы",
                "Лимфома Ходжкина",
                "Неходжкинская лимфома",
                "Поражают лимфатическую систему",
                "Опухоли мозга",
                "Медуллобластома",
                "Астроцитома",
                "Второй по частоте вид рака у детей",
                "Нейробластома",
                "Опухоль, возникающая из нервных клеток, чаще — надпочечников",
                "Саркомы",
                "Саркома мягких тканей и Юинга — поражают мышцы и кости",
                "Другие виды",
                "Опухоль Вилмса, ретинобластома, гепатобластома и другие редкие формы",
            ],
        ),
        ("children.about.team", ["педиатр, онколог, медсестра, психолог"]),
        ("children.about.genetics", ["когда стоит проверить семью"]),
        ("children.about.stats", ["распространенность, тренды", "беречь детей от пестицидов"]),
        (
            "children.diagnosis.diagnostics",
            [
                "лабораторные анализы: что они показывают",
                "КТ, МРТ, ПЭТ — зачем нужны и как проходят",
                "биопсия и гистологическое исследование",
                "как читать результаты: словарь для родителей",
                "вопросы, которые важно задать врачу",
                "Биопсия",
            ],
        ),
        (
            "children.diagnosis.treatment",
            [
                "химиотерапия: как работает, побочные эффекты",
                "лучевая терапия у детей",
                "трансплантация костного мозга",
                "иммунотерапия и таргетная терапия",
                "клинические испытания: что это и как попасть",
            ],
        ),
        (
            "children.care",
            [
                "Физический уход",
                "питание во время химиотерапии",
                "управление болью",
                "инфекционная безопасность",
                "центральные венозные катетеры",
                "Эмоциональная поддержка",
                "как говорить с ребенком о болезни",
                "работа с тревогой у родителей",
                "поддержка братьев и сестер",
                "психологические службы",
                "Практические вопросы",
                "обучение в больнице",
                "финансовая помощь семьям",
                "права ребенка-пациента",
                "группы поддержки",
            ],
        ),
        (
            "children.family",
            [
                "Для родителей",
                "как справляться с эмоциями и не выгореть",
                "уход за собой во время лечения ребенка",
                "как общаться с медицинской командой",
                "совместное принятие решений о лечении",
                "ресурсы юридической и финансовой помощи",
                "Для близких",
                "как помочь, когда не знаешь, что сказать",
                "практическая помощь: что реально нужно семье",
                "поддержка братьев и сестер больного ребенка",
                "разговоры с бабушками и дедушками",
                "сообщество семей — группы взаимопомощи",
            ],
        ),
        (
            "children.after",
            [
                "Наблюдение после лечения",
                "график контрольных осмотров",
                "поздние эффекты терапии",
                "паспорт здоровья выжившего",
                "Возвращение к жизни",
                "возврат в школу и учеба",
                "физическая реабилитация",
                "эмоциональное восстановление",
                "Долгосрочное здоровье",
                "рост и развитие",
                "репродуктивное здоровье",
                "профилактика рецидива",
            ],
        ),
    ],
)
def test_tz_bullets_verbatim_ru(seeded, key: str, snippets: list[str]) -> None:
    text = body_text(page_for(key, "ru"))
    for snippet in snippets:
        assert snippet in text, f"{key}: missing {snippet!r}"


def test_uz_bodies_are_real_uzbek_with_placeholders(seeded) -> None:
    text = body_text(page_for("women.support.breast", "uz"))
    assert "Jismoniy salomatlik" in text
    assert "Hissiy qoʻllab-quvvatlash" in text
    assert "[[VERIFY: doctor]]" in text  # Figma copy (D-065) waits for the doctor
    assert "[[TODO: content — copywriter]]" in body_text(page_for("women.after.breast", "ru"))
    types = body_text(page_for("children.about.types", "uz"))
    assert "Leykozlar" in types
    assert "Neyroblastoma" in types


def test_block_types_match_spec_for_key_pages(seeded) -> None:
    assert "steps" in page_for("women.treatment.breast", "uz").block_types
    assert "steps" in page_for("women.awareness.breast", "uz").block_types
    assert "cards_grid" in page_for("women.awareness.cervical", "uz").block_types
    assert "text_cards" in page_for("women.after.breast", "uz").block_types
    assert page_for("women.support.breast", "uz").block_types.count("three_columns") == 1
    assert page_for("children.family", "uz").block_types.count("two_columns") == 1
    assert "cards_grid" in page_for("children.about.types", "uz").block_types
    assert "glossary_terms" in page_for("children.diagnosis.diagnostics", "ru").block_types
    assert "faq_accordion" in page_for("children.diagnosis.diagnostics", "ru").block_types
    assert "cta" in page_for("women.awareness.breast", "ru").block_types


def test_six_childhood_cancer_cards(seeded) -> None:
    page = page_for("children.about.types", "ru")
    grid = next(b for b in page.body if b.block_type == "cards_grid")
    assert len(grid.value["cards"]) == 6


def test_patient_route_has_four_steps_with_pp402_deadline(seeded) -> None:
    page = page_for("women.treatment.breast", "ru")
    steps = next(b for b in page.body if b.block_type == "steps")
    assert len(steps.value["steps"]) == 4
    assert steps.value["steps"][2]["deadline"] == "[[VERIFY: PP-402 referral deadlines]]"


def test_short_directory_url_redirects(seeded, client: Client) -> None:
    response = client.get("/uz/qayerga-murojaat/")
    assert response.status_code == 301
    assert response["Location"].endswith("/uz/ayollar/qayerga-murojaat/")
    response = client.get("/ru/kuda-obratitsya/")
    assert response.status_code == 301


# ---------------------------------------------------------------------------
# idempotency + gate: every page 200 in uz and ru
# ---------------------------------------------------------------------------
def test_seed_is_idempotent(seeded) -> None:
    before = Page.objects.count()
    result = Seeder().run()
    assert result["created"] == 0
    assert result["updated"] == 0
    assert Page.objects.count() == before


def test_management_command_runs(seeded, capsys) -> None:
    call_command("seed_content", lang="uz,ru")
    assert "created=0" in capsys.readouterr().out


def test_management_command_rejects_unknown_language(seeded) -> None:
    from django.core.management.base import CommandError

    with pytest.raises(CommandError):
        call_command("seed_content", lang="uz,en")


def test_every_live_page_returns_200_in_both_languages(seeded, client: Client) -> None:
    pages = Page.objects.live().filter(depth__gte=2).exclude(url_path="/").specific()
    seen = 0
    for page in pages:
        url = page.url
        assert url, page
        response = client.get(url)
        if getattr(page, "is_variant_group", False) or getattr(page, "open_first_topic", False):
            # D-066: a variant group / the women's section opens its first child (≤ 2 hops)
            for _hop in range(2):
                if response.status_code != 302:
                    break
                response = client.get(response["Location"])
        assert response.status_code == 200, (url, response.status_code)
        assert f'lang="{page.locale.language_code}"' in response.content.decode()
        seen += 1
    assert seen >= 2 * len(tree.iter_nodes()) + 2
