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

    from apps.core.og import render_og_image

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
    name = f"{specific.locale.language_code}-{specific.pk}.png"  # stored under upload_to="og/"
    if specific.og_image_generated:
        specific.og_image_generated.delete(save=False)
    specific.og_image_generated.save(name, ContentFile(png), save=False)
    # update_fields: no new revision, no signals storm (page_published is not re-sent)
    specific.save(update_fields=["og_image_generated"], clean=False)
    return str(specific.og_image_generated.name)
