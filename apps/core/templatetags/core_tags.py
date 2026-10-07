"""Template tags shared by every page: navigation, breadcrumbs, language links, hreflang,
phone formatting. Every tag degrades gracefully when `page` is missing (404/500, app views)."""

from __future__ import annotations

import re
from dataclasses import replace
from typing import Any
from urllib.parse import urlencode

from django import template
from django.conf import settings
from django.urls import translate_url
from django.utils import translation
from django.utils.html import format_html, format_html_join
from django.utils.safestring import SafeString
from wagtail.models import Locale, Page, Site

from apps.core.navigation import get_header_links, get_navigation, get_site_links

register = template.Library()

_DIGITS = re.compile(r"\D+")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _current_language() -> str:
    return translation.get_language() or settings.LANGUAGE_CODE


def _locale_or_none(code: str) -> Locale | None:
    try:
        return Locale.objects.get(language_code=code)
    except Locale.DoesNotExist:
        return None


def site_root_url(request: Any) -> str:
    """Canonical origin: the Wagtail Site hostname (ertaaniqla.uz in prod, not an alias)."""
    if request is not None:
        site = Site.find_for_request(request)
        if site is not None:
            return str(site.root_url)
    return str(settings.SITE_BASE_URL).rstrip("/")


def translated_url(page: Page | None, code: str) -> str:
    """URL of `page` in language `code`: translated page → its section → language root."""
    fallback = f"/{code}/"
    if page is None or not getattr(page, "pk", None):
        return fallback
    locale = _locale_or_none(code)
    if locale is None:
        return fallback
    translation_page = page.get_translation_or_none(locale)
    if translation_page is not None and translation_page.live:
        return str(translation_page.url or fallback)
    section = page.specific.get_section() if hasattr(page.specific, "get_section") else None
    if section is not None:
        section_translation = section.get_translation_or_none(locale)
        if section_translation is not None and section_translation.live:
            return str(section_translation.url or fallback)
    return fallback


# ---------------------------------------------------------------------------
# tags
# ---------------------------------------------------------------------------
@register.inclusion_tag("components/nav.html", takes_context=True)
def main_nav(context: dict[str, Any]) -> dict[str, Any]:
    lang = _current_language()
    return {
        "sections": get_navigation(lang),
        "links": get_header_links(lang),
        "LANGUAGE_CODE": lang,
        "request": context.get("request"),
        "page": context.get("page"),
        "section_key": context.get("section_key", ""),
    }


@register.inclusion_tag("components/section_tabs.html", takes_context=True)
def section_tabs(context: dict[str, Any]) -> dict[str, Any]:
    """Pill tab bar with the active section's menu items (design: Figma 2408:816).

    Renders nothing outside a section. The active tab is the menu item whose URL is a
    prefix of the current path, so children of a topic keep their parent highlighted.
    """
    lang = _current_language()
    section_key = context.get("section_key", "")
    request = context.get("request")
    path = getattr(request, "path", "") or ""
    section = next((s for s in get_navigation(lang) if s.key == section_key), None)
    items = [] if section is None else _same_variant_items(context.get("page"), section.items)
    active_url = ""
    for item in items:
        url = item.url or ""
        if url and path.startswith(url) and len(url) > len(active_url):
            active_url = url
    return {"items": items, "active_url": active_url, "section_key": section_key}


def _same_variant_items(page: Any, items: list[Any]) -> list[Any]:
    """On a variant page (…/skrining/bachadon-boyni-saratoni/) every tab opens the same variant
    under its own topic, so reading about cervical cancer never jumps to breast cancer (EA-09).
    A tab keeps the topic URL (→ first variant) when that topic has no such child."""
    if page is None or not getattr(page, "pk", None):
        return items
    parent = page.get_parent().specific
    if not getattr(parent, "is_variant_group", False):
        return items
    siblings = {
        str(p.url)
        for p in Page.objects.live()
        .filter(slug=page.slug, depth=page.depth, locale_id=page.locale_id)
        .defer_streamfields()
    }
    result = []
    for item in items:
        candidate = f"{item.url}{page.slug}/" if item.url else ""
        result.append(replace(item, url=candidate) if candidate in siblings else item)
    return result


@register.inclusion_tag("components/variant_switch.html", takes_context=True)
def variant_switch(context: dict[str, Any]) -> dict[str, Any]:
    """Breast / cervical pill pair (Figma 2408:234) between the sibling pages of a variant group.

    Renders nothing unless the page's parent is a TopicIndexPage with `is_variant_group`.
    """
    page = context.get("page")
    if page is None or not getattr(page, "pk", None):
        return {"items": [], "group_title": ""}
    parent = page.get_parent().specific
    variants = parent.get_variants() if hasattr(parent, "get_variants") else []
    items = [
        {"title": variant.title, "url": variant.url, "active": variant.pk == page.pk}
        for variant in variants
    ]
    return {"items": items if len(items) > 1 else [], "group_title": getattr(parent, "title", "")}


