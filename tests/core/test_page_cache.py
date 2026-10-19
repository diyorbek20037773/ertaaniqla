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
    # D-093: browsers revalidate every navigation (ETag → 304); nginx may keep it 10 s
    assert first["Cache-Control"] == "public, max-age=0, must-revalidate, s-maxage=10"
    assert first["ETag"].startswith('W/"')
    second = client.get(article.url)
    assert second["X-Page-Cache"] == "HIT"
    assert second["ETag"] == first["ETag"]  # the nonce differs, the page does not
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
    assert third["ETag"] != first["ETag"]


@override_settings(PAGE_CACHE_SECONDS=300)
def test_cache_bypasses(children_visible, seeded, client: Client, user) -> None:
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
    assert not first.has_header("ETag")
    second = Client().get("/uz/savol-javob/")
    assert second.get("X-Page-Cache") != "HIT"
    assert "csrftoken" in second.cookies
    # plain content pages are still cached
    Client().get("/uz/lugat/")
    assert Client().get("/uz/lugat/").get("X-Page-Cache") == "HIT"


@override_settings(PAGE_CACHE_SECONDS=300)
def test_revalidation_is_a_304_without_csp(seeded) -> None:
    """D-093: a browser holding the current version gets 304 Not Modified with no body and no
    Content-Security-Policy (a new policy on a 304 would replace the stored one and block the
    stored page's inline nonce script) — from a cache hit and, after the entry is gone, from
    the content-derived ETag."""
    from django.core.cache import cache

    url = "/uz/ayollar/ogohlik/kokrak-bezi-saratoni/"
    etag = Client().get(url)["ETag"]
    hit = Client().get(url, HTTP_IF_NONE_MATCH=etag)
    assert hit.status_code == 304 and hit.content == b""
    assert "Content-Security-Policy" not in hit and hit["ETag"] == etag
    assert hit["Cache-Control"].startswith("public, max-age=0") and hit["X-Page-Cache"] == "HIT"
    cache.clear()  # the server entry is gone; the page itself did not change
    miss = Client().get(url, HTTP_IF_NONE_MATCH=etag)
    assert miss.status_code == 304 and "Content-Security-Policy" not in miss
    assert Client().get(url, HTTP_IF_NONE_MATCH="*").status_code == 304
    other = Client().get(url, HTTP_IF_NONE_MATCH='W/"0000"')
    assert other.status_code == 200 and "Content-Security-Policy" in other
    article = ArticlePage.objects.get(url_path__endswith=url[3:], locale__language_code="uz")
    article.title = "Yangi sarlavha"
    article.save_revision().publish()
    changed = Client().get(url, HTTP_IF_NONE_MATCH=etag)
    assert changed.status_code == 200 and "Yangi sarlavha" in changed.content.decode()


@override_settings(PAGE_CACHE_SECONDS=300)
def test_server_entry_lives_page_cache_seconds(seeded, monkeypatch) -> None:
    from apps.core import cache as page_cache

    timeouts = []
    real_set = page_cache.cache.set

    def recording_set(key, value, timeout=None, *args, **kwargs):  # type: ignore[no-untyped-def]
        if str(key).startswith("page-cache:") and key != page_cache.VERSION_KEY:
            timeouts.append(timeout)
        return real_set(key, value, timeout, *args, **kwargs)

    monkeypatch.setattr(page_cache.cache, "set", recording_set)
    Client().get("/uz/lugat/")
    assert timeouts == [300]  # not 300 + an hour of stale copies


def test_etag_tracks_release_and_ignores_the_nonce(tmp_path, settings) -> None:
    from apps.core.cache import page_etag

    settings.STATIC_ROOT = tmp_path
    (tmp_path / "staticfiles.json").write_text('{"paths": {}}', encoding="utf-8")
    tags = []
    for release in ("aaa111", "bbb222"):
        settings.APP_RELEASE = release
        build_id.cache_clear()
        tags.append(page_etag(b'<script nonce="n1">x</script>', "n1"))
        assert tags[-1] == page_etag(b'<script nonce="n2">x</script>', "n2")
    build_id.cache_clear()
    assert tags[0] != tags[1]  # a deploy that changes no static file still changes the ETag


@override_settings(PAGE_CACHE_SECONDS=300)
def test_latin_and_cyrillic_views_are_cached_apart(seeded) -> None:
    """/oz/ is rendered by the /uz/ view; sharing one entry showed «UZ» as the active language
    on Cyrillic pages (and hid the way back to Latin)."""
    url = "/uz/haqimizda/"
    Client().get(url.replace("/uz/", "/oz/"), follow=True)
    latin = Client().get(url).content.decode()
    assert re.search(r'class="lang-seg__item is-active"[^>]*>UZ<', latin)
    cyrillic = Client().get(url.replace("/uz/", "/oz/"), follow=True).content.decode()
    assert re.search(r'class="lang-seg__item is-active"[^>]*>ЎЗ<', cyrillic)
    assert 'href="/uz/haqimizda/"' in cyrillic  # the way back to Latin stays a link
