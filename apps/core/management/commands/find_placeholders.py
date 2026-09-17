"""Launch gate: list live pages and site settings that still contain seed placeholders
(`[[TODO: …]]`, `[[VERIFY: …]]`). Exit code 1 when anything is found (`--fail`)."""

from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from wagtail.models import Page

PLACEHOLDER_RE = re.compile(r"\[\[(TODO|VERIFY)\b")


def count_placeholders(data: Any) -> Counter[str]:
    return Counter(PLACEHOLDER_RE.findall(json.dumps(data, default=str, ensure_ascii=False)))


class Command(BaseCommand):
    help = "List live pages / site settings that still contain [[TODO]] or [[VERIFY]] placeholders."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--fail", action="store_true", help="exit 1 if anything is found")

    def handle(self, *args: Any, **options: Any) -> None:
        from apps.core.models import SiteSettings

        found = 0
        for page in Page.objects.live().filter(depth__gte=2).specific().order_by("path"):
            counts = count_placeholders(page.serializable_data())
            if counts:
                found += 1
                self.stdout.write(
                    f"{page.locale.language_code}  {page.url or page.url_path}  "
                    f"TODO={counts['TODO']} VERIFY={counts['VERIFY']}  (id {page.pk})"
                )
        for site_settings in SiteSettings.objects.select_related("site"):
            counts = count_placeholders(site_settings.__dict__)
            if counts:
                found += 1
                self.stdout.write(
                    f"site settings ({site_settings.site})  "
                    f"TODO={counts['TODO']} VERIFY={counts['VERIFY']}"
                )
        if not found:
            self.stdout.write(self.style.SUCCESS("no placeholders on live content"))
            return
        message = f"{found} live object(s) still contain placeholders"
        if options["fail"]:
            raise CommandError(message)
        self.stdout.write(self.style.WARNING(message))
