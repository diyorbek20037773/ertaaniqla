"""Cache invalidation on content changes (spec §4.5)."""

from __future__ import annotations

from typing import Any

from django.db.models.signals import post_delete
from django.dispatch import receiver
from wagtail.models import Page
from wagtail.signals import page_published, page_unpublished, post_page_move

from apps.core.navigation import invalidate_navigation


@receiver(page_published)
@receiver(page_unpublished)
@receiver(post_page_move)
def _page_changed(sender: Any, **kwargs: Any) -> None:
    invalidate_navigation()


@receiver(post_delete, sender=Page)
def _page_deleted(sender: Any, **kwargs: Any) -> None:
    invalidate_navigation()
