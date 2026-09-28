"""Re-create OG / story images whose file is gone (EA-04).

On a host with an ephemeral disk (Railway without a volume) a redeploy wipes `/media/og/` while
the database still points at the files. `--missing` (default) renders only those; `--all`
renders every live page. Runs inline, not through Celery.
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand
from wagtail.models import Page


def _missing(field: Any) -> bool:
    return not field or not field.storage.exists(field.name)


class Command(BaseCommand):
    help = "Regenerate OG/story images for live pages whose image file is missing."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--all", action="store_true", help="regenerate every live page")

    def handle(self, *args: Any, **options: Any) -> None:
        from apps.core.tasks import generate_og_image

        done = 0
        for page in Page.objects.live().filter(depth__gt=1).specific().iterator():
            if not hasattr(page, "og_image_generated") or getattr(page, "og_image_id", None):
                continue
            if (
                options["all"]
                or _missing(page.og_image_generated)
                or _missing(page.story_image_generated)
            ):
                generate_og_image(page.pk)
                done += 1
        self.stdout.write(self.style.SUCCESS(f"regenerated social images for {done} page(s)"))
