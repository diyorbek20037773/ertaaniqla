"""`manage.py seed_content --lang uz,ru` — build/update the full TZ page tree (spec §6).

Idempotent: safe to run on every deploy. Never writes medical content (placeholders only).
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.core.seed.builder import Seeder


class Command(BaseCommand):
    help = "Create or update the complete TZ page tree with placeholders in every language."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--lang",
            default=",".join(code for code, _ in settings.WAGTAIL_CONTENT_LANGUAGES),
            help="Comma-separated language codes, default language first (default: all).",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        languages = tuple(code.strip() for code in options["lang"].split(",") if code.strip())
        known = {code for code, _ in settings.WAGTAIL_CONTENT_LANGUAGES}
        unknown = [code for code in languages if code not in known]
        if unknown:
            raise CommandError(f"Unknown language(s): {', '.join(unknown)}")
        if languages[0] != settings.LANGUAGE_CODE:
            raise CommandError(
                f"The first language must be the default ({settings.LANGUAGE_CODE})."
            )
        result = Seeder(languages).run()
        self.stdout.write(
            self.style.SUCCESS(
                f"seed_content: created={result['created']} updated={result['updated']} "
                f"unchanged={result['unchanged']} languages={','.join(languages)}"
            )
        )
