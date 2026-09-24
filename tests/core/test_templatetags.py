"""core_tags: language switcher, hreflang, breadcrumbs, canonical, phone filters (F1, §7)."""

from __future__ import annotations

import pytest
from django.template import Context, Template
from django.test import Client, RequestFactory
from django.utils import translation
from wagtail.models import Locale

from apps.articles.models import ArticlePage
from apps.core.templatetags.core_tags import (
    localized,
    phone_display,
    phone_href,
    section_style,
    translated_url,
)

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("raw", "display", "href"),
    [
        ("+998901234567", "+998 90 123-45-67", "tel:+998901234567"),
        ("998 71 200 11 22", "+998 71 200-11-22", "tel:+998712001122"),
        ("901234567", "+998 90 123-45-67", "tel:+998901234567"),
        ("1001", "1001", "tel:+1001"),
        ("", "", ""),
    ],
)
def test_phone_filters(raw: str, display: str, href: str) -> None:
    assert phone_display(raw) == display
    assert phone_href(raw) == href


def test_translated_url_points_to_counterpart(seeded) -> None:
    article = ArticlePage.objects.get(
        url_path__endswith="/ayollar/ogohlik/kokrak-bezi-saratoni/", locale__language_code="uz"
    )
    assert translated_url(article, "ru") == "/ru/zhenskiy/osvedomlennost/rak-molochnoy-zhelezy/"
    assert translated_url(article, "uz") == article.url


def test_translated_url_falls_back_to_section_then_root(seeded) -> None:
    article = ArticlePage.objects.get(
        url_path__endswith="/ayollar/ogohlik/kokrak-bezi-saratoni/", locale__language_code="uz"
    )
    ru = article.get_translation(Locale.objects.get(language_code="ru"))
    ru.unpublish()
    assert translated_url(article, "ru") == "/ru/zhenskiy/"
    assert translated_url(None, "ru") == "/ru/"
    assert translated_url(article, "de") == "/de/"


def test_language_switcher_links_to_counterpart(seeded, client: Client) -> None:
    html = client.get("/uz/ayollar/ogohlik/kokrak-bezi-saratoni/").content.decode()
    assert 'href="/ru/zhenskiy/osvedomlennost/rak-molochnoy-zhelezy/" hreflang="ru"' in html
    assert 'aria-current="true" lang="uz"' in html


def test_hreflang_and_canonical_in_head(seeded, client: Client) -> None:
    html = client.get("/ru/detskiy/").content.decode()
    # origin = Wagtail Site hostname (canonical domain), not the request host
    assert (
        '<link rel="alternate" hreflang="uz" href="http://localhost/uz/bolalar/" data-script-keep>'
        in html
    )
    assert '<link rel="alternate" hreflang="uz-Cyrl" href="http://localhost/oz/bolalar/">' in html
    assert '<link rel="alternate" hreflang="ru" href="http://localhost/ru/detskiy/">' in html
    assert (
        '<link rel="alternate" hreflang="x-default" href="http://localhost/uz/bolalar/" '
        "data-script-keep>" in html
    )
    assert '<link rel="canonical" href="http://localhost/ru/detskiy/">' in html


def test_breadcrumbs_on_nested_page(seeded, client: Client) -> None:
    html = client.get("/ru/zhenskiy/skrining/rak-molochnoy-zhelezy/").content.decode()
    assert 'aria-label="Хлебные крошки"' in html or "breadcrumbs" in html
    assert '<span aria-current="page">Рак молочной железы</span>' in html
    assert 'href="/ru/zhenskiy/skrining/"' in html
    home_html = client.get("/ru/").content.decode()
    assert "breadcrumbs__list" not in home_html


def test_tags_degrade_without_page(seeded) -> None:
    request = RequestFactory().get("/uz/qidiruv/")
    with translation.override("uz"):
        html = Template(
            "{% load core_tags %}{% hreflang_links %}|{% canonical_url %}|"
            "{% breadcrumbs %}|{% lang_switch %}"
        ).render(Context({"request": request, "page": None}))
    assert 'hreflang="x-default" href="http://localhost/uz/"' in html
    assert "http://localhost/uz/qidiruv/" in html
    assert 'href="/ru/"' in html


def test_section_style_only_with_colours() -> None:
    class S:
        colour_primary = ""
        colour_accent = ""

    assert section_style(None) == ""
    assert section_style(S()) == ""
    S.colour_primary = "#abcdef"
    S.colour_accent = "#fedcba"
    assert section_style(S()) == "body{--brand:#abcdef;--brand-soft:#fedcba;}"


def test_localized_filter_falls_back_to_uz() -> None:
    class Obj:
        disclaimer_uz = "uz text"
        disclaimer_ru = ""

    with translation.override("ru"):
        assert localized(Obj(), "disclaimer") == "uz text"
    with translation.override("uz"):
        assert localized(Obj(), "disclaimer") == "uz text"
    assert localized(None, "disclaimer") == ""


def test_error_pages_render_without_page_context(seeded, client: Client) -> None:
    response = client.get("/uz/mavjud-emas/")
    assert response.status_code == 404
    html = response.content.decode()
    assert 'lang="uz"' in html
