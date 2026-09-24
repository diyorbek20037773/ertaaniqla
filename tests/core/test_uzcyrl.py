"""Uzbek Cyrillic site version: transliteration rules and the /oz/ middleware (D-047, D-049)."""

from __future__ import annotations

import re
import time

import pytest
from django.test import Client, override_settings

from apps.core.uzcyrl import transliterate, transliterate_html, transliterate_json_value

# --- word rules (table-driven) ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("latin", "cyrillic"),
    [
        ("Erta aniqla", "Эрта аниқла"),
        ("Koʻkrak bezi saratoni", "Кўкрак бези саратони"),
        ("ko'krak", "кўкрак"),  # ASCII apostrophe typed by editors
        ("ko‘krak", "кўкрак"),
        ("gʻamxoʻrlik", "ғамхўрлик"),
        ("bog'", "боғ"),  # word-final gʻ
        ("O'ZBEKISTON", "ЎЗБЕКИСТОН"),
        ("Oʻzbekiston", "Ўзбекистон"),
        ("Shifokor", "Шифокор"),
        ("chaqaloq", "чақалоқ"),
        ("xavf", "хавф"),
        ("hayot", "ҳаёт"),
        ("jamoa", "жамоа"),
        ("ellik", "эллик"),  # e at word start → э
        ("poeziya", "поэзия"),  # e after a vowel → э
        ("aeroport", "аэропорт"),
        ("tekshiruv", "текширув"),  # e after a consonant → е
        ("yer", "ер"),
        ("diyeta", "диета"),
        ("yosh", "ёш"),
        ("oyoq", "оёқ"),
        ("yurak", "юрак"),
        ("qiyomat", "қиёмат"),
        ("maʼno", "маъно"),  # tutuq belgisi → ъ
        ("ta’lim", "таълим"),
        ("Isʼhoq", "Исҳоқ"),  # sʼh keeps s and h apart
        ("operatsiya", "операция"),
        ("revolyutsion", "революцион"),
        ("oʻtsa", "ўтса"),  # native t+s stays тс
        ("vaksinalar", "вакциналар"),
        ("sentabr", "сентябрь"),
        ("sentabrda", "сентябрда"),
        ("rayon", "район"),
        ("Yandex", "Яндекс"),
        ("Telegram", "Telegram"),
        ("WhatsApp", "WhatsApp"),
        ("HPV-test", "HPV-тест"),
        ("II bosqich", "II босқич"),
        ("PQ-402 boʻyicha", "ПҚ-402 бўйича"),
        ("UTT", "УТТ"),
        ("45–65 yosh", "45–65 ёш"),
    ],
)
def test_word_rules(latin: str, cyrillic: str) -> None:
    assert transliterate(latin) == cyrillic


def test_protected_chunks_are_untouched() -> None:
    text = "[[TODO: content — copywriter]] matn https://t.me/erta_aniqla?x=1 va info@ertaaniqla.uz"
    assert transliterate(text) == (
        "[[TODO: content — copywriter]] матн https://t.me/erta_aniqla?x=1 ва info@ertaaniqla.uz"
    )
    assert transliterate("Рак молочной железы 2026") == "Рак молочной железы 2026"
    assert transliterate("") == ""
    assert transliterate("&nbsp;salom&amp;") == "&nbsp;салом&amp;"


def test_html_converts_text_and_text_attributes_only() -> None:
    html = (
        '<html lang="uz"><head><title>Bosh sahifa</title>'
        '<meta name="description" content="Erta aniqlash">'
        '<meta property="og:url" content="https://ertaaniqla.uz/uz/">'
        '<script nonce="n">var label = "salom";</script>'
        "<style>.shifokor{color:red}</style></head>"
        '<body><a href="/uz/ayollar/" title="Ayollar" class="shifokor">Ayollar saratoni</a>'
        '<img alt="Rasm" src="/media/rasm.png"><input placeholder="Qidiruv" name="q">'
        "<code>make check</code><pre>docker compose</pre>"
        '<span translate="no">Oʻzbekcha <b>lotin</b></span> keyin'
        "<div data-no-translit><div>ichki</div> tashqi</div> oxiri"
        "<!-- izoh --></body></html>"
    )
    out = transliterate_html(html)
    assert "<title>Бош саҳифа</title>" in out
    assert 'content="Эрта аниқлаш"' in out
    assert 'content="https://ertaaniqla.uz/uz/"' in out  # URLs are the middleware's job
    assert 'var label = "salom";' in out and ".shifokor{color:red}" in out
    assert 'href="/uz/ayollar/" title="Аёллар" class="shifokor">Аёллар саратони</a>' in out
    assert 'alt="Расм" src="/media/rasm.png"' in out
    assert 'placeholder="Қидирув" name="q"' in out
    assert "<code>make check</code><pre>docker compose</pre>" in out
    assert '<span translate="no">Oʻzbekcha <b>lotin</b></span> кейин' in out
    assert "<div data-no-translit><div>ichki</div> tashqi</div> охири" in out
    assert "<!-- izoh -->" in out


