"""Link checker (spec §6): renders every live page in every locale through the test client,
collects `href`/`src`, verifies internal links resolve (2xx/3xx) and — with `--external` —
HEADs external URLs. Exit code 1 when something is broken so it can run in CI or cron.
"""

from __future__ import annotations

import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from django.core.management.base import BaseCommand
from django.test import Client
from wagtail.models import Page

HREF_RE = re.compile(r'(?:href|src)="([^"#]+)(?:#[^"]*)?"')
SKIP_PREFIXES = ("mailto:", "tel:", "javascript:", "data:", "sms:")


class Command(BaseCommand):
    help = "Check internal (and optionally external) links on every live page."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--external", action="store_true", help="also HEAD external URLs")
        parser.add_argument("--timeout", type=float, default=8.0)
        parser.add_argument("--limit", type=int, default=0, help="check only the first N pages")

    def handle(self, *args: Any, **options: Any) -> None:
        client = Client(HTTP_X_E2E="1")
        pages = Page.objects.live().public().filter(depth__gte=2).specific().order_by("path")
        if options["limit"]:
            pages = pages[: options["limit"]]
        internal: dict[str, set[str]] = {}
        external: dict[str, set[str]] = {}
        broken: list[str] = []
        checked_pages = 0
        for page in pages:
            url = page.url
            if not url:
                continue
            response = client.get(url)
            checked_pages += 1
            if response.status_code != 200:
                broken.append(f"{url} → HTTP {response.status_code} (page itself)")
                continue
            for link in HREF_RE.findall(response.content.decode("utf-8", "replace")):
                link = link.strip()
                if not link or link.startswith(SKIP_PREFIXES):
                    continue
                if link.startswith(("http://", "https://", "//")):
                    external.setdefault(link, set()).add(url)
                elif link.startswith("/"):
                    internal.setdefault(link.split("?")[0], set()).add(url)

        for link, sources in sorted(internal.items()):
            if link.startswith(("/static/", "/media/")):
                continue  # served by nginx/whitenoise, not by the URLconf
            status = client.get(link, follow=False).status_code
            if status >= 400:
                broken.append(f"{link} → HTTP {status} (from {sorted(sources)[0]})")

        if options["external"]:
            for link, sources in sorted(external.items()):
                target = "https:" + link if link.startswith("//") else link
                status = self._head(target, options["timeout"])
                if status >= 400 or status == 0:
                    broken.append(
                        f"{target} → HTTP {status or 'error'} (from {sorted(sources)[0]})"
                    )

        self.stdout.write(
            f"pages: {checked_pages}, internal links: {len(internal)}, external links: "
            f"{len(external)}{'' if options['external'] else ' (not checked, use --external)'}"
        )
        if broken:
            for line in broken:
                self.stdout.write(self.style.ERROR(f"BROKEN {line}"))
            raise SystemExit(1)
        self.stdout.write(self.style.SUCCESS("no broken links"))

    @staticmethod
    def _head(url: str, timeout: float) -> int:
        if urllib.parse.urlsplit(url).scheme not in ("http", "https"):
            return 0
        request = urllib.request.Request(  # noqa: S310 - scheme checked above
            url, method="HEAD", headers={"User-Agent": "ertaaniqla-linkcheck/1.0"}
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
                return int(response.status)
        except urllib.error.HTTPError as exc:
            if exc.code in (403, 405):  # HEAD refused — try GET
                try:
                    get = urllib.request.Request(  # noqa: S310 - scheme checked above
                        url, headers={"User-Agent": "ertaaniqla-linkcheck/1.0"}
                    )
                    with urllib.request.urlopen(get, timeout=timeout) as response:  # noqa: S310
                        return int(response.status)
                except urllib.error.HTTPError as exc2:
                    return int(exc2.code)
                except (urllib.error.URLError, TimeoutError, ValueError):
                    return 0
            return int(exc.code)
        except (urllib.error.URLError, TimeoutError, ValueError):
            return 0
