"""Mega-menu data (spec §2.1, §4.5): built from the page tree, cached per locale for an hour,
invalidated by page publish/unpublish/move/delete signals (see `apps.core.signals`)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from django.conf import settings
from django.core.cache import cache

NAV_CACHE_SECONDS = 60 * 60


@dataclass
class NavItem:
    title: str
    url: str
    summary: str = ""
    children: list[NavItem] = field(default_factory=list)


@dataclass
class NavSection:
    key: str
    title: str
    url: str
    tagline: str
    emoji: str
    items: list[NavItem]


def nav_cache_key(language_code: str) -> str:
    return f"nav:{language_code}"


def _item(page: Any, with_children: bool) -> NavItem:
    children: list[NavItem] = []
    if with_children:
        children = [
            _item(child, with_children=False)
            for child in page.get_children().live().in_menu().specific()
        ]
    return NavItem(
        title=str(page.title),
        url=str(page.url or ""),
        summary=str(getattr(page, "summary", "") or getattr(page, "tagline", "") or ""),
        children=children,
    )


def build_navigation(language_code: str) -> list[NavSection]:
    """Both sections with their 5 top-level menu items and one level of sub-items."""
    from wagtail.models import Locale

    from apps.sections.models import SectionIndexPage

    try:
        locale = Locale.objects.get(language_code=language_code)
    except Locale.DoesNotExist:
        return []
    sections: list[NavSection] = []
    for section in SectionIndexPage.objects.live().filter(locale=locale).order_by("path"):
        sections.append(
            NavSection(
                key=section.section_key,
                title=str(section.title),
                url=str(section.url or ""),
                tagline=section.tagline,
                emoji=section.emoji,
                items=[_item(page, with_children=True) for page in section.get_menu_items()],
            )
        )
    return sections


def get_navigation(language_code: str) -> list[NavSection]:
    key = nav_cache_key(language_code)
    cached = cache.get(key)
    if cached is not None:
        return list(cached)
    nav = build_navigation(language_code)
    cache.set(key, nav, NAV_CACHE_SECONDS)
    return nav


def invalidate_navigation() -> None:
    cache.delete_many([nav_cache_key(code) for code, _ in settings.LANGUAGES])