def test_json_islands_convert_text_values_not_keys_or_urls() -> None:
    html = (
        '<script type="application/json" id="map-data">'
        '[{"name": "Poliklinika", "kind": "polyclinic", "url": "/uz/a/", "lat": 41.3}]</script>'
        '<script type="application/ld+json">{"@type": "MedicalWebPage", "name": "Belgilar"}'
        "</script>"
    )
    out = transliterate_html(html)
    assert '"name": "Поликлиника", "kind": "polyclinic", "url": "/uz/a/", "lat": 41.3' in out
    assert '"@type": "MedicalWebPage", "name": "Белгилар"' in out
    assert transliterate_json_value({"a": ["salom", 1, None]}) == {"a": ["салом", 1, None]}
    broken = '<script type="application/json">{not json</script>'
    assert transliterate_html(broken) == broken


def test_transliteration_is_fast_enough() -> None:
    body = "<p>Koʻkrak bezi saratoni erta aniqlansa, davolash natijasi yaxshi boʻladi.</p>" * 800
    started = time.perf_counter()
    transliterate_html(body)
    assert time.perf_counter() - started < 1.0  # ~60 KB page, uncached, generous CI bound


# --- /oz/ middleware ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_every_live_uz_page_is_served_in_cyrillic(seeded, client: Client) -> None:
    from wagtail.models import Page

    pages = Page.objects.live().filter(locale__language_code="uz", depth__gte=2).specific()
    urls = [p.url for p in pages if p.url]
    assert len(urls) > 30
    for url in urls:
        response = client.get("/oz/" + url[4:])
        for _hop in range(2):  # D-066: variant groups open their first child
            if response.status_code != 302:
                break
            assert response["Location"].startswith("/oz/"), url
            response = client.get(response["Location"])
        assert response.status_code == 200, url
        assert '<html lang="uz-Cyrl"' in response.content.decode(), url
        assert response["Content-Language"] == "uz-Cyrl"


@pytest.mark.django_db
def test_cyrillic_page_links_titles_and_alternates(seeded, client: Client) -> None:
    html = client.get("/oz/ayollar/ogohlik/kokrak-bezi-saratoni/").content.decode()
    assert "<title>Кўкрак бези саратони — Эрта аниқла</title>" in html
    assert (
        '<link rel="canonical" href="http://localhost/oz/ayollar/ogohlik/kokrak-bezi-saratoni/">'
        in html
    )
    assert (
        'property="og:url" content="http://localhost/oz/ayollar/ogohlik/kokrak-bezi-saratoni/"'
        in html
    )
    assert (
        '<link rel="alternate" hreflang="uz" '
        'href="http://localhost/uz/ayollar/ogohlik/kokrak-bezi-saratoni/" '
        "data-script-keep>" in html
    )
    assert (
        'hreflang="ru" href="http://localhost/ru/zhenskiy/osvedomlennost/rak-molochnoy-zhelezy/"'
        in html
    )
    # switcher: the Latin link is kept, Cyrillic is current, names are never transliterated
    assert 'aria-current="true" lang="uz-Cyrl" translate="no">Ўзбекча</span>' in html
    assert ">Oʻzbekcha</a>" in html
    # every other internal Uzbek link stays inside /oz/
    assert re.findall(r'<a [^>]*href="(/uz/[^"]*)"', html) == [
        "/uz/ayollar/ogohlik/kokrak-bezi-saratoni/"
    ]
    assert 'href="/oz/ayollar/"' in html
    assert "%2Foz%2Fayollar%2Fogohlik%2Fkokrak-bezi-saratoni%2F" in html  # share links
    visible = re.sub(r"<script.*?</script>|<style.*?</style>|<[^>]+>", " ", html, flags=re.S)
    visible = re.sub(r"\[\[[^\]]*\]\]", " ", visible)
    latin_words = set(re.findall(r"[A-Za-z]{3,}", visible)) - {"Oʻzbekcha", "zbekcha"}
    brands = {"Telegram", "WhatsApp", "Facebook", "Instagram", "TikTok", "YouTube"}
    brands |= {"logo", "Agency", "Yandex", "Hamroh"}  # translate="no" design placeholders
    assert latin_words <= brands, latin_words


