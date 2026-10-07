"""Anonymous page cache (spec §4.5): hit/miss, nonce swap, invalidation on publish, bypass for
cookies/POST/HTMX partial keys, and the analytics/a11y client hooks."""

from __future__ import annotations

import json
import re

import pytest
from django.test import Client, override_settings

from apps.articles.models import ArticlePage
from apps.core.cache import build_id, bump_page_cache, page_cache_key, page_cache_version

pytestmark = pytest.mark.django_db


@override_settings(PAGE_CACHE_SECONDS=300)
def test_cache_hit_swaps_nonce_and_publish_invalidates(seeded, client: Client) -> None:
    article = ArticlePage.objects.get(
        url_path__endswith="/ayollar/ogohlik/kokrak-bezi-saratoni/", locale__language_code="uz"
    )
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
    url = "/uz/bolalar/"
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


def test_new_deploy_gets_a_fresh_cache(tmp_path, rf, settings) -> None:
    """Cached HTML names hashed CSS/JS files; after a deploy those files are gone, so the key
    carries the static-manifest hash (otherwise a page served from cache loads no styles)."""
    settings.STATIC_ROOT = tmp_path
    request = rf.get("/uz/")
    keys = []
    for hashed in ("main.aaa.css", "main.bbb.css"):
        manifest = json.dumps({"paths": {"main.css": hashed}})
        (tmp_path / "staticfiles.json").write_text(manifest, encoding="utf-8")
        build_id.cache_clear()
        keys.append(page_cache_key(request))
    build_id.cache_clear()
    assert keys[0] != keys[1]


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


@override_settings(PAGE_CACHE_SECONDS=300)
def test_pages_with_a_csrf_token_are_never_cached(seeded) -> None:
    """EA-25: a cached form page carried the first visitor's CSRF token and set no cookie
    for the next one (403 on submit). Pages that use a token stay private and uncached."""
    first = Client().get("/uz/savol-javob/")
    assert "csrftoken" in first.cookies
    assert "public" not in first.get("Cache-Control", "")
    second = Client().get("/uz/savol-javob/")
    assert second.get("X-Page-Cache") != "HIT"
    assert "csrftoken" in second.cookies
    # plain content pages are still cached
    Client().get("/uz/lugat/")
    assert Client().get("/uz/lugat/").get("X-Page-Cache") == "HIT"
