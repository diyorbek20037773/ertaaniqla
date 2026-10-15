"""Sections switched off for visitors (D-087). «Bolalar saratoni» stays hidden until its content is
ready: Settings → Site settings → «Show the childhood cancer section».

While a section is off:
* the section and every page under it answer 404 (editors still preview them in the CMS);
* the header menu, section tabs, footer site map, landing cards, topic pills, search and the
  sitemap leave it out;
* news, articles, videos, questions, stories, terms and self-checks of that section are not
  listed.

The pages and their data stay untouched, so ticking the box brings everything back at once.
"""

from __future__ import annotations

from typing import Any

from django.core.cache import cache

HIDDEN_CACHE_KEY = "sections:hidden"
HIDDEN_CACHE_SECONDS = 60 * 60

# disease topic → the section it belongs to
TOPIC_SECTION = {"breast": "women", "cervical": "women", "children": "children"}


def _load() -> tuple[list[str], list[str]]:
    from wagtail.models import Site

    from apps.core.models import SectionKey, SiteSettings
    from apps.sections.models import SectionIndexPage

    site = Site.objects.filter(is_default_site=True).first()
    show_children = bool(site and SiteSettings.for_site(site).show_children_section)
    hidden = [] if show_children else [SectionKey.CHILDREN.value]
    paths = list(
        SectionIndexPage.objects.filter(section_key__in=hidden).values_list("path", flat=True)
    )
    return hidden, paths


def _cached() -> tuple[list[str], list[str]]:
    value: tuple[list[str], list[str]] | None = cache.get(HIDDEN_CACHE_KEY)
    if value is None:
        value = _load()
        cache.set(HIDDEN_CACHE_KEY, value, HIDDEN_CACHE_SECONDS)
    return value


def invalidate() -> None:
    cache.delete(HIDDEN_CACHE_KEY)


def hidden_sections() -> frozenset[str]:
    return frozenset(_cached()[0])


def hidden_topics() -> frozenset[str]:
    hidden = hidden_sections()
    return frozenset(topic for topic, section in TOPIC_SECTION.items() if section in hidden)


def visible_topics() -> list[tuple[str, str]]:
    """`Topic.choices` without the topics of hidden sections (filter pills, landing cards)."""
    from apps.core.models import Topic

    hidden = hidden_topics()
    return [(value, label) for value, label in Topic.choices if value not in hidden]


def visible_section_choices(choices: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Section filter options (directory, glossary, stories, materials) without hidden ones."""
    hidden = hidden_sections()
    return [(value, label) for value, label in choices if value not in hidden]


def path_is_hidden(path: str) -> bool:
    """True for a page inside a hidden section (cheap: tree path only, no query)."""
    return any(path.startswith(prefix) for prefix in _cached()[1])


def page_is_hidden(page: Any) -> bool:
    """A page inside a hidden section, or one that names a hidden section or topic itself
    (self-check for parents, patient story, news item)."""
    if not hidden_sections():
        return False
    if path_is_hidden(str(page.path)):
        return True
    from apps.core.models import BasePage

    specific = page.specific
    own_key = getattr(type(specific), "section_key", None)
    declared = own_key is not None and own_key is not BasePage.section_key  # not inherited
    if declared and str(getattr(specific, "section_key", "") or "") in hidden_sections():
        return True
    return str(getattr(specific, "topic", "") or "") in hidden_topics()


def exclude_hidden_pages(pages: Any) -> Any:
    """A page queryset without the pages under hidden sections (sitemap, search)."""
    from django.db.models import Q

    paths = _cached()[1]
    if not paths:
        return pages
    query = Q()
    for prefix in paths:
        query |= Q(path__startswith=prefix)
    return pages.exclude(query)