@register.inclusion_tag("components/share.html", takes_context=True)
def share_bar(context: dict[str, Any]) -> dict[str, Any]:
    """Share links (spec §10): Telegram first, then WhatsApp, Facebook; copy link + story image."""
    from urllib.parse import quote

    page = context.get("page")
    request = context.get("request")
    base = site_root_url(request)
    url = f"{base}{page.url}" if page is not None and getattr(page, "pk", None) else base
    title = str(getattr(page, "title", "") or "Erta aniqla")
    encoded_url, encoded_title = quote(url, safe=""), quote(title, safe="")
    links = [
        {
            "key": "telegram",
            "label": "Telegram",
            "href": f"https://t.me/share/url?url={encoded_url}&text={encoded_title}",
        },
        {
            "key": "whatsapp",
            "label": "WhatsApp",
            "href": f"https://wa.me/?text={encoded_title}%20{encoded_url}",
        },
        {
            "key": "facebook",
            "label": "Facebook",
            "href": f"https://www.facebook.com/sharer/sharer.php?u={encoded_url}",
        },
    ]
    story = getattr(page, "story_image_generated_url", "")
    return {
        "links": links,
        "url": url,
        "title": title,
        "story_url": f"{base}{story}" if story else "",
    }


@register.simple_tag(takes_context=True)
def jsonld(context: dict[str, Any]) -> SafeString:
    """`<script type="application/ld+json">` with the page's graph (empty for non-page views)."""
    from apps.core import seo

    items = context.get("jsonld")
    if not items:
        request = context.get("request")
        base = site_root_url(request)
        items = [seo.organization_ld(base, _current_language())]
    return seo.jsonld_script(seo.graph(list(items)))


@register.simple_tag
def site_verification() -> SafeString:
    from apps.core import seo

    return seo.site_verification_tags()


@register.simple_tag
def header_links() -> dict[str, str]:
    """Header item URLs (home, about, doctors, faq) of the current language (cached)."""
    return get_header_links(_current_language())


@register.simple_tag
def site_links() -> list[Any]:
    """Footer links to the root-level utility pages of the current language (cached)."""
    return get_site_links(_current_language())


@register.inclusion_tag("components/breadcrumbs.html", takes_context=True)
def breadcrumbs(context: dict[str, Any]) -> dict[str, Any]:
    page = context.get("page")
    crumbs: list[Page] = []
    if page is not None and getattr(page, "pk", None):
        # depth 1 = tree root, depth 2 = site root (home) — start from the home page
        crumbs = list(page.get_ancestors(inclusive=True).live().filter(depth__gte=2).specific())
    return {"crumbs": crumbs, "page": page}


@register.inclusion_tag("components/lang_switch.html", takes_context=True)
def lang_switch(context: dict[str, Any]) -> dict[str, Any]:
    return {"links": language_versions(context)}


# Filters and the search query survive a language switch (EA-16); nothing else is copied.
KEPT_QUERY_KEYS = ("q", "region", "kind", "section", "audience", "free", "letter")


def _kept_query(request: Any) -> str:
    params = getattr(request, "GET", None)
    if not params:
        return ""
    kept = [(k, v) for k in KEPT_QUERY_KEYS for v in params.getlist(k) if v]
    return "?" + urlencode(kept) if kept else ""


def language_versions(context: dict[str, Any]) -> list[dict[str, Any]]:
    """Site versions for the switcher and hreflang: uz (Latin), uz-Cyrl (`/oz/`, D-049), ru.

    `keep` marks Latin URLs that the Cyrillic middleware must not rewrite to `/oz/`.
    """
    from apps.core.middleware import (
        CYRILLIC_LANGUAGE_TAG,
        is_cyrillic_request,
        latin_to_cyrillic_path,
    )

    page = context.get("page")
    request = context.get("request")
    current = CYRILLIC_LANGUAGE_TAG if is_cyrillic_request(request) else _current_language()
    query = _kept_query(request)
    versions: list[dict[str, Any]] = []
    for code, name in settings.LANGUAGES:
        if page is None and request is not None and getattr(request, "resolver_match", None):
            url = translate_url(request.path, code)  # app views: /uz/qidiruv/ ↔ /ru/poisk/
        else:
            url = translated_url(page, code)
        url += query
        versions.append(
            {
                "code": code,
                "name": name,
                "url": url,
                "keep": code == "uz",
                "is_current": code == current,
            }
        )
        if code == "uz" and getattr(settings, "UZ_CYRILLIC_ENABLED", True):
            versions.append(
                {
                    "code": CYRILLIC_LANGUAGE_TAG,
                    "name": "Ўзбекча",
                    "url": latin_to_cyrillic_path(url),
                    "keep": False,
                    "is_current": current == CYRILLIC_LANGUAGE_TAG,
                }
            )
    return versions


