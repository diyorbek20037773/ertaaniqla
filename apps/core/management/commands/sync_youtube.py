"""Add the new videos of the portal's YouTube channel (Settings → Site settings → YouTube) to
«Videoroliklar» (D-085). Videos already on the site are left as they are."""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Import new videos from the portal's YouTube channel."

    def handle(self, *args: Any, **options: Any) -> None:
        from apps.media_library.youtube import sync_from_settings

        added = sync_from_settings()
        self.stdout.write(f"sync_youtube: added={len(added)} {','.join(added)}".rstrip())
