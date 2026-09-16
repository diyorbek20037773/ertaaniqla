"""Anonymous page cache (spec §4.5): hit/miss, nonce swap, invalidation on publish, bypass for
cookies/POST/HTMX partial keys, and the analytics/a11y client hooks."""

from __future__ import annotations

import re

import pytest
from django.test import Client, override_settings

from apps.articles.models import ArticlePage
from apps.core.cache import bump_page_cache, page_cache_version

pytestmark = pytest.mark.django_db


@override_settings(PAGE_CACHE_SECONDS=300)
def test_cache_hit_swaps_nonce_and_publish_invalidates(seeded, client: Client) -> None:
    article = ArticlePage.objects.get(slug="belgilar", locale__language_code="uz")
    first = client.get(article.url)
    assert first["X-Page-Cache"] == "MISS"
    assert "max-age=300" in first["Cache-Control"]
    second = client.get(article.url)
    assert second["X-Page-Cache"] == "HIT"
    nonce_first = re.search(r'nonce="([^"]+)"', first.content.decode()).group(1)
    nonce_second = re.search(r'nonce="([^"]+)"', second.content.decode()).group(1)
    assert nonce_first != nonce_second
    csp_second = second["Content-Security-Policy"]
    assert nonce_second in csp_second  # HTML nonce matches the header nonce
    assert nonce_first not in second.content.decode()

    article.title = "Belgilar (yangilandi)"
    article.save_revision().publish()
    third = client.get(article.url)
    assert third["X-Page-Cache"] == "MISS"
    assert "Belgilar (yangilandi)" in third.content.decode()


@override_settings(PAGE_CACHE_SECONDS=300)
def test_cache_bypasses(seeded, client: Client, user) -> None:
    url = "/uz/ayollar/"
    assert client.get(url)["X-Page-Cache"] == "MISS"
    assert client.get(url)["X-Page-Cache"] == "HIT"
    # HTMX partials have their own key
    partial = client.get("/uz/qidiruv/?q=skrining", HTTP_HX_REQUEST="true")
    assert partial["X-Page-Cache"] == "MISS"
    assert client.get("/uz/qidiruv/?q=skrining")["X-Page-Cache"] == "MISS"  # full page ≠ partial
    # logged-in users never get cached pages
    client.force_login(user)
    assert not client.get(url).has_header("X-Page-Cache")
    # POST is never cached
    anon = Client()
    assert not anon.post("/uz/savol-javob/", {}).has_header("X-Page-Cache")
    # pages that set cookies (CSRF form) are never stored, so no cache header at all
    assert not anon.get("/uz/savol-javob/").has_header("X-Page-Cache")
    assert not anon.get("/uz/savol-javob/").has_header("X-Page-Cache")


def test_cache_disabled_by_default(seeded, client: Client) -> None:
    assert not client.get("/uz/").has_header("X-Page-Cache")


def test_version_bump() -> None:
    v = page_cache_version()
    assert bump_page_cache() == v + 1


def test_consent_banner_and_toolbar_markup(seeded, client: Client) -> None:
    from wagtail.models import Site

    from apps.core.models import SiteSettings

    html = client.get("/uz/").content.decode()
    assert 'data-component="a11y-toolbar"' in html
    assert 'data-component="consent"' not in html  # no Metrika id → no banner
    settings_obj, _ = SiteSettings.objects.get_or_create(
        site=Site.objects.get(is_default_site=True)
    )
    settings_obj.metrika_id = "12345678"
    settings_obj.save()
    html = client.get("/uz/").content.decode()
    assert 'data-metrika-id="12345678"' in html and "mc.yandex.ru" not in html
