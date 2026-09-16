"""Core Celery tasks."""

from __future__ import annotations

import logging

from celery import shared_task
from django.core.files.base import ContentFile

logger = logging.getLogger("ertaaniqla.core")


@shared_task(name="core.generate_og_image", ignore_result=True)
def generate_og_image(page_id: int) -> str:
    """Render and store the OpenGraph image for a live page (spec §10). Returns the file name."""
    from wagtail.models import Page

    from apps.core.og import render_og_image, render_story_image

    page = Page.objects.filter(pk=page_id, live=True).first()
    if page is None:
        return ""
    specific = page.specific
    if not hasattr(specific, "og_image_generated"):
        return ""
    subtitle = getattr(specific, "summary", "") or getattr(specific, "tagline", "") or ""
    png = render_og_image(
        title=str(specific.title),
        subtitle=str(subtitle),
        section_key=str(getattr(specific, "section_key", "") or ""),
        language=str(specific.locale.language_code),
    )
    story = render_story_image(
        title=str(specific.title),
        subtitle=str(subtitle),
        section_key=str(getattr(specific, "section_key", "") or ""),
        language=str(specific.locale.language_code),
    )
    name = f"{specific.locale.language_code}-{specific.pk}.png"  # stored under upload_to="og/"
    if specific.og_image_generated:
        specific.og_image_generated.delete(save=False)
    specific.og_image_generated.save(name, ContentFile(png), save=False)
    if specific.story_image_generated:
        specific.story_image_generated.delete(save=False)
    specific.story_image_generated.save(name, ContentFile(story), save=False)
    # update_fields: no new revision, no signals storm (page_published is not re-sent)
    specific.save(update_fields=["og_image_generated", "story_image_generated"], clean=False)
    return str(specific.og_image_generated.name)


HERO_FILTERS = ("width-400", "width-800", "width-1200", "fill-640x360", "fill-400x225")


@shared_task(name="core.prefetch_renditions", ignore_result=True)
def prefetch_renditions(page_id: int) -> int:
    """Generate the hero/card renditions (WebP + original format) used by the templates
    (spec §4.5), so the first visitor never waits for Pillow. Returns the number generated."""
    from wagtail.models import Page

    page = Page.objects.filter(pk=page_id).first()
    if page is None:
        return 0
    image = getattr(page.specific, "hero_image", None)
    if image is None:
        return 0
    count = 0
    for spec in HERO_FILTERS:
        for fmt in ("", "|format-webp"):
            try:
                image.get_rendition(spec + fmt)
                count += 1
            except Exception:  # pragma: no cover - broken source file
                logger.exception("rendition %s%s failed for image %s", spec, fmt, image.pk)
    return count
