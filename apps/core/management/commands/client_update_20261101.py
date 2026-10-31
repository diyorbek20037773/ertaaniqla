"""One-off (D-109, developer 2026-11-01: «telegram sozini olib tashla, shunchaki "yangiliklar"
bolsin»): the Telegram channel's list takes the plain address. Run once after the deploy:

    python manage.py client_update_20261101

* «Foydali maʼlumotlar»: /uz/yangiliklar/ → /uz/foydali-malumotlar/,
  /ru/novosti/ → /ru/poleznaya-informatsiya/ (first, to free the addresses);
* «Yangiliklar» (the channel): /uz/telegram-yangiliklar/ → /uz/yangiliklar/,
  /ru/telegram-novosti/ → /ru/novosti/.

The channel list's lead loses «Telegram» too («Erta aniqla» loyihasining soʻnggi yangiliklari.).
The articles' and the posts' old addresses redirect (Wagtail makes the redirects when a slug
changes). A list with an unpublished draft is left alone (an editor's work is never published by
this command); a second run changes nothing.
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

# the lead `client_update_20261031` gave the channel's list → the one without «Telegram»
LEADS = {
    "uz": (
        "«Erta aniqla» Telegram kanalidagi xabarlar.",
        "«Erta aniqla» loyihasining soʻnggi yangiliklari.",
    ),
    "ru": ("Сообщения Telegram-канала «Erta aniqla».", "Последние новости проекта «Erta aniqla»."),
}

# (the channel's list?, language): (old slug, new slug) — the site's own list goes first
RENAMES: tuple[tuple[bool, str, str, str], ...] = (
    (False, "uz", "yangiliklar", "foydali-malumotlar"),
    (False, "ru", "novosti", "poleznaya-informatsiya"),
    (True, "uz", "telegram-yangiliklar", "yangiliklar"),
    (True, "ru", "telegram-novosti", "novosti"),
)


def rename_lists() -> tuple[list[str], list[str]]:
    """(renamed "old → new" lines, skipped lines)."""
    from apps.posts.models import PostIndexPage, PostKind

    renamed: list[str] = []
    skipped: list[str] = []
    for channel, language, old, new in RENAMES:
        page = PostIndexPage.objects.filter(
            locale__language_code=language, kind=PostKind.NEWS, telegram_feed=channel, slug=old
        ).first()
        if page is None:
            continue
        if page.has_unpublished_changes:
            skipped.append(f"{page.url_path} (unpublished draft)")
            continue
        if page.get_siblings(inclusive=False).filter(slug=new).exists():
            skipped.append(f"{page.url_path} ({new} is taken)")  # its neighbour was skipped
            continue
        old_path = page.url_path
        page.slug = new
        if channel and page.lead == LEADS[language][0]:
            page.lead = LEADS[language][1]
        page.save_revision().publish()
        renamed.append(f"{old_path} → {page.url_path}")
    return renamed, skipped


class Command(BaseCommand):
    help = "D-109: «Yangiliklar» at /uz/yangiliklar/, «Foydali maʼlumotlar» at its own address."

    def handle(self, *args: Any, **options: Any) -> None:
        with transaction.atomic():
            renamed, skipped = rename_lists()
        for line in renamed:
            self.stdout.write(f"renamed {line}")
        for line in skipped:
            self.stdout.write(f"skipped {line}")
        self.stdout.write(f"client_update_20261101: renamed {len(renamed)}")
