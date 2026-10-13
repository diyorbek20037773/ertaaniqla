"""Apply the client's content changes of 2026-10-13 (docs/FAQ.docx, D-084) to a live site:
the women's «Savol-javob» tab (one page per disease) is created when missing, «Xabardorlik» is
retitled «Umumiy maʼlumot» and «Haqimizda» «Biz haqimizda» — only where the seeded title is still
in place. Nothing an editor changed is overwritten; safe to re-run."""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand

RENAMES = (
    (
        "women.awareness",
        {"uz": "Xabardorlik", "ru": "Осведомленность"},
        {"uz": "Umumiy maʼlumot", "ru": "Общая информация"},
    ),
    ("about", {"uz": "Haqimizda"}, {"uz": "Biz haqimizda"}),
)


class Command(BaseCommand):
    help = "Create the women's «Savol-javob» tab and apply the client's renames (2026-10-13)."

    def handle(self, *args: Any, **options: Any) -> None:
        from apps.core.navigation import invalidate_navigation
        from apps.core.seed.builder import Seeder

        seeder = Seeder()
        created = seeder.add_missing(("women.faq",))
        renamed = sum(seeder.rename(key, old, new) for key, old, new in RENAMES)
        invalidate_navigation()
        self.stdout.write(
            f"seed_client_changes: created={','.join(created) or '-'} renamed={renamed}"
        )
