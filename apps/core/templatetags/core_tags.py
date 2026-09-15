"""Template tags shared by every page: navigation, breadcrumbs, language links, hreflang,
phone formatting. Every tag degrades gracefully when `page` is missing (404/500, app views)."""

from __future__ import annotations

import re
from typing import Any

from django import template
from django.conf import settings
from django.utils import translation
from django.utils.html import format_html, format_html_join
from django.utils.safestring import SafeString
from wagtail.models import Locale, Page, Site

from apps.core.navigation import get_navigation

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
        "LANGUAGE_CODE": lang,
        "request": context.get("request"),
        "page": context.get("page"),
        "section_key": context.get("section_key", ""),
    }


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
    page = context.get("page")
    current = _current_language()
    links = [
        {
            "code": code,
            "name": name,
            "url": translated_url(page, code),
            "is_current": code == current,
        }
        for code, name in settings.LANGUAGES
    ]
    return {"links": links}


@register.simple_tag(takes_context=True)
def hreflang_links(context: dict[str, Any]) -> SafeString:
    """`<link rel="alternate" hreflang>` for every language + x-default (spec §7)."""
    page = context.get("page")
    request = context.get("request")
    base = site_root_url(request)
    pairs = [(code, base + translated_url(page, code)) for code, _ in settings.LANGUAGES]
    default_url = dict(pairs)[settings.LANGUAGE_CODE]
    links = format_html_join(
        "\n", '<link rel="alternate" hreflang="{}" href="{}">', ((code, url) for code, url in pairs)
    )
    return format_html(
        '{}\n<link rel="alternate" hreflang="x-default" href="{}">', links, default_url
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
def localized(obj: Any, field: str) -> str:
    """`{{ settings.core.SiteSettings|localized:"disclaimer" }}` → `<field>_<lang>`, uz fallback."""
    if obj is None:
        return ""
    lang = _current_language()
    return str(getattr(obj, f"{field}_{lang}", "") or getattr(obj, f"{field}_uz", "") or "")
