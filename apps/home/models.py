"""`HomePage` (spec §4.3): hero, two section cards, featured articles/videos, stats strip,
emergency banner."""

from __future__ import annotations

from typing import Any

from django.db import models
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.fields import RichTextField, StreamField
from wagtail.models import Orderable, Page
from wagtail.search import index

from apps.articles.blocks import IntroBlock, StatBlock, stream_plain_text
from apps.core.models import BasePage


class HomePage(BasePage):
    hero_title = models.CharField(
        _("hero title"),
        max_length=160,
        blank=True,
        help_text=_("Key idea of the portal — early detection. Filled by the copywriter."),
    )
    hero_subtitle = models.CharField(_("hero subtitle"), max_length=300, blank=True)
    emergency_banner = RichTextField(
        _("home emergency banner"),
        blank=True,
        editor="minimal",
        help_text=_(
            "Optional home-only banner (e.g. screening campaign month). "
            "The site-wide banner lives in Settings → Site settings."
        ),
    )
    stats = StreamField(
        [("stat", StatBlock())],
        blank=True,
        max_num=3,
        verbose_name=_("statistics strip (3 stats)"),
    )
    body = StreamField(IntroBlock(), blank=True, verbose_name=_("additional content"))

    content_panels = [
        *Page.content_panels,
        MultiFieldPanel([FieldPanel("hero_title"), FieldPanel("hero_subtitle")], heading=_("Hero")),
        FieldPanel("emergency_banner"),
        InlinePanel("featured_articles", label=_("Featured articles"), max_num=6),
        InlinePanel("featured_videos", label=_("Featured videos"), max_num=3),
        FieldPanel("stats"),
        FieldPanel("body"),
    ]
    search_fields = [*Page.search_fields, index.SearchField("hero_title")]

    parent_page_types = ["wagtailcore.Page"]
    subpage_types = [
        "sections.SectionIndexPage",
        "articles.ArticlePage",
        "directory.DirectoryPage",
        "stories.StoryIndexPage",
        "tools.ToolsIndexPage",
        "faq.FAQPage",
        "feedback.FeedbackPage",
        "glossary.GlossaryPage",
        "media_library.MaterialsPage",
    ]
    template = "home/home_page.html"

    class Meta:
        verbose_name = _("home page")

    def get_body_text(self) -> str:
        return f"{self.hero_title} {self.hero_subtitle} {stream_plain_text(self.body)}"

    def get_sections(self) -> list[Page]:
        from apps.sections.models import SectionIndexPage

        return list(SectionIndexPage.objects.child_of(self).live().specific())

    def get_context(self, request: Any, *args: Any, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context(request, *args, **kwargs)
        context["sections"] = self.get_sections()
        context["featured_articles"] = [
            item.article.specific
            for item in self.featured_articles.select_related("article")
            if item.article.live
        ]
        context["featured_videos"] = [
            item.video for item in self.featured_videos.select_related("video", "video__poster")
        ]
        return context


class HomeFeaturedArticle(Orderable):
    page = ParentalKey(HomePage, on_delete=models.CASCADE, related_name="featured_articles")
    article = models.ForeignKey(
        "articles.ArticlePage",
        verbose_name=_("article"),
        on_delete=models.CASCADE,
        related_name="+",
    )

    panels = [FieldPanel("article")]

    class Meta(Orderable.Meta):
        verbose_name = _("featured article")

    def __str__(self) -> str:
        return str(self.article)


class HomeFeaturedVideo(Orderable):
    page = ParentalKey(HomePage, on_delete=models.CASCADE, related_name="featured_videos")
    video = models.ForeignKey(
        "media_library.Video",
        verbose_name=_("video"),
        on_delete=models.CASCADE,
        related_name="+",
    )

    panels = [FieldPanel("video")]

    class Meta(Orderable.Meta):
        verbose_name = _("featured video")

    def __str__(self) -> str:
        return str(self.video)
