"""Per-language sitemaps (spec §7, §10): `/uz/sitemap.xml` lists only uz pages, `/ru/…` only
ru pages; `noindex` pages and tool pages behind a disabled flag are excluded."""

from __future__ import annotations

from typing import Any

from django.utils import translation
from wagtail.contrib.sitemaps import Sitemap
from wagtail.models import Locale


class LocaleSitemap(Sitemap):
    def items(self) -> Any:
        language = translation.get_language() or "uz"
        try:
            locale = Locale.objects.get(language_code=language)
        except Locale.DoesNotExist:
            return []
        pages = (
            self.get_wagtail_site()
            .root_page.localized.get_descendants(inclusive=True)
            .live()
            .public()
            .filter(locale=locale)
            .order_by("path")
        )
        excluded: list[int] = []
        for page in pages.specific():
            flag_enabled = getattr(page, "flag_enabled", None)
            if getattr(page, "noindex", False) or (
                callable(flag_enabled) and not flag_enabled(self.request)
            ):
                excluded.append(page.pk)
        # Wagtail's Sitemap iterates a queryset (.iterator()), so return one
        return pages.exclude(pk__in=excluded).specific()
