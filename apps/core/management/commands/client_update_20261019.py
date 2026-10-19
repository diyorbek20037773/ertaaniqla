"""One-off: the client's videos of 2026-10-19 (D-097) added to the «Videoroliklar» list with their
Uzbek and Russian descriptions. Run once after the deploy:

    python manage.py client_update_20261019

Missing videos are created (cover from YouTube); existing ones only get their empty fields
filled, so a second run — or a run after an editor's change — changes nothing.
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "Add the client's videos of 2026-10-19 (safe to re-run)."

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        from apps.media_library.client_videos import add_client_videos

        created, filled = add_client_videos()
        self.stdout.write(f"videos created: {len(created)} {' '.join(created)}")
        self.stdout.write(f"videos with empty fields filled: {len(filled)} {' '.join(filled)}")
