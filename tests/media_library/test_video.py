"""`Video` snippet validation and helpers (fields per spec §4.3; transcoding arrives in M3)."""

from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile

from apps.media_library.models import Video, VideoKind, VideoSource, VideoStatus

pytestmark = pytest.mark.django_db


def test_upload_requires_file() -> None:
    video = Video(title="x", source=VideoSource.UPLOAD)
    with pytest.raises(ValidationError) as exc:
        video.full_clean()
    assert "file" in exc.value.message_dict


def test_external_requires_matching_url() -> None:
    video = Video(title="x", source=VideoSource.YOUTUBE, external_url="")
    with pytest.raises(ValidationError):
        video.full_clean()
    video.external_url = "https://www.tiktok.com/@a/video/1"
    with pytest.raises(ValidationError) as exc:
        video.full_clean()
    assert "external_url" in exc.value.message_dict


def test_external_video_is_ready_immediately() -> None:
    video = Video(
        title="Doctor talk",
        source=VideoSource.TELEGRAM,
        external_url="https://t.me/ertaaniqla/1",
        kind=VideoKind.SHORT_VERTICAL,
    )
    video.full_clean()
    video.save()
    assert video.status == VideoStatus.READY
    assert video.is_external and video.is_ready and video.is_vertical
    assert str(video) == "Doctor talk"


def test_upload_stays_uploaded_and_rendition_helpers() -> None:
    video = Video(title="raw", source=VideoSource.UPLOAD)
    video.file.save("sample.mp4", ContentFile(b"\x00\x00"), save=False)
    video.full_clean()
    video.save()
    assert video.status == VideoStatus.UPLOADED
    assert video.rendition_url("720p") == ""
    video.renditions = {"720p": {"url": "/media/videos/720.mp4"}}
    assert video.rendition_url("720p") == "/media/videos/720.mp4"
    assert video.subtitles_for("ru") == video.subtitles_ru
    assert video.subtitles_for("uz") == video.subtitles_uz
    assert not video.is_external


@pytest.mark.django_db
def test_russian_title_on_the_russian_site(seeded, client) -> None:
    """D-095: /ru/ shows `title_ru` once an editor filled it; /uz/ (and /oz/) keep the title; an
    empty `title_ru` falls back to the title. The YouTube sync never writes `title_ru`."""
    video = Video.objects.create(
        title="Mammografiya haqida",
        title_ru="О маммографии",
        source=VideoSource.YOUTUBE,
        external_url="https://www.youtube.com/watch?v=AAAAAAAAAAA",
        status=VideoStatus.READY,
    )
    ru = client.get("/ru/video/").content.decode()
    assert "О маммографии" in ru and "Mammografiya haqida" not in ru
    watch = client.get(f"/ru/video/{video.pk}/").content.decode()
    assert "<title>О маммографии" in watch
    assert "Mammografiya haqida" in client.get("/uz/videoroliklar/").content.decode()
    video.title_ru = ""
    video.save()
    assert "Mammografiya haqida" in client.get("/ru/video/").content.decode()


@pytest.mark.django_db
def test_watch_page_describes_the_video(seeded, client) -> None:
    """A shared /ru/video/<id>/ link shows the video, not the list: og:title, canonical and the
    language switch name this video; the JSON-LD is its VideoObject."""
    import json
    import re

    video = Video.objects.create(
        title="Mammografiya haqida",
        title_ru="О маммографии",
        source=VideoSource.YOUTUBE,
        external_url="https://www.youtube.com/watch?v=AAAAAAAAAAA",
        status=VideoStatus.READY,
    )
    html = client.get(f"/ru/video/{video.pk}/").content.decode()
    assert '<meta property="og:title" content="О маммографии">' in html
    canonical = re.search(r'<link rel="canonical" href="([^"]+)"', html)
    assert canonical is not None and canonical.group(1).endswith(f"/ru/video/{video.pk}/")
    assert re.search(rf'hreflang="uz" href="[^"]*/uz/videoroliklar/{video.pk}/"', html)
    graph = json.loads(re.search(r'application/ld\+json"[^>]*>(.*?)</script>', html, re.S)[1])
    items = graph.get("@graph", [graph])
    [video_ld] = [i for i in items if i.get("@type") == "VideoObject"]
    assert video_ld["name"] == "О маммографии"
    assert not [i for i in items if i.get("@type") == "MedicalWebPage"]  # not the list's page
    video.transcript = "<p>Mammografiya &amp; UZI.</p><p>Keyingi qadam</p>"
    video.save()
    html = client.get(f"/uz/videoroliklar/{video.pk}/").content.decode()
    assert (
        '<meta property="og:description" content="Mammografiya &amp; UZI. Keyingi qadam">' in html
    )
    listing = client.get("/ru/video/").content.decode()  # the list keeps its own canonical
    assert re.search(r'<link rel="canonical" href="[^"]*/ru/video/">', listing)
