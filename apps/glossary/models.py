"""Glossary terms (spec §4.3 `Term`): parents' medical dictionary, inline tooltips (M4)."""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField
from wagtail.models import TranslatableMixin
from wagtail.search import index
from wagtail.snippets.models import register_snippet

from apps.core.models import SectionKey, TimeStampedModel


class TermSection(models.TextChoices):
    WOMEN = SectionKey.WOMEN.value, SectionKey.WOMEN.label
    CHILDREN = SectionKey.CHILDREN.value, SectionKey.CHILDREN.label
    BOTH = "both", _("Both sections")


@register_snippet
class Term(TranslatableMixin, index.Indexed, TimeStampedModel):
    term = models.CharField(_("term"), max_length=120, db_index=True)
    definition = RichTextField(_("definition"), editor="minimal")
    section = models.CharField(
        _("section"), max_length=16, choices=TermSection.choices, default=TermSection.BOTH
    )
    synonyms = models.CharField(
        _("synonyms"),
        max_length=300,
        blank=True,
        help_text=_("Comma-separated alternative spellings (e.g. Cyrillic, abbreviations)."),
    )

    panels = [
        FieldPanel("term"),
        FieldPanel("definition"),
        FieldPanel("section"),
        FieldPanel("synonyms"),
    ]

    search_fields = [
        index.SearchField("term", boost=3),
        index.SearchField("synonyms"),
        index.SearchField("definition"),
        index.FilterField("locale_id"),
        index.FilterField("section"),
    ]

    class Meta(TranslatableMixin.Meta):
        verbose_name = _("glossary term")
        verbose_name_plural = _("glossary terms")
        ordering = ["term"]

    def __str__(self) -> str:
        return self.term

    @property
    def synonym_list(self) -> list[str]:
        return [s.strip() for s in self.synonyms.split(",") if s.strip()]
