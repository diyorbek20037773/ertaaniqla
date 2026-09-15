"""Site search view and service (spec A4): FTS, synonyms across languages, translit,
HTMX partial + non-JS page, translated URLs."""

from __future__ import annotations

import pytest
from django.core.management import call_command
from django.test import Client

from apps.search.services import search_pages

pytestmark = pytest.mark.django_db


def test_uz_query_finds_ru_page_via_synonym(seeded) -> None:
    results = search_pages("saraton", "ru")
    titles = {r.title for r in results}
    assert "Женский рак" in titles or "Детский рак" in titles
    assert results[0].language_code == "ru"  # visitor's language first


def test_cyrillic_query_finds_latin_page(seeded) -> None:
    results = search_pages("скрининг", "uz")
    assert results
    assert results[0].language_code == "uz"
    assert any(r.url == "/uz/ayollar/skrining/" for r in results)


def test_apostrophe_variants_match_content(seeded) -> None:
    straight = {r.url for r in search_pages("ko'krak", "uz")}
    modifier = {r.url for r in search_pages("koʻkrak", "uz")}
    assert straight and straight == modifier


def test_autocomplete_prefix(seeded) -> None:
    results = search_pages("Kimg", "uz")  # title prefix (AutocompleteField on ArticlePage.title)
    assert any(r.title.startswith("Kimga") for r in results)


def test_empty_and_short_queries(seeded) -> None:
    assert search_pages("", "uz") == []
    assert search_pages("a", "uz") == []


def test_result_fields(seeded) -> None:
    result = search_pages("Belgilar", "uz")[0]
    assert result.title
    assert result.url.startswith("/uz/")
    assert result.section_key in {"women", "children", ""}
    assert result.summary


def test_search_page_translated_urls(seeded, client: Client) -> None:
    uz = client.get("/uz/qidiruv/", {"q": "skrining"})
    assert uz.status_code == 200
    html = uz.content.decode()
    assert 'role="search"' in html
    assert "/uz/ayollar/skrining/" in html
    assert 'name="robots" content="noindex' in html
    ru = client.get("/ru/poisk/", {"q": "скрининг"})
    assert ru.status_code == 200
    assert "/ru/zhenskiy/skrining/" in ru.content.decode()
    assert client.get("/ru/qidiruv/").status_code == 404


def test_search_page_without_query_and_empty_result(seeded, client: Client) -> None:
    html = client.get("/uz/qidiruv/").content.decode()
    assert "search-results__hint" in html
    html = client.get("/uz/qidiruv/", {"q": "qwertyuiopzzz"}).content.decode()
    assert "search-results__empty" in html


def test_htmx_returns_partial(seeded, client: Client) -> None:
    response = client.get("/uz/qidiruv/", {"q": "skrining"}, HTTP_HX_REQUEST="true")
    html = response.content.decode()
    assert "<html" not in html
    assert "search-results__count" in html
    assert "HX-Request" in response["Vary"]


def test_post_not_allowed(seeded, client: Client) -> None:
    assert client.post("/uz/qidiruv/", {"q": "x"}).status_code == 405


def test_rebuild_search_command(seeded, capsys) -> None:
    call_command("rebuild_search", verbosity=0)
    assert "rebuild_search: index rebuilt" in capsys.readouterr().out
    assert search_pages("skrining", "uz")
