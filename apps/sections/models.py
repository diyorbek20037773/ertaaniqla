"""Section and topic index pages (spec §4.3). Sections are page-tree subtrees:
HomePage → SectionIndexPage(women|children) → TopicIndexPage → ArticlePage.
"""

from __future__ import annotations

from typing import Any

from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.fields import StreamField
from wagtail.models import Page
from wagtail.search import index

from apps.articles.blocks import IntroBlock, stream_plain_text
from apps.core.models import BasePage, SectionKey

HEX_COLOUR = RegexValidator(r"^#[0-9a-fA-F]{6}$", _("Enter a colour like #b8336a."))

SECTION_ICONS = [
    ("ribbon-women", _("🎗 ribbon (women)")),
    ("ribbon-children", _("🎀 ribbon (children)")),
]


class SectionIndexPage(BasePage):
    """Root of one of the two sections; provides the mega-menu for its subtree."""

    section_key = models.CharField(
        _("section"), max_length=16, choices=SectionKey.choices, db_index=True
    )
    tagline = models.CharField(
        _("tagline"),
        max_length=200,
        blank=True,
        help_text=_("One sentence shown on the home page card and under the section title."),
    )
    colour_primary = models.CharField(
        _("primary colour"),
        max_length=7,
        blank=True,
        validators=[HEX_COLOUR],
        help_text=_("Overrides the token default (--brand). Leave empty to use tokens.css."),
    )
    colour_accent = models.CharField(
        _("accent colour"), max_length=7, blank=True, validators=[HEX_COLOUR]
    )
    icon = models.CharField(_("icon"), max_length=32, choices=SECTION_ICONS, default="ribbon-women")
    intro = StreamField(IntroBlock(), blank=True, verbose_name=_("intro"))

    content_panels = [
        *Page.content_panels,
        FieldPanel("tagline"),
        FieldPanel("intro"),
    ]
    settings_panels = [
        *BasePage.settings_panels,
        MultiFieldPanel(
            [
                FieldPanel("section_key"),
                FieldPanel("icon"),
                FieldPanel("colour_primary"),
                FieldPanel("colour_accent"),
            ],
            heading=_("Section identity"),
        ),
    ]
    search_fields = [*Page.search_fields, index.SearchField("tagline"), index.SearchField("intro")]

    parent_page_types = ["home.HomePage"]
    subpage_types = [
        "sections.TopicIndexPage",
        "articles.ArticlePage",
        "directory.DirectoryPage",
    ]
    template = "sections/section_index_page.html"

    class Meta:
        verbose_name = _("section index page")

    def get_body_text(self) -> str:
        return stream_plain_text(self.intro)

    def get_section(self) -> SectionIndexPage:
        return self

    @property
    def emoji(self) -> str:
        return "🎗" if self.section_key == SectionKey.WOMEN else "🎀"

    def get_menu_items(self) -> list[Page]:
        """Top-level menu of this section: live children with `show_in_menus`, tree order."""
        return list(self.get_children().live().in_menu().specific())

    def get_subsections(self) -> list[Page]:
        """Every live child (menu or not) — used by the section index listing."""
        return list(self.get_children().live().specific())

    def get_context(self, request: Any, *args: Any, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context(request, *args, **kwargs)
        context["subsections"] = self.get_subsections()
        return context


class TopicIndexPage(BasePage):
    """E.g. «Скрининг», «Диагностика и лечение»: intro + auto-listing of child articles."""

    intro = StreamField(IntroBlock(), blank=True, verbose_name=_("intro"))
    summary = models.CharField(
        _("summary"),
        max_length=300,
        blank=True,
        help_text=_("Shown on the section index card and in the mega-menu."),
    )

    content_panels = [*Page.content_panels, FieldPanel("summary"), FieldPanel("intro")]
    search_fields = [*Page.search_fields, index.SearchField("summary"), index.SearchField("intro")]

    parent_page_types = ["sections.SectionIndexPage", "sections.TopicIndexPage"]
    subpage_types = ["articles.ArticlePage", "sections.TopicIndexPage"]
    template = "sections/topic_index_page.html"

    class Meta:
        verbose_name = _("topic index page")

    def get_body_text(self) -> str:
        return stream_plain_text(self.intro)

    def get_articles(self) -> list[Page]:
        return list(self.get_children().live().specific())

    def get_context(self, request: Any, *args: Any, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context(request, *args, **kwargs)
        context["articles"] = self.get_articles()
        return context
