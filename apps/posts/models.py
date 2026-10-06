"""News and articles («Yangiliklar», «Maqolalar» — design 2026-10, «Bosh sahifa» frames 3–7).

`PostIndexPage` lists its `PostPage` children newest first with the topic filter pills
(«Barchasi / Ko'krak bezi saratoni / Bachadon bo'yni saratoni / Bolalar saratoni»). One model
pair serves both lists: the index's `kind` picks the card layout. Editors add a post in the CMS
under the right index — nothing else to configure.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.paginator import Paginator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.fields import StreamField
from wagtail.models import Page
from wagtail.search import index

from apps.articles.blocks import ArticleBodyBlock, IntroBlock, stream_plain_text
from apps.core.models import BasePage, Topic, topic_from_request

PAGE_SIZE = 12


class PostKind(models.TextChoices):
    NEWS = "news", _("News")
    ARTICLES = "articles", _("Articles")


class PostIndexPage(BasePage):
    """`/uz/yangiliklar/`, `/uz/maqolalar/` (ru: `/ru/novosti/`, `/ru/stati/`)."""

    kind = models.CharField(
        _("list type"), max_length=16, choices=PostKind.choices, default=PostKind.NEWS
    )
    intro = StreamField(IntroBlock(), blank=True, verbose_name=_("intro"))

    content_panels = [*Page.content_panels, FieldPanel("kind"), FieldPanel("intro")]
    parent_page_types = ["home.HomePage"]
    subpage_types = ["posts.PostPage"]
    template = "posts/post_index_page.html"

    class Meta:
        verbose_name = _("news / articles list")

    def get_body_text(self) -> str:
        return stream_plain_text(self.intro)

    def get_posts(self, topic: str = "") -> models.QuerySet[PostPage]:
        posts = PostPage.objects.child_of(self).live().select_related("image")
        if topic:
            posts = posts.filter(topic=topic)
        return posts.order_by("-date", "-first_published_at")

    def get_context(self, request: Any, *args: Any, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context(request, *args, **kwargs)
        topic = topic_from_request(request)
        paginator = Paginator(self.get_posts(topic), PAGE_SIZE)
        context["topic"] = topic
        context["topics"] = Topic.choices
        context["posts"] = paginator.get_page(request.GET.get("page"))
        return context


class PostPage(BasePage):
    """One news item or article: topic chip, date, picture, summary, body."""

    topic = models.CharField(_("topic"), max_length=16, choices=Topic.choices, db_index=True)
    date = models.DateField(_("date"), default=timezone.localdate, db_index=True)
    image = models.ForeignKey(
        settings.WAGTAILIMAGES_IMAGE_MODEL,
        verbose_name=_("picture"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    summary = models.CharField(
        _("summary"),
        max_length=300,
        blank=True,
        help_text=_("Two lines shown on the card (articles) and in search results."),
    )
    body = StreamField(ArticleBodyBlock(), blank=True, verbose_name=_("body"))

    content_panels = [
        *Page.content_panels,
        MultiFieldPanel(
            [FieldPanel("topic"), FieldPanel("date"), FieldPanel("image")], heading=_("Card")
        ),
        FieldPanel("summary"),
        FieldPanel("body"),
    ]
    search_fields = [
        *Page.search_fields,
        index.SearchField("summary", boost=2),
        index.SearchField("body"),
        index.AutocompleteField("title"),
        index.FilterField("topic"),
    ]
    parent_page_types = ["posts.PostIndexPage"]
    subpage_types: list[str] = []
    template = "posts/post_page.html"

    class Meta:
        verbose_name = _("news item / article")
        verbose_name_plural = _("news and articles")
        ordering = ["-date"]

    jsonld_article = True

    def get_body_text(self) -> str:
        return f"{self.summary} {stream_plain_text(self.body)}"

    @property
    def kind(self) -> str:
        parent = self.get_parent()
        return str(getattr(parent.specific, "kind", PostKind.NEWS)) if parent else PostKind.NEWS
