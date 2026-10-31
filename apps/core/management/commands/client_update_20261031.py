"""One-off (D-109): the Telegram channel's posts get a list of their own, apart from the site's own
articles in «Foydali maʼlumotlar» (developer's choice 2026-10-31). Run once after the deploy:

    python manage.py client_update_20261031

* creates «Yangiliklar» (/uz/telegram-yangiliklar/) and its Russian version «Новости»
  (/ru/telegram-novosti/) next to «Foydali maʼlumotlar», marked as the channel's list: new posts
  of the channel are published there, the header shows it after «Foydali maʼlumotlar»;
* moves the posts imported so far into them; their old addresses redirect to the new ones.

A second run changes nothing.
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

UZ = {
    "title": "Yangiliklar",
    "slug": "telegram-yangiliklar",
    "lead": "«Erta aniqla» Telegram kanalidagi xabarlar.",
}
RU = {
    "title": "Новости",
    "slug": "telegram-novosti",
    "lead": "Сообщения Telegram-канала «Erta aniqla».",
}


def ensure_lists() -> tuple[Any, Any, bool]:
    """The channel's uz list and its ru version (None without a Russian tree); created?"""
    from wagtail.models import Locale, Page

    from apps.posts.models import PostIndexPage, PostKind

    uz = Locale.objects.get(language_code="uz")
    created = False
    uz_list = PostIndexPage.objects.filter(locale=uz, telegram_feed=True).first()
    if uz_list is None:
        useful = PostIndexPage.objects.filter(
            locale=uz, kind=PostKind.NEWS, telegram_feed=False
        ).first()
        if useful is None:
            raise CommandError("no «Foydali maʼlumotlar» list to put «Yangiliklar» next to")
        uz_list = PostIndexPage(
            locale=uz, kind=PostKind.NEWS, telegram_feed=True, show_in_menus=False, **UZ
        )
        useful.get_parent().add_child(instance=uz_list)
        uz_list.save_revision().publish()
        created = True
    ru = Locale.objects.filter(language_code="ru").first()
    ru_list = uz_list.get_translation_or_none(ru) if ru is not None else None
    if ru is not None and ru_list is None and uz_list.get_parent().get_translation_or_none(ru):
        ru_list = uz_list.copy_for_translation(ru)
        ru_list.title = ru_list.draft_title = RU["title"]
        ru_list.lead = RU["lead"]
        # set in the database: a save() would see a new slug and redirect from the uz one
        ru_list.slug = RU["slug"]
        ru_list.set_url_path(ru_list.get_parent())
        Page.objects.filter(pk=ru_list.pk).update(slug=ru_list.slug, url_path=ru_list.url_path)
        ru_list.save()
        ru_list.save_revision().publish()
        created = True
    return uz_list, ru_list, created


def move_posts(uz_list: Any, ru_list: Any) -> int:
    """Every news item the bot made goes to the channel's list of its language."""
    from apps.posts.models import PostPage, TelegramPost

    ids = {i for r in TelegramPost.objects.all() for i in (r.page_id, r.ru_page_id) if i}
    moved = 0
    for page in PostPage.objects.filter(id__in=ids).order_by("date", "id"):
        target = uz_list if page.locale_id == uz_list.locale_id else ru_list
        if target is None or page.get_parent().pk == target.pk:
            continue
        page.move(target, pos="last-child")  # Wagtail makes the redirect from the old address
        moved += 1
    return moved


class Command(BaseCommand):
    help = "D-109: «Yangiliklar» — the Telegram channel's own news list."

    def handle(self, *args: Any, **options: Any) -> None:
        with transaction.atomic():
            uz_list, ru_list, created = ensure_lists()
            moved = move_posts(uz_list, ru_list)
        self.stdout.write(
            f"client_update_20261031: lists {'created' if created else 'kept'} "
            f"({uz_list.url_path}{', ' + ru_list.url_path if ru_list else ''}), moved {moved}"
        )
