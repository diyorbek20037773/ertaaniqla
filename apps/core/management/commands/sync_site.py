"""Point the default Wagtail Site at the public origin from `SITE_BASE_URL` (D-075).

Canonical, hreflang, OG image, JSON-LD, share links and the per-language sitemaps are all built
from `Site.root_url`; the seed creates the Site as `localhost:80`, so without this every absolute
URL on a deployed host read `http://localhost/…`. Idempotent; the `migrate` role runs it.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from wagtail.models import Site


def site_target(base_url: str) -> tuple[str, int]:
    """`https://ertaaniqla.uz` → ("ertaaniqla.uz", 443); an explicit port wins."""
    parts = urlsplit(base_url)
    if not parts.hostname:
        raise CommandError(f"SITE_BASE_URL has no host: {base_url!r}")
    port = parts.port or (443 if parts.scheme == "https" else 80)
    return parts.hostname, port


class Command(BaseCommand):
    help = "Set the default Wagtail Site hostname/port from SITE_BASE_URL."

    def handle(self, *args: Any, **options: Any) -> None:
        hostname, port = site_target(str(settings.SITE_BASE_URL))
        site = Site.objects.filter(is_default_site=True).first()
        if site is None:
            self.stdout.write("no default site yet (run seed_content first) — nothing to do")
            return
        if (site.hostname, site.port) == (hostname, port):
            self.stdout.write(f"site already {hostname}:{port}")
            return
        site.hostname, site.port = hostname, port
        site.save(update_fields=["hostname", "port"])
        # Site.root_url is cached per request only, but page URLs are in the page cache
        from apps.core.cache import bump_page_cache

        bump_page_cache()
        self.stdout.write(self.style.SUCCESS(f"default site → {hostname}:{port}"))
