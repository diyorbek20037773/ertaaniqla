"""Glossary `Term` snippet (translatable)."""

from __future__ import annotations

import pytest
from wagtail.models import Locale

from apps.glossary.models import Term

pytestmark = pytest.mark.django_db


def test_term_translation_and_synonyms(seeded) -> None:
    term = Term.objects.get(term="Biopsiya", locale__language_code="uz")
    ru = term.get_translation(Locale.objects.get(language_code="ru"))
    assert ru.term == "Биопсия"
    assert term.synonym_list == ["biopsiya", "биопсия"]
    assert str(term) == "Biopsiya"
    assert "[[TODO" in term.definition


def test_glossary_block_renders_definitions_as_rich_text(seeded, client) -> None:
    """EA-12: the inline glossary block showed `<p>…</p>` as literal text."""
    for url in (
        "/uz/bolalar/diagnostika-va-davolash/diagnostika/",
        "/ru/detskiy/diagnostika-i-lechenie/diagnostika/",
    ):
        html = client.get(url).content.decode()
        assert "glossary-terms__definition" in html
        assert "&lt;p&gt;" not in html, url
