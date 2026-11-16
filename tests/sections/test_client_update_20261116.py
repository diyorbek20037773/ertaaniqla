"""The doctor's patient route for cervical screening and the client's wording without «murojaat»
(D-113, docs/new_edits/ of 2026-11-16): 8 steps with where each takes place, the result
branches, «what CIN means»; the header button, the directory page's name, its filter order and
the state-programme label; `client_update_20261116` bringing a live site there."""

from __future__ import annotations

import io
import json
from typing import Any

import pytest
from django.core.management import call_command
from django.test import Client
from wagtail.models import Page, Site

from apps.core.models import SiteSettings
from apps.directory.models import DirectoryPage

pytestmark = pytest.mark.django_db
SCREENING_UZ = "/uz/ayollar/skrining/bachadon-boyni-saratoni/"
SCREENING_RU = "/ru/zhenskiy/skrining/rak-sheyki-matki/"


def _route(html: str) -> str:
    return html.split('id="screening-route"', 1)[1].split("</section>", 1)[0]


def test_route_has_the_doctors_eight_steps(seeded: Any, client: Client) -> None:
    route = _route(client.get(SCREENING_UZ).content.decode())
    assert ">Tekshiruv qadamlari</h2>" in route
    assert route.count('class="screening-route__step"') == 8
    for title in (
        "Tekshiruvga taklif",
        "Ginekolog qabuli va tahlil olish",
        "Davolash",
        "Boshqa ayollar koʻmagi",
    ):
        assert f">{title}</h3>" in route
    assert route.count('class="screening-route__where"') == 7 + 5  # 7 steps say where, 5 branches
    assert route.count('class="screening-route__outcome"') == 5
    assert "HPV aniqlanmadi" in route and "Oʻrtacha va kuchli oʻzgarishlar (CIN 2–3)" in route
    assert ">CIN nima degani</h3>" in route and "Bu hali saraton emas." in route
    ru = _route(client.get(SCREENING_RU).content.decode())
    assert ">Этапы обследования</h2>" in ru
    assert "Женщин 30–50 лет приглашают на скрининг по списку, не дожидаясь жалоб." in ru
    assert "Биопсия, затем лечение (конизация) без перехода к онкологу." in ru
    assert "Онкологический центр (РОНЦ / региональный)" in ru


def test_wording_without_murojaat(seeded: Any, client: Client) -> None:
    home = client.get("/uz/").content.decode()
    assert "Sizning tekshiruv yoʻlagingiz" in home and "Skrining joyini toping" not in home
    assert "Ваш путь к проверке" in client.get("/ru/").content.decode()
    directory = DirectoryPage.objects.get(locale__language_code="uz")
    html = client.get(directory.url).content.decode()
    assert "<h1>Tekshiruv yoʻlagi va tibbiyot muassasalari</h1>" in html
    assert "Qayerga murojaat qilish" not in html and "Murojaat qilish" not in html
    assert ">Davlat dasturi doirasida</label>" in html
    form = html.split('class="filter-form"', 1)[1]
    order = [form.index(f'for="filter-{name}"') for name in ("section", "region", "kind", "q")]
    assert order == sorted(order)  # section first, then region and type
    ru = DirectoryPage.objects.get(locale__language_code="ru")
    assert ru.title == "Медицинские учреждения и путь проверки"
    footer = html.split('class="site-footer"', 1)[1]
    assert f'href="{directory.url}">Tekshiruv yoʻlagi va tibbiyot muassasalari</a>' in footer


def _old_site() -> tuple[Any, Any]:
    """Production before the update: the D-105 route, the old names and pill."""
    old_route = {
        "title": "Skriningni qayerda oʻtasiz",
        "intro": "<p>Viloyatingiz va tumaningizni tanlang.</p>",
        "steps": [
            {
                "title": "Tahlil topshirish",
                "text": "<p>Eski matn</p>",
                "places": "district_polyclinics",
            }
        ],
    }
    screening = Page.objects.get(
        url_path__endswith="/ayollar/skrining/bachadon-boyni-saratoni/"
    ).specific
    raw = json.loads(json.dumps(list(screening.body.raw_data)))
    for block in raw:
        if block["type"] == "screening_route":
            block["value"] = old_route
        if block["type"] == "cta":
            block["value"]["button_label"] = "Murojaat qilish"
    screening.body = raw
    screening.save_revision().publish()
    directory = DirectoryPage.objects.get(locale__language_code="uz")
    directory.title = directory.draft_title = "Qayerga murojaat qilish"
    directory.save_revision().publish()
    settings = SiteSettings.for_site(Site.objects.get(is_default_site=True))
    columns = json.loads(json.dumps(list(settings.footer_columns_uz.raw_data)))
    for column in columns:
        for link in column["value"]["links"]:
            value = link.get("value", link)
            if value.get("page") == directory.pk:
                value["label"] = "Murojaat qilish"
    settings.footer_columns_uz = columns
    settings.save()
    return screening, directory


def test_one_off_update_brings_a_live_site_there(seeded: Any, client: Client) -> None:
    screening, directory = _old_site()
    out = io.StringIO()
    call_command("client_update_20261116", stdout=out)
    assert f"updated (body): {screening.url_path}" in out.getvalue()
    assert "footer links renamed: 1" in out.getvalue()
    directory.refresh_from_db()
    assert directory.title == "Tekshiruv yoʻlagi va tibbiyot muassasalari"
    html = client.get(SCREENING_UZ).content.decode()
    route = _route(html)
    assert route.count('class="screening-route__step"') == 8 and "Tahlil topshirish" not in route
    assert "Murojaat qilish" not in html and "Sizning tekshiruv yoʻlagingiz" in html
    out = io.StringIO()
    call_command("client_update_20261116", stdout=out)
    assert out.getvalue().strip() == "footer links renamed: 0"  # nothing left to do


def test_one_off_update_leaves_an_editors_draft(seeded: Any, admin_user: Any) -> None:
    screening, _directory = _old_site()
    screening.title = "Muharrir qoralamasi"
    screening.save_revision(user=admin_user)
    out = io.StringIO()
    call_command("client_update_20261116", stdout=out)
    assert f"skipped (unpublished draft): {screening.url_path}" in out.getvalue()


def test_one_off_update_fixes_the_first_wording(seeded: Any, client: Client) -> None:
    """«Sizning tekshiruv yoʻlagi» was live for a day; the grammar wants «…yoʻlagingiz»."""
    screening, _directory = _old_site()
    raw = json.loads(json.dumps(list(screening.body.raw_data)))
    for block in raw:
        if block["type"] == "cta":
            block["value"]["button_label"] = "Sizning tekshiruv yoʻlagi"
    screening.body = raw
    screening.save_revision().publish()
    call_command("client_update_20261116", stdout=io.StringIO())
    html = client.get(SCREENING_UZ).content.decode()
    assert "Sizning tekshiruv yoʻlagingiz" in html
    assert html.count("Sizning tekshiruv yoʻlagi") == html.count("Sizning tekshiruv yoʻlagingiz")
