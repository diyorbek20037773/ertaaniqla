"""Glossary (spec §4.3 `Term`, F14): parents' medical dictionary, glossary page, inline tooltips
(`glossary_tags.glossary_wrap`)."""

from __future__ import annotations

from typing import Any

from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField, StreamField
from wagtail.models import Page, TranslatableMixin
from wagtail.search import index
from wagtail.snippets.models import register_snippet

from apps.articles.blocks import IntroBlock, stream_plain_text
from apps.core.models import BasePage, SectionKey, TimeStampedModel


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


class GlossaryPage(BasePage):
    """`/uz/lugat/` `/ru/slovar/` — every term of the current language, grouped by letter,
    filterable by section and by a plain `?q=` substring (F14)."""

    intro = StreamField(IntroBlock(), blank=True, verbose_name=_("intro"))

    content_panels = [*Page.content_panels, FieldPanel("intro")]
    parent_page_types = ["home.HomePage"]
    subpage_types: list[str] = []
    template = "glossary/glossary_page.html"

    class Meta:
        verbose_name = _("glossary page")

    def get_body_text(self) -> str:
        return stream_plain_text(self.intro)

    def get_terms(self, section: str = "", query: str = "") -> list[Term]:
        qs = Term.objects.filter(locale=self.locale)
        if section in {TermSection.WOMEN, TermSection.CHILDREN}:
            qs = qs.filter(section__in=[section, TermSection.BOTH])
        if query:
            qs = qs.filter(Q(term__icontains=query) | Q(synonyms__icontains=query))
        return list(qs.order_by("term"))

    def get_context(self, request: Any, *args: Any, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context(request, *args, **kwargs)
        section = request.GET.get("section", "")
        query = " ".join(request.GET.get("q", "").split())[:60]
        terms = self.get_terms(section, query)
        groups: dict[str, list[Term]] = {}
        for term in terms:
            groups.setdefault(term.term[:1].upper(), []).append(term)
        context.update(
            {
                "terms": terms,
                "groups": sorted(groups.items()),
                "section_filter": section
                if section in {TermSection.WOMEN, TermSection.CHILDREN}
                else "",
                "query": query,
            }
        )
        return context
