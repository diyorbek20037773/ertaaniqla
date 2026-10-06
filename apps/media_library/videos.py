"""«Videoroliklar» list (design 2026-10, «Bosh sahifa» frame 6): every ready `Video` snippet as a
card grid with the topic filter, plus a watch page per video at `<list>/<id>/`.
`/uz/videoroliklar/` `/ru/video/`. Videos are added in the CMS under Snippets → Videos.
"""

from __future__ import annotations

from typing import Any

from django.core.paginator import Paginator
from django.db import models
from django.http import Http404
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel
from wagtail.contrib.routable_page.models import RoutablePageMixin, path
from wagtail.fields import StreamField
from wagtail.models import Page

from apps.articles.blocks import IntroBlock, stream_plain_text
from apps.core.models import BasePage, Topic, topic_from_request

PAGE_SIZE = 12


def ready_videos(topic: str = "") -> models.QuerySet[Any]:
    from apps.media_library.models import Video, VideoStatus

    videos = Video.objects.filter(status=VideoStatus.READY).select_related("poster")
    return videos.filter(topic=topic) if topic else videos


class VideoIndexPage(RoutablePageMixin, BasePage):
    intro = StreamField(IntroBlock(), blank=True, verbose_name=_("intro"))

    content_panels = [*Page.content_panels, FieldPanel("intro")]
    parent_page_types = ["home.HomePage"]
    subpage_types: list[str] = []
    template = "media_library/video_index_page.html"

    class Meta:
        verbose_name = _("videos list")

    def get_body_text(self) -> str:
        return stream_plain_text(self.intro)

    def get_context(self, request: Any, *args: Any, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context(request, *args, **kwargs)
        topic = topic_from_request(request)
        context["topic"] = topic
        context["topics"] = Topic.choices
        videos = Paginator(ready_videos(topic), PAGE_SIZE).get_page(request.GET.get("page"))
        self.add_watch_urls(videos)
        context["videos"] = videos
        return context

    def add_watch_urls(self, videos: Any) -> None:
        for video in videos:
            video.watch_url = f"{self.url}{video.pk}/"

    @path("")
    def index_route(self, request: Any, *args: Any, **kwargs: Any) -> Any:
        return self.render(request)

    @path("<int:video_id>/")
    def watch(self, request: Any, video_id: int) -> Any:
        video = ready_videos().filter(pk=video_id).first()
        if video is None:
            raise Http404
        context = self.get_context(request)
        context["video"] = video
        context["more"] = list(ready_videos(video.topic).exclude(pk=video.pk)[:3])
        self.add_watch_urls(context["more"])
        return TemplateResponse(request, "media_library/video_watch.html", context)
