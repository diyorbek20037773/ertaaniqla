"""`ArticlePage` — the content page type (spec §4.3). Blocks live in `blocks.py`."""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel
from wagtail.fields import StreamField
from wagtail.models import Page
from wagtail.search import index

from apps.articles.blocks import ArticleBodyBlock, stream_plain_text
from apps.core.models import BasePage


class ArticlePage(BasePage):
    summary = models.CharField(
        _("summary"),
        max_length=300,
        help_text=_("Shown in listings, the mega-menu and search results."),
    )
    hero_image = models.ForeignKey(
        settings.WAGTAILIMAGES_IMAGE_MODEL,
        verbose_name=_("hero image"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    body = StreamField(ArticleBodyBlock(), blank=True, verbose_name=_("body"))

    content_panels = [
        *Page.content_panels,
        FieldPanel("summary"),
        FieldPanel("hero_image"),
        FieldPanel("body"),
    ]
    search_fields = [
        *Page.search_fields,
        index.SearchField("summary", boost=2),
        index.SearchField("body"),
        index.AutocompleteField("title"),
    ]

    parent_page_types = [
        "sections.SectionIndexPage",
        "sections.TopicIndexPage",
        "articles.ArticlePage",
        "home.HomePage",
    ]
    subpage_types = ["articles.ArticlePage"]
    template = "articles/article_page.html"

    class Meta:
        verbose_name = _("article")
        verbose_name_plural = _("articles")

    jsonld_article = True

    def get_body_text(self) -> str:
        return f"{self.summary} {stream_plain_text(self.body)}"

    def get_jsonld(self, request: Any) -> list[dict[str, Any]]:
        from apps.core import seo
        from apps.core.templatetags.core_tags import site_root_url

        items = super().get_jsonld(request)
        base = site_root_url(request)
        for child in self.body:
            if child.block_type == "video" and child.value.get("video"):
                video = seo.video_ld(child.value["video"], base, self.locale.language_code)
                if video:
                    items.append(video)
        return items

    @property
    def block_types(self) -> list[str]:
        return [child.block_type for child in self.body]
