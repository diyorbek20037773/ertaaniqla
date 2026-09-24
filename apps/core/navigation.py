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
    key: str = ""  # only site links carry one (SITE_LINK_TYPES), so templates can pick one out


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


SITE_LINK_TYPES: tuple[tuple[str, str], ...] = (
    ("tools", "tools.ToolsIndexPage"),
    ("stories", "stories.StoryIndexPage"),
    ("faq", "faq.FAQPage"),
    ("glossary", "glossary.GlossaryPage"),
    ("materials", "media_library.MaterialsPage"),
    ("feedback", "feedback.FeedbackPage"),
)


def site_links_cache_key(language_code: str) -> str:
    return f"sitelinks:{language_code}"


def build_site_links(language_code: str) -> list[NavItem]:
    """Root-level utility pages (tools, stories, FAQ, glossary, feedback) for the footer."""
    from django.apps import apps as django_apps
    from wagtail.models import Locale

    try:
        locale = Locale.objects.get(language_code=language_code)
    except Locale.DoesNotExist:
        return []
    links: list[NavItem] = []
    for key, label in SITE_LINK_TYPES:
        model = django_apps.get_model(label)
        page = model.objects.live().filter(locale=locale).first()
        if page is not None:
            links.append(NavItem(title=str(page.title), url=str(page.url or ""), key=key))
    return links


def get_site_links(language_code: str) -> list[NavItem]:
    key = site_links_cache_key(language_code)
    cached = cache.get(key)
    if cached is not None:
        return list(cached)
    links = build_site_links(language_code)
    cache.set(key, links, NAV_CACHE_SECONDS)
    return links


def header_links_cache_key(language_code: str) -> str:
    return f"headerlinks:{language_code}"


HEADER_LINK_KEYS = ("home", "about", "doctors", "faq")


def build_header_links(language_code: str) -> dict[str, str]:
    """URLs of the Figma header items around «Bo'limlar» (D-064): home, about, doctors, FAQ.

    About / doctors are chosen in Site settings (uz page); the translation in the requested
    language is used, and an item without a live page is simply left out.
    """
    from wagtail.models import Locale, Site

    from apps.core.models import SiteSettings

    try:
        locale = Locale.objects.get(language_code=language_code)
    except Locale.DoesNotExist:
        return {}
    site = Site.objects.filter(is_default_site=True).select_related("root_page").first()
    if site is None:
        return {}
    urls: dict[str, str] = {}
    candidates: dict[str, Any] = {"home": site.root_page}
    site_settings = SiteSettings.for_site(site)
    candidates["about"] = site_settings.about_page
    candidates["doctors"] = site_settings.doctors_page
    for key, page in candidates.items():
        localized = page.get_translation_or_none(locale) if page is not None else None
        if localized is not None and localized.live and localized.url:
            urls[key] = str(localized.url)
    faq = next((link for link in build_site_links(language_code) if link.key == "faq"), None)
    if faq is not None and faq.url:
        urls["faq"] = faq.url
    return urls


def get_header_links(language_code: str) -> dict[str, str]:
    key = header_links_cache_key(language_code)
    cached = cache.get(key)
    if cached is not None:
        return dict(cached)
    links = build_header_links(language_code)
    cache.set(key, links, NAV_CACHE_SECONDS)
    return links


def invalidate_navigation() -> None:
    keys = [nav_cache_key(code) for code, _ in settings.LANGUAGES]
    keys += [site_links_cache_key(code) for code, _ in settings.LANGUAGES]
    keys += [header_links_cache_key(code) for code, _ in settings.LANGUAGES]
    cache.delete_many(keys)
