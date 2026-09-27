"""Cache invalidation on content changes (spec §4.5)."""

from __future__ import annotations

from typing import Any

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from wagtail.models import Page
from wagtail.signals import page_published, page_unpublished, post_page_move

from apps.core.cache import bump_page_cache
from apps.core.navigation import invalidate_navigation
from apps.core.queue import enqueue_on_commit


@receiver(page_published)
@receiver(page_unpublished)
@receiver(post_page_move)
def _page_changed(sender: Any, **kwargs: Any) -> None:
    invalidate_navigation()
    bump_page_cache()


@receiver(post_delete, sender=Page)
def _page_deleted(sender: Any, **kwargs: Any) -> None:
    invalidate_navigation()
    bump_page_cache()


@receiver(post_save)
def _settings_changed(sender: Any, **kwargs: Any) -> None:
    """Site settings, terms, institutions, questions: rendered into pages → drop the cache."""
    label = getattr(getattr(sender, "_meta", None), "label", "")
    if label in {
        "core.SiteSettings",
        "glossary.Term",
        "directory.Institution",
        "faq.Question",
        "media_library.Video",
    }:
        bump_page_cache()
    if label == "core.SiteSettings":
        invalidate_navigation()  # header menu pages (about / doctors) live in the settings


@receiver(page_published)
def _generate_og_image(sender: Any, instance: Any, **kwargs: Any) -> None:
    """Spec §10: OG image per page, generated on publish unless the editor chose one."""
    if not hasattr(instance, "og_image_generated") or getattr(instance, "og_image_id", None):
        return
    from apps.core.tasks import generate_og_image

    enqueue_on_commit(generate_og_image, instance.pk)


@receiver(page_published)
def _prefetch_renditions(sender: Any, instance: Any, **kwargs: Any) -> None:
    """Spec §4.5: image renditions are generated on publish, not on the first visit."""
    if getattr(instance, "hero_image_id", None) is None:
        return
    from apps.core.tasks import prefetch_renditions

    enqueue_on_commit(prefetch_renditions, instance.pk)
