"""One-off: the client's videos of 2026-10-20 (D-101) added to the «Videoroliklar» list with their
Uzbek and Russian titles. Run once after the deploy:

    python manage.py client_update_20261020

Missing videos are created (cover from YouTube) above the earlier ones; existing ones only get
their empty fields filled, so a second run — or a run after an editor's change — changes nothing.
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "Add the client's videos of 2026-10-20 (safe to re-run)."

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        from apps.media_library.client_videos import VIDEOS_20261020, add_client_videos

        created, filled = add_client_videos(VIDEOS_20261020)
        self.stdout.write(f"videos created: {len(created)} {' '.join(created)}")
        self.stdout.write(f"videos with empty fields filled: {len(filled)} {' '.join(filled)}")
