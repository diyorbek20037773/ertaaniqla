"""Publish the client's Word news (`scripts/news_docx.py` → `apps/posts/news/*.json`, D-090).

    python manage.py publish_client_news

Creates every item that is not on the site yet — Uzbek under «Foydali maʼlumotlar» and its
Russian version linked as the translation — with its topic, date and cover. Items already there
are left as editors made them; a Russian version nobody edited takes the client's own Russian.
Safe to re-run.
"""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "Publish the client's news items from apps/posts/news/*.json (safe to re-run)."

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        from apps.core.cache import bump_page_cache
        from apps.posts.client_news import publish_client_news

        uz_count, ru_count = publish_client_news()
        bump_page_cache()
        self.stdout.write(f"publish_client_news: uz={uz_count} ru={ru_count}")