@register.simple_tag(takes_context=True)
def hreflang_links(context: dict[str, Any]) -> SafeString:
    """`<link rel="alternate" hreflang>` for every site version + x-default (spec §7)."""
    base = site_root_url(context.get("request"))
    versions = language_versions(context)
    default_url = next(base + v["url"] for v in versions if v["code"] == settings.LANGUAGE_CODE)
    links = format_html_join(
        "\n",
        '<link rel="alternate" hreflang="{}" href="{}"{}>',
        (
            (v["code"], base + v["url"], SafeString(" data-script-keep" if v["keep"] else ""))
            for v in versions
        ),
    )
    return format_html(
        '{}\n<link rel="alternate" hreflang="x-default" href="{}" data-script-keep>',
        links,
        default_url,
    )


@register.simple_tag(takes_context=True, name="site_root_url")
def site_root_url_tag(context: dict[str, Any]) -> str:
    return site_root_url(context.get("request"))


@register.simple_tag(takes_context=True)
def canonical_url(context: dict[str, Any]) -> str:
    page = context.get("page")
    request = context.get("request")
    base = site_root_url(request)
    if page is not None and getattr(page, "pk", None):
        return f"{base}{page.url}"
    if request is not None:
        return f"{base}{request.path}"
    return base


@register.simple_tag
def section_style(section: Any) -> SafeString:
    """Inline `<style>` (nonce'd in the template) overriding --brand from CMS colours."""
    if section is None:
        return SafeString("")
    rules = []
    if getattr(section, "colour_primary", ""):
        rules.append(f"--brand:{section.colour_primary};")
    if getattr(section, "colour_accent", ""):
        rules.append(f"--brand-soft:{section.colour_accent};")
    if not rules:
        return SafeString("")
    return format_html("body{{{}}}", "".join(rules))


# ---------------------------------------------------------------------------
# filters
# ---------------------------------------------------------------------------
@register.filter
def phone_display(value: str) -> str:
    """`+998901234567` → `+998 90 123-45-67` (spec §7). Non-UZ numbers are returned as is."""
    digits = _DIGITS.sub("", value or "")
    if len(digits) == 12 and digits.startswith("998"):
        return f"+998 {digits[3:5]} {digits[5:8]}-{digits[8:10]}-{digits[10:12]}"
    if len(digits) == 9:
        return f"+998 {digits[0:2]} {digits[2:5]}-{digits[5:7]}-{digits[7:9]}"
    return value or ""


@register.filter
def phone_href(value: str) -> str:
    digits = _DIGITS.sub("", value or "")
    if len(digits) == 9:
        digits = "998" + digits
    return f"tel:+{digits}" if digits else ""


@register.filter
def localized_value(obj: Any, field: str) -> Any:
    """Like `localized` but returns the raw value (StreamField, FK) — footer columns."""
    if obj is None:
        return None
    lang = _current_language()
    value = getattr(obj, f"{field}_{lang}", None)
    return value if value else getattr(obj, f"{field}_uz", None)


@register.simple_tag(takes_context=True)
def footer_map(context: dict[str, Any], site_settings: Any) -> list[dict[str, Any]]:
    """Footer site map of the current language with every link resolved in ~3 queries: the
    chosen pages' translations are fetched in one go (`.localized` per link cost 2 queries
    each, ~70 per page view)."""
    columns = localized_value(site_settings, "footer_columns") or []
    pages = [link.get("page") for col in columns for link in col.value["links"]]
    keys = {page.translation_key for page in pages if page is not None}
    lang = _current_language()
    translated = {
        page.translation_key: page
        for page in Page.objects.live()
        .filter(translation_key__in=keys, locale__language_code=lang)
        .defer_streamfields()
    }
    request = context.get("request")
    result = []
    for col in columns:
        links = []
        for link in col.value["links"]:
            page = link.get("page")
            if page is not None:
                target = translated.get(page.translation_key, page)
                href = str(target.get_url(request) or "")
            else:
                href = str(link.get("url") or "")
            if link.get("anchor") and href:
                href = f"{href}#{link['anchor']}"
            if href:
                links.append({"label": link["label"], "href": href})
        result.append({"title": col.value["title"], "links": links})
    return result


@register.simple_tag
def cache_version() -> str:
    """Bumped on every publish / settings save and on every deploy (apps.core.cache) — fragment
    cache keys."""
    from apps.core.cache import build_id, page_cache_version

    return f"{build_id()}-{page_cache_version()}"


@register.filter
def link_href(link: Any) -> str:
    """URL of a FooterLinkBlock value: the page's translation in the current language (+anchor),
    else the external URL."""
    page = link.get("page")
    href = str(page.localized.url or "") if page is not None else str(link.get("url") or "")
    anchor = link.get("anchor")
    return f"{href}#{anchor}" if anchor and href else href


@register.filter
def localized(obj: Any, field: str) -> str:
    """`{{ settings.core.SiteSettings|localized:"disclaimer" }}` → `<field>_<lang>`, uz fallback."""
    if obj is None:
        return ""
    lang = _current_language()
    return str(getattr(obj, f"{field}_{lang}", "") or getattr(obj, f"{field}_uz", "") or "")
