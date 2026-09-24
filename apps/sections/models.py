"""Section and topic index pages (spec §4.3). Sections are page-tree subtrees:
HomePage → SectionIndexPage(women|children) → TopicIndexPage → ArticlePage.
"""

from __future__ import annotations

from typing import Any

from django.core.validators import RegexValidator
from django.db import models
from django.http import HttpResponse, HttpResponseRedirect
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


def _redirect_to(page: Page | None, request: Any) -> HttpResponseRedirect | None:
    """302 to `page` unless previewing (editors must still see the index itself)."""
    if page is None or getattr(request, "is_preview", False):
        return None
    return HttpResponseRedirect(page.get_url(request=request))


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
    open_first_topic = models.BooleanField(
        _("open the first topic"),
        default=False,
        help_text=_(
            "The design has no section overview: visitors go straight to the first menu topic "
            "(302). The overview stays visible in preview."
        ),
    )

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
                FieldPanel("open_first_topic"),
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

    def serve(self, request: Any, *args: Any, **kwargs: Any) -> HttpResponse:
        if self.open_first_topic:
            items = self.get_menu_items()
            redirect = _redirect_to(items[0] if items else None, request)
            if redirect is not None:
                return redirect
        response: HttpResponse = super().serve(request, *args, **kwargs)
        return response

    def get_sitemap_urls(self, request: Any = None) -> list[dict[str, Any]]:
        return [] if self.open_first_topic else super().get_sitemap_urls(request)


class TopicIndexPage(BasePage):
    """E.g. «Скрининг», «Диагностика и лечение»: intro + auto-listing of child articles."""

    intro = StreamField(IntroBlock(), blank=True, verbose_name=_("intro"))
    summary = models.CharField(
        _("summary"),
        max_length=300,
        blank=True,
        help_text=_("Shown on the section index card and in the mega-menu."),
    )

    is_variant_group = models.BooleanField(
        _("children are variants of one topic"),
        default=False,
        help_text=_(
            "E.g. breast / cervical cancer: the topic opens its first child page (302) and every "
            "child shows a switch between the variants (Figma design)."
        ),
    )

    content_panels = [
        *Page.content_panels,
        FieldPanel("summary"),
        FieldPanel("intro"),
        FieldPanel("is_variant_group"),
    ]
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

    def get_variants(self) -> list[Page]:
        """The pages the variant switch offers (tree order), empty unless `is_variant_group`."""
        return self.get_articles() if self.is_variant_group else []

    def get_context(self, request: Any, *args: Any, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context(request, *args, **kwargs)
        context["articles"] = self.get_articles()
        return context

    def serve(self, request: Any, *args: Any, **kwargs: Any) -> HttpResponse:
        variants = self.get_variants()
        redirect = _redirect_to(variants[0] if variants else None, request)
        if redirect is not None:
            return redirect
        response: HttpResponse = super().serve(request, *args, **kwargs)
        return response

    def get_sitemap_urls(self, request: Any = None) -> list[dict[str, Any]]:
        return [] if self.is_variant_group else super().get_sitemap_urls(request)
