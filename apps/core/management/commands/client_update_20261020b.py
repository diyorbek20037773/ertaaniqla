"""One-off: the Russian home page keeps the brand slogan in Uzbek (client 2026-10-20, D-102):
«Эрта аниқла – ҳаётни сақла» instead of the translated «Эрта аниқла – сохрани жизнь». Run once
after the deploy:

    python manage.py client_update_20261020b

Only the seeded wording is replaced; a slogan an editor wrote in the CMS is kept, so a second
run changes nothing.
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

OLD = "Эрта аниқла – сохрани жизнь"
NEW = "Эрта аниқла – ҳаётни сақла"


class Command(BaseCommand):
    help = "Russian home page slogan in Uzbek: «Эрта аниқла – ҳаётни сақла» (safe to re-run)."

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        from apps.home.models import HomePage

        changed = 0
        for page in HomePage.objects.filter(locale__language_code="ru"):
            if page.hero_title != OLD:
                continue  # already changed, or an editor's own wording
            page.hero_title = NEW
            page.save_revision(log_action=True).publish()
            changed += 1
        self.stdout.write(f"Russian home slogan updated on {changed} page(s)")
