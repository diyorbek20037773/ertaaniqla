"""Tool pages: waffle flags, forms, HTMX partials, disclaimer, seeded in both languages."""

from __future__ import annotations

import pytest
from django.core.cache import cache
from django.test import Client, override_settings
from waffle.models import Flag

from apps.tools.models import FLAG_SCREENING, ScreeningToolPage, SelfCheckPage, ToolsIndexPage

pytestmark = pytest.mark.django_db


def test_seeded_tool_pages_in_both_languages(seeded, client: Client) -> None:
    for url in (
        "/uz/vositalar/",
        "/ru/instrumenty/",
        "/uz/vositalar/skrining/",
        "/ru/instrumenty/skrining/",
        "/uz/vositalar/oz-tekshiruv/",
        "/ru/instrumenty/samoproverka/",
        "/uz/vositalar/bolalar-belgilari/",
        "/ru/instrumenty/priznaki-u-detey/",
    ):
        response = client.get(url)
        assert response.status_code == 200, url
        assert 'class="disclaimer"' in response.content.decode(), url


def test_index_lists_three_tools(seeded, client: Client) -> None:
    html = client.get("/uz/vositalar/").content.decode()
    assert html.count('<article class="card">') == 3


def test_screening_post_full_page_and_htmx(seeded, client: Client) -> None:
    page = ScreeningToolPage.objects.get(locale__language_code="uz")
    data = {"age": 50, "last_mammography": "never", "last_ultrasound": "never", "last_hpv": "1"}
    html = client.post(page.url, data).content.decode()
    assert "tool-result--due" in html
    assert "tool-result__test--due" in html
    assert "tool-result__test--not_applicable" in html  # ultrasound at 50
    partial = client.post(page.url, data, HTTP_HX_REQUEST="true").content.decode()
    assert "<html" not in partial and "tool-result" in partial
    assert 'href="/uz/ayollar/qayerga-murojaat/"' in partial  # where_page CTA when due


def test_screening_invalid_age_shows_errors(seeded, client: Client) -> None:
    page = ScreeningToolPage.objects.get(locale__language_code="ru")
    html = client.post(page.url, {"age": 5}).content.decode()
    assert "form-errors" in html
    assert 'aria-invalid="true"' in html or "field--error" in html


def test_selfcheck_post(seeded, client: Client) -> None:
    page = SelfCheckPage.objects.get(locale__language_code="uz", kind="women")
    ids = [choice for choice, _ in page.item_choices()]
    assert len(ids) == 3
    urgent_id = next(str(c.id) for c in page.items if c.value["urgency"] == "urgent")
    html = client.post(page.url, {"items": [urgent_id]}).content.decode()
    assert "tool-result--urgent" in html
    assert "1 " in html  # "1 of 3 ticked"
    none = client.post(page.url, {}, HTTP_HX_REQUEST="true").content.decode()
    assert "tool-result--none" in none
    children = SelfCheckPage.objects.get(locale__language_code="uz", kind="children")
    assert 'data-section="children"' in client.get(children.url).content.decode()


@override_settings(WAFFLE_FLAG_DEFAULT=False)
def test_flag_off_hides_tools(seeded, client: Client) -> None:
    Flag.objects.update_or_create(name=FLAG_SCREENING, defaults={"everyone": False})
    page = ScreeningToolPage.objects.get(locale__language_code="uz")
    assert client.get(page.url).status_code == 404
    index = ToolsIndexPage.objects.get(locale__language_code="uz")
    html = client.get(index.url).content.decode()
    assert page.title not in html
    Flag.objects.update_or_create(name=FLAG_SCREENING, defaults={"everyone": True})
    cache.clear()  # waffle caches flag objects
    assert client.get(page.url).status_code == 200


def test_body_text_and_section(seeded) -> None:
    page = ScreeningToolPage.objects.get(locale__language_code="uz")
    assert page.section_key == "women"
    assert page.summary in page.get_body_text()
    index = ToolsIndexPage.objects.get(locale__language_code="uz")
    assert index.get_body_text()
