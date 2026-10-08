"""Fill the empty final-design landing blocks of every home page (D-081). Safe to re-run: text an
editor already entered is kept (apps.home.design)."""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Fill empty landing blocks (directions, free screening, questions) with the design copy."

    def handle(self, *args: Any, **options: Any) -> None:
        from apps.home.design import fill_home_design
        from apps.home.models import HomePage

        homes = list(HomePage.objects.all().select_related("locale"))
        uz_home = next((h for h in homes if h.locale.language_code == settings.LANGUAGE_CODE), None)
        if uz_home is None:
            self.stdout.write("seed_home_design: no home page — skipped")
            return
        for home in homes:
            changed = fill_home_design(home, uz_home)
            code = home.locale.language_code
            self.stdout.write(f"seed_home_design: {code} filled={','.join(changed) or '-'}")
