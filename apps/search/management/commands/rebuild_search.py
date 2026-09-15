"""`manage.py rebuild_search` (spec §6) — rebuild the Postgres FTS index (wraps Wagtail's
`update_index`). Run after bulk imports or a search-config change."""

from __future__ import annotations

from typing import Any

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Rebuild the full-text search index for every indexed model."

    def handle(self, *args: Any, **options: Any) -> None:
        call_command("update_index", verbosity=options.get("verbosity", 1))
        self.stdout.write(self.style.SUCCESS("rebuild_search: index rebuilt"))
