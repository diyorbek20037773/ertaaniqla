"""Cache invalidation on content changes (spec §4.5)."""

from __future__ import annotations

from typing import Any

from django.db import transaction
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


@receiver(page_published)
def _generate_og_image(sender: Any, instance: Any, **kwargs: Any) -> None:
    """Spec §10: OG image per page, generated on publish unless the editor chose one."""
    if not hasattr(instance, "og_image_generated") or getattr(instance, "og_image_id", None):
        return
    from apps.core.tasks import generate_og_image

    page_id = instance.pk
    transaction.on_commit(lambda: generate_og_image.delay(page_id))