@pytest.mark.django_db
def test_latin_and_russian_pages_are_unchanged(seeded, client: Client) -> None:
    uz = client.get("/uz/ayollar/ogohlik/kokrak-bezi-saratoni/").content.decode()
    assert '<html lang="uz"' in uz and "Koʻkrak bezi saratoni" in uz
    assert (
        'hreflang="uz-Cyrl" href="http://localhost/oz/ayollar/ogohlik/kokrak-bezi-saratoni/"' in uz
    )
    ru = client.get("/ru/zhenskiy/osvedomlennost/rak-molochnoy-zhelezy/").content.decode()
    assert '<html lang="ru"' in ru
    assert 'href="/oz/ayollar/ogohlik/kokrak-bezi-saratoni/" hreflang="uz-Cyrl"' in ru


@pytest.mark.django_db
def test_redirects_search_htmx_and_sitemap(seeded, client: Client) -> None:
    bare = client.get("/oz")
    assert bare.status_code == 301 and bare["Location"] == "/oz/"
    no_slash = client.get("/oz/ayollar")
    assert no_slash.status_code in (301, 302)
    assert no_slash["Location"].startswith("/oz/ayollar/")
    search = client.get("/oz/qidiruv/?q=скрининг")
    assert search.status_code == 200
    assert "/oz/ayollar/skrining/" in search.content.decode()
    partial = client.get("/oz/qidiruv/?q=saraton", HTTP_HX_REQUEST="true")
    assert partial.status_code == 200 and "<html" not in partial.content.decode()
    assert "саратон" in partial.content.decode().lower()
    sitemap = client.get("/oz/sitemap.xml").content.decode()
    assert "<loc>http://localhost/oz/ayollar/" in sitemap and "/uz/" not in sitemap
    assert client.get("/oz/mavjud-emas-sahifa/").status_code == 404


@pytest.mark.django_db
def test_directory_htmx_and_map_island_in_cyrillic(seeded, client: Client) -> None:
    from django.core.management import call_command

    call_command("import_institutions", "data/institutions.sample.csv", verbosity=0)
    html = client.get("/oz/ayollar/qayerga-murojaat/").content.decode()
    island = re.search(r'<script type="application/json" id="map-data">(.*?)</script>', html, re.S)
    assert island is not None and "Юнусобод" in island.group(1)
    partial = client.get(
        "/oz/ayollar/qayerga-murojaat/?region=tashkent-city", HTTP_HX_REQUEST="true"
    ).content.decode()
    assert "Юнусобод" in partial


@pytest.mark.django_db
def test_forms_post_under_oz(seeded, client: Client) -> None:
    html = client.get("/oz/savol-javob/").content.decode()
    actions = re.findall(r'<form[^>]*action="([^"]*)"', html) + re.findall(
        r'hx-post="([^"]*)"', html
    )
    assert actions and all(a.startswith("/oz/") or not a.startswith("/") for a in actions), actions


@pytest.mark.django_db
@override_settings(PAGE_CACHE_SECONDS=300)
def test_page_cache_is_shared_and_nonce_survives(seeded) -> None:
    client = Client()
    first = client.get("/oz/bolalar/")
    second = client.get("/oz/bolalar/")
    latin = client.get("/uz/bolalar/")
    assert first["X-Page-Cache"] == "MISS" and second["X-Page-Cache"] == "HIT"
    assert latin["X-Page-Cache"] == "HIT"  # one cached Latin page serves both scripts
    assert '<html lang="uz"' in latin.content.decode()
    nonce = re.search(r'nonce="([^"]+)"', second.content.decode())
    assert nonce is not None and f"'nonce-{nonce.group(1)}'" in second["Content-Security-Policy"]


@pytest.mark.django_db
@override_settings(UZ_CYRILLIC_ENABLED=False)
def test_can_be_switched_off(seeded, client: Client) -> None:
    response = client.get("/oz/bolalar/", follow=True)  # unknown prefix → /uz/oz/… → 404
    assert response.status_code == 404
    html = client.get("/uz/bolalar/").content.decode()
    assert "uz-Cyrl" not in html and "Ўзбекча" not in html
