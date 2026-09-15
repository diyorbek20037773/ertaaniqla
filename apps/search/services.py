"""Site search (spec A4, §7): Postgres FTS (`ertaaniqla` config = simple + unaccent) over live
pages of both locales, with uz/ru synonym expansion and Latin↔Cyrillic transliteration.
Results of the visitor's language come first. Nothing is stored.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from django.utils.html import strip_tags
from wagtail.models import Page
from wagtail.search.query import Or, PlainText, SearchQuery

from apps.search.synonyms import SYNONYM_GROUPS
from apps.search.translit import normalise_apostrophes, script_variants

MAX_QUERY_LENGTH = 100
MAX_RESULTS = 30
MIN_QUERY_LENGTH = 2

_WORD = re.compile(r"[\wʻʼ-]+", re.UNICODE)


def normalise(text: str) -> str:
    return normalise_apostrophes(text.strip().lower())


_SYNONYM_INDEX: dict[str, list[str]] = {}
for _group in SYNONYM_GROUPS:
    _normalised = [normalise(item) for item in _group]
    for _item in _normalised:
        _SYNONYM_INDEX.setdefault(_item, []).extend(x for x in _normalised if x != _item)


def clean_query(raw: str) -> str:
    """Trim, cap length, drop control characters. Empty string = no search."""
    text = re.sub(r"[\x00-\x1f\x7f]", " ", raw or "")
    text = re.sub(r"\s+", " ", text).strip()[:MAX_QUERY_LENGTH]
    return text if len(text) >= MIN_QUERY_LENGTH else ""


def expand_query(query: str) -> list[str]:
    """Query variants: original, transliterations, synonyms of each word / whole phrase."""
    variants: list[str] = []
    for variant in script_variants(query):
        variants.append(variant)
    phrase = normalise(query)
    if phrase in _SYNONYM_INDEX:
        variants.extend(_SYNONYM_INDEX[phrase])
    for word in _WORD.findall(phrase):
        variants.extend(_SYNONYM_INDEX.get(word, []))
    seen: set[str] = set()
    result: list[str] = []
    for item in variants:
        key = item.lower()
        if item and key not in seen:
            seen.add(key)
            result.append(item)
    return result[:12]


def build_query(query: str) -> SearchQuery:
    variants = expand_query(query)
    if len(variants) == 1:
        return PlainText(variants[0])
    return Or([PlainText(variant) for variant in variants])


@dataclass
class SearchResult:
    page: Any
    title: str
    url: str
    summary: str
    language_code: str
    section_key: str

    @classmethod
    def from_page(cls, page: Any) -> SearchResult:
        specific = page.specific
        summary = getattr(specific, "summary", "") or getattr(specific, "tagline", "")
        if not summary:
            summary = (
                strip_tags(specific.get_body_text())[:200]
                if hasattr(specific, "get_body_text")
                else ""
            )
        return cls(
            page=specific,
            title=str(specific.title),
            url=str(specific.url or ""),
            summary=str(summary)[:300],
            language_code=str(specific.locale.language_code),
            section_key=str(getattr(specific, "section_key", "") or ""),
        )


def search_pages(query: str, language_code: str, limit: int = MAX_RESULTS) -> list[SearchResult]:
    """Full-text search + autocomplete (prefix) merged, current language first."""
    query = clean_query(query)
    if not query:
        return []
    base = Page.objects.live().public().filter(depth__gt=1)
    ordered: list[Any] = []
    seen_ids: set[int] = set()
    for hit in base.search(build_query(query))[: limit * 2]:
        if hit.pk not in seen_ids:
            seen_ids.add(hit.pk)
            ordered.append(hit)
    if len(ordered) < limit:
        for hit in base.autocomplete(normalise_apostrophes(query))[:limit]:
            if hit.pk not in seen_ids:
                seen_ids.add(hit.pk)
                ordered.append(hit)
    # stable sort: visitor's language first, search rank otherwise preserved
    ordered.sort(key=lambda page: 0 if page.locale.language_code == language_code else 1)
    return [SearchResult.from_page(page) for page in ordered[:limit]]
