"""Manual run of the PII retention jobs (spec §8): question contacts 90 days after the answer,
feedback submissions after 180 days. Celery beat runs the same services nightly."""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Purge expired PII (question contacts > 90 d after answer, feedback > 180 d)."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--dry-run", action="store_true", help="only report what would go")

    def handle(self, *args: Any, **options: Any) -> None:
        from django.db import transaction

        from apps.faq.services import purge_contacts
        from apps.feedback.services import purge_old_submissions

        if options["dry_run"]:
            # run the real services inside a transaction that is always rolled back
            with transaction.atomic():
                questions = purge_contacts()
                feedback = purge_old_submissions()
                transaction.set_rollback(True)
            self.stdout.write(
                f"dry-run: {questions} question contact(s), {feedback} feedback row(s)"
            )
            return
        questions = purge_contacts()
        feedback = purge_old_submissions()
        self.stdout.write(
            self.style.SUCCESS(
                f"purged {questions} question contact(s), {feedback} feedback row(s)"
            )
        )
