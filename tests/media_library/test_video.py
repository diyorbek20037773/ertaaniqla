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
