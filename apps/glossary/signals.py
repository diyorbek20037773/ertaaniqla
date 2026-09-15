from __future__ import annotations

from typing import Any

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.glossary.models import Term
from apps.glossary.templatetags.glossary_tags import invalidate_glossary_cache


@receiver(post_save, sender=Term)
@receiver(post_delete, sender=Term)
def _term_changed(sender: Any, **kwargs: Any) -> None:
    invalidate_glossary_cache()
