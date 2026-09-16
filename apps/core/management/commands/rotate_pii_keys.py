"""Re-encrypt every encrypted column with the newest Fernet key (spec §8, RUNBOOK §6).

Procedure: prepend the new key to PII_ENCRYPTION_KEYS (old keys stay so rows can still be
read) → restart → run this command → remove the old key → restart. Rows are rewritten with
`update()` so `updated_at`/signals are untouched; the field's `get_prep_value` encrypts with
the first (newest) key.
"""

from __future__ import annotations

from typing import Any

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.core.fields import EncryptedTextField, reset_key_cache


def encrypted_fields() -> list[tuple[type[Any], list[str]]]:
    found: list[tuple[type[Any], list[str]]] = []
    for model in apps.get_models():
        names = [f.name for f in model._meta.get_fields() if isinstance(f, EncryptedTextField)]
        if names:
            found.append((model, names))
    return found


class Command(BaseCommand):
    help = "Re-encrypt all EncryptedTextField columns with the newest PII_ENCRYPTION_KEYS entry."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--batch-size", type=int, default=500)

    def handle(self, *args: Any, **options: Any) -> None:
        from django.conf import settings

        if not getattr(settings, "PII_ENCRYPTION_KEYS", None):
            raise CommandError("PII_ENCRYPTION_KEYS is empty — nothing to rotate to")
        reset_key_cache()
        total = 0
        for model, names in encrypted_fields():
            label = model._meta.label
            rotated = 0
            queryset = model._default_manager.all().order_by("pk")
            for obj in queryset.iterator(chunk_size=options["batch_size"]):
                values = {n: getattr(obj, n) for n in names if getattr(obj, n)}
                if not values:
                    continue
                with transaction.atomic():
                    # update() → get_prep_value → encrypt() with the newest key
                    model._default_manager.filter(pk=obj.pk).update(**values)
                rotated += 1
            total += rotated
            self.stdout.write(f"{label}: {rotated} row(s) re-encrypted ({', '.join(names)})")
        self.stdout.write(self.style.SUCCESS(f"done: {total} row(s)"))
