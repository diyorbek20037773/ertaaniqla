"""Glossary page (F14) and inline term tooltips."""

from __future__ import annotations

import pytest
from django.test import Client
from django.utils import translation
from wagtail.models import Locale

from apps.glossary.models import GlossaryPage, Term
from apps.glossary.templatetags.glossary_tags import get_terms, glossary_wrap, wrap_terms

pytestmark = pytest.mark.django_db


def test_page_lists_groups_and_filters(seeded, client: Client) -> None:
    html = client.get("/uz/lugat/").content.decode()
    assert 'id="term-' in html and "glossary-letters" in html
    assert "Biopsiya" in html
    filtered = client.get("/uz/lugat/?q=remis").content.decode()
    assert "Remissiya" in filtered and "Biopsiya" not in filtered
    assert client.get("/ru/slovar/").status_code == 200
    page = GlossaryPage.objects.get(locale__language_code="uz")
    assert len(page.get_terms(section="women")) == 3  # 'both' terms count for every section


def test_wrap_first_occurrence_only_and_skip_links(seeded) -> None:
    with translation.override("uz"):
        refs = get_terms("uz")
        assert refs
        html = "<p>Biopsiya kerak. <a href='/x'>Biopsiya</a> yana biopsiya.</p><h2>Biopsiya</h2>"
        out = wrap_terms(html, refs)
    assert out.count('class="term"') == 1
    assert 'href="/uz/lugat/#term-' in out
    assert "<a href='/x'>Biopsiya</a>" in out  # untouched inside a link
    assert "<h2>Biopsiya</h2>" in out


def test_synonyms_and_word_boundaries(seeded) -> None:
    with translation.override("uz"):
        refs = get_terms("uz")
        out = wrap_terms("<p>биопсия va biopsiyaga</p>", refs)
    assert out.count('class="term"') == 1  # synonym matched; 'biopsiyaga' (suffix) not matched
    assert glossary_wrap("") == ""


def test_cache_invalidated_on_term_change(seeded) -> None:
    with translation.override("uz"):
        before = len(get_terms("uz"))
        Term.objects.create(
            locale=Locale.objects.get(language_code="uz"),
            term="Kimyoterapiya",
            definition="<p>x</p>",
        )
        assert len(get_terms("uz")) == before + 1


def test_rich_text_block_wraps_terms(seeded, client: Client) -> None:
    # seeded diagnostics page mentions "biopsiya" in its callout, not rich_text; add a check on
    # the filter through the template path instead
    from django.template import Context, Template

    with translation.override("ru"):
        html = Template("{% load glossary_tags %}{{ text|glossary_wrap }}").render(
            Context({"text": "<p>Нужна биопсия.</p>"})
        )
    assert 'class="term"' in html and "/ru/slovar/#term-" in html
