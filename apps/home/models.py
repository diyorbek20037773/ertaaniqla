"""`HomePage` (spec §4.3): hero, two section cards, featured articles/videos, stats strip,
emergency banner."""

from __future__ import annotations

from typing import Any

from django.db import models
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
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
        # Design 2026-10 replaced «featured articles / videos» and the stats strip with the
        # news, videos and articles feeds; their panels are hidden, the data stays until a
        # contract migration removes the fields (D-077).
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
        "media_library.VideoIndexPage",
        "posts.PostIndexPage",
    ]
    template = "home/home_page.html"

    class Meta:
        verbose_name = _("home page")

    @property
    def html_title(self) -> str:
        """Hero slogan ("Erta aniqla – hayotni saqla"), not "Erta aniqla — Erta aniqla" (EA-13)."""
        return str(self.seo_title or self.hero_title or self.title)

    def get_body_text(self) -> str:
        return f"{self.hero_title} {self.hero_subtitle} {stream_plain_text(self.body)}"

    def get_sections(self) -> list[Page]:
        from apps.sections.models import SectionIndexPage

        return list(SectionIndexPage.objects.child_of(self).live().specific())

    @property
    def hero_title_parts(self) -> tuple[str, str]:
        """Figma hero: «ERTA ANIQLA –» in the gradient, «HAYOTNI SAQLA» in grey below.

        The title is split after the first dash; without one the whole title is the main part.
        """
        title = self.hero_title or self.title
        for dash in (" – ", " — ", " - "):
            main, found, rest = title.partition(dash)
            if found:
                return f"{main}{dash.rstrip()}", rest
        return title, ""

    def get_directory_url(self) -> str:
        """«Murojaat qilish» in the hero → the «where to go» directory (D-064)."""
        from apps.directory.models import DirectoryPage

        page = DirectoryPage.objects.live().filter(locale=self.locale).first()
        return str(page.url or "") if page is not None else ""

    def get_quick_checks(self, request: Any) -> list[Page]:
        """Flag-enabled tool pages shown as the landing page's check cards (Figma 2408:26)."""
        from apps.tools.models import ToolsIndexPage

        index = ToolsIndexPage.objects.child_of(self).live().first()
        return [] if index is None else index.get_tools(request)[:3]

    def get_landing_feeds(self) -> dict[str, Any]:
        """Design 2026-10 landing blocks: «Eng ko'p beriladigan savollar» topic cards, the newest
        news (lead + three rows), videos and articles — each with its list page for the pills."""
        from apps.core.models import Topic
        from apps.faq.models import FAQPage
        from apps.media_library.videos import VideoIndexPage, ready_videos
        from apps.posts.models import PostIndexPage, PostKind

        def child(model: Any, **filters: Any) -> Any:
            return model.objects.child_of(self).live().filter(**filters).first()

        news_index = child(PostIndexPage, kind=PostKind.NEWS)
        articles_index = child(PostIndexPage, kind=PostKind.ARTICLES)
        video_index = child(VideoIndexPage)
        videos = list(ready_videos()[:8])
        if video_index is not None:
            video_index.specific.add_watch_urls(videos)
        return {
            "faq_page": child(FAQPage),
            "topics": Topic.choices,
            "news_index": news_index,
            "news": list(news_index.get_posts()[:4]) if news_index else [],
            "articles_index": articles_index,
            "articles": list(articles_index.get_posts()[:8]) if articles_index else [],
            "video_index": video_index,
            "videos": videos if video_index is not None else [],
        }

    def get_context(self, request: Any, *args: Any, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context(request, *args, **kwargs)
        context.update(self.get_landing_feeds())
        context["sections"] = self.get_sections()
        context["quick_checks"] = self.get_quick_checks(request)
        context["directory_url"] = self.get_directory_url()
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
