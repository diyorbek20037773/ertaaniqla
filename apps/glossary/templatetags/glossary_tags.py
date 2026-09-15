"""`{{ html|glossary_wrap }}` — wraps the first occurrence of every glossary term of the
current language in a link to its definition (`<a class="term" title="…" href="…#term-id">`),
skipping text that is already inside a link/heading/abbr. Terms are cached per language and
invalidated on Term save/delete (apps.glossary.signals)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from django import template
from django.core.cache import cache
from django.utils import translation
from django.utils.html import escape, strip_tags
from django.utils.safestring import SafeString, mark_safe

register = template.Library()

CACHE_SECONDS = 60 * 60
_TAG_RE = re.compile(r"(<[^>]+>)")
_SKIP_TAGS = {"a", "abbr", "h1", "h2", "h3", "h4", "button", "script", "style"}


@dataclass(frozen=True)
class TermRef:
    id: int
    term: str
    definition: str
    url: str
    pattern: re.Pattern[str]


def cache_key(language: str) -> str:
    return f"glossary:{language}"


def invalidate_glossary_cache() -> None:
    from django.conf import settings

    cache.delete_many([cache_key(code) for code, _ in settings.LANGUAGES])


def _load_terms(language: str) -> list[TermRef]:
    from wagtail.models import Locale

    from apps.glossary.models import GlossaryPage, Term

    try:
        locale = Locale.objects.get(language_code=language)
    except Locale.DoesNotExist:
        return []
    page = GlossaryPage.objects.live().filter(locale=locale).first()
    base_url = str(page.url) if page is not None else ""
    refs: list[TermRef] = []
    for term in Term.objects.filter(locale=locale).order_by("-term"):  # longest-first-ish
        words = [term.term, *term.synonym_list]
        alternatives = sorted({w.strip() for w in words if w.strip()}, key=len, reverse=True)
        if not alternatives:
            continue
        pattern = re.compile(
            r"(?<![\wʻʼ])(" + "|".join(re.escape(a) for a in alternatives) + r")(?![\wʻʼ])",
            re.IGNORECASE,
        )
        refs.append(
            TermRef(
                id=term.pk,
                term=term.term,
                definition=" ".join(strip_tags(str(term.definition)).split())[:300],
                url=f"{base_url}#term-{term.pk}" if base_url else "",
                pattern=pattern,
            )
        )
    refs.sort(key=lambda ref: len(ref.term), reverse=True)
    return refs


def get_terms(language: str) -> list[TermRef]:
    key = cache_key(language)
    cached = cache.get(key)
    if cached is not None:
        return list(cached)
    refs = _load_terms(language)
    cache.set(key, refs, CACHE_SECONDS)
    return refs


def wrap_terms(html: str, refs: list[TermRef]) -> str:
    if not refs or not html:
        return html
    pending = list(refs)
    parts = _TAG_RE.split(html)
    skip_depth = 0
    for index, part in enumerate(parts):
        if not part:
            continue
        if part.startswith("<"):
            name_match = re.match(r"</?\s*([a-zA-Z0-9]+)", part)
            name = name_match.group(1).lower() if name_match else ""
            if name in _SKIP_TAGS and not part.endswith("/>"):
                skip_depth += -1 if part.startswith("</") else 1
                skip_depth = max(skip_depth, 0)
            continue
        if skip_depth or not pending:
            continue
        text = part
        for ref in list(pending):
            match = ref.pattern.search(text)
            if match is None:
                continue
            title = escape(ref.definition)
            found = escape(match.group(1))
            if ref.url:
                replacement = f'<a class="term" href="{ref.url}" title="{title}">{found}</a>'
            else:
                replacement = f'<abbr class="term" title="{title}">{found}</abbr>'
            text = text[: match.start()] + replacement + text[match.end() :]
            pending.remove(ref)
        parts[index] = text
    return "".join(parts)


@register.filter(name="glossary_wrap", is_safe=True)
def glossary_wrap(value: Any) -> SafeString:
    html = str(value)
    language = translation.get_language() or "uz"
    return mark_safe(wrap_terms(html, get_terms(language)))  # noqa: S308 - input is CMS rich text
