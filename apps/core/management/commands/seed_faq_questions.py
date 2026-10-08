"""Add the final design's most asked questions (D-081) with placeholder answers for the doctors.
Safe to re-run: existing wording is never duplicated or changed (apps.faq.design)."""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Add the design's most asked questions (answers are placeholders for the doctors)."

    def handle(self, *args: Any, **options: Any) -> None:
        from apps.faq.design import seed_questions
        from apps.home.models import HomePage

        uz_home = HomePage.objects.filter(locale__language_code=settings.LANGUAGE_CODE).first()
        if uz_home is None:
            self.stdout.write("seed_faq_questions: no home page — skipped")
            return
        added = seed_questions(uz_home)
        self.stdout.write(f"seed_faq_questions: added={added}")
