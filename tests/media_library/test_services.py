"""Upload safety (spec §8): MIME sniffing, EXIF/GPS stripping, VTT check; transcoding
status machine (failure path without ffmpeg, integration path with ffmpeg)."""

from __future__ import annotations

import io
import shutil
import subprocess
from pathlib import Path

import pytest
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image

from apps.media_library import services
from apps.media_library.models import PortalDocument, PortalImage, Video, VideoSource, VideoStatus

pytestmark = pytest.mark.django_db


def jpeg_with_gps() -> bytes:
    image = Image.new("RGB", (40, 30), (10, 20, 30))
    exif = Image.Exif()
    exif[0x0112] = 6  # orientation: rotate 90
    exif[0x010F] = "TestCam"  # Make
    exif[0x013B] = "Somebody"  # Artist — personal data that must never reach the public
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", exif=exif.tobytes())
    return buffer.getvalue()


def test_sniff_mime_and_validate_upload() -> None:
    pdf = SimpleUploadedFile("x.pdf", b"%PDF-1.4 test", content_type="application/pdf")
    assert services.sniff_mime(pdf) == "application/pdf"
    services.validate_upload(pdf, frozenset({"application/pdf"}), 1024, "Doc")
    html = SimpleUploadedFile("x.pdf", b"<html><body>hi</body></html>")
    with pytest.raises(ValidationError):
        services.validate_upload(html, frozenset({"application/pdf"}), 1024, "Doc")
    with pytest.raises(ValidationError):
        services.validate_upload(pdf, frozenset({"application/pdf"}), 4, "Doc")


def test_document_clean_rejects_mismatched_content() -> None:
    doc = PortalDocument(title="fake", file=SimpleUploadedFile("fake.pdf", b"<html>x</html>"))
    with pytest.raises(ValidationError):
        doc.full_clean()
    ok = PortalDocument(title="real", file=SimpleUploadedFile("real.pdf", b"%PDF-1.4 x"))
    ok.full_clean()


def test_validate_vtt() -> None:
    services.validate_vtt(SimpleUploadedFile("a.vtt", b"WEBVTT\n\n00:00.000 --> 00:01.000\nHi"))
    services.validate_vtt(SimpleUploadedFile("a.vtt", "﻿WEBVTT\n".encode()))
    with pytest.raises(ValidationError):
        services.validate_vtt(SimpleUploadedFile("a.vtt", b"1\n00:00:00,000 --> 00:00:01,000\nHi"))


def test_video_clean_validates_subtitles_and_mime() -> None:
    video = Video(title="v", source=VideoSource.UPLOAD)
    video.file = SimpleUploadedFile("v.mp4", b"<html>not a video</html>")
    video.subtitles_uz = SimpleUploadedFile("s.vtt", b"not vtt")
    with pytest.raises(ValidationError) as exc:
        video.full_clean()
    assert {"file", "subtitles_uz"} <= set(exc.value.message_dict)
    external = Video(title="e", source=VideoSource.YOUTUBE, external_url="https://youtu.be/abcdefg")
    external.subtitles_ru = SimpleUploadedFile("s.vtt", b"nope")
    with pytest.raises(ValidationError) as exc:
        external.full_clean()
    assert "subtitles_ru" in exc.value.message_dict


def test_strip_exif_removes_gps_and_applies_orientation() -> None:
    upload = SimpleUploadedFile("photo.jpg", jpeg_with_gps(), content_type="image/jpeg")
    cleaned = services.strip_exif(upload, "photo.jpg")
    assert cleaned is not None
    image = Image.open(io.BytesIO(cleaned.read()))
    assert not image.getexif()
    assert image.size == (30, 40)  # rotated per orientation tag
    assert services.strip_exif(SimpleUploadedFile("x.svg", b"<svg/>"), "x.svg") is None


def test_portal_image_upload_is_stripped_on_save() -> None:
    image = PortalImage(title="gps")
    image.file = SimpleUploadedFile("gps.jpg", jpeg_with_gps(), content_type="image/jpeg")
    image.width, image.height = 40, 30
    image.save()
    image.refresh_from_db()
    with image.file.open("rb") as fh:
        stored = Image.open(io.BytesIO(fh.read()))
    assert not stored.getexif()


@override_settings(FFMPEG_BINARY="/definitely/not/here/ffmpeg")
def test_transcode_without_ffmpeg_marks_failed() -> None:
    video = Video(title="raw", source=VideoSource.UPLOAD)
    video.file.save("raw.mp4", ContentFile(b"\x00" * 10), save=False)
    Video.objects.bulk_create([video])  # bypass the post_save signal for a controlled run
    video = Video.objects.get(title="raw")
    services.transcode_video(video)
    video.refresh_from_db()
    assert video.status == VideoStatus.FAILED
    assert "ffmpeg" in video.processing_error
    assert not services.ffmpeg_available()


@override_settings(FFMPEG_BINARY="/definitely/not/here/ffmpeg", CELERY_TASK_ALWAYS_EAGER=True)
def test_signal_enqueues_task_on_upload(django_capture_on_commit_callbacks) -> None:
    video = Video(title="signal", source=VideoSource.UPLOAD)
    video.file.save("signal.mp4", ContentFile(b"\x00" * 10), save=False)
    with django_capture_on_commit_callbacks(execute=True):
        video.save()
    video.refresh_from_db()
    assert video.status == VideoStatus.FAILED  # task ran eagerly and recorded the failure


def test_task_ignores_external_videos() -> None:
    from apps.media_library.tasks import transcode_video

    video = Video.objects.create(
        title="ext", source=VideoSource.YOUTUBE, external_url="https://youtu.be/abcdefg"
    )
    transcode_video(video.pk)
    transcode_video(10**9)
    video.refresh_from_db()
    assert video.status == VideoStatus.UPLOADED or video.status == VideoStatus.READY


# ---------------------------------------------------------------------------
# integration: real ffmpeg (docker image / CI)
# ---------------------------------------------------------------------------
@pytest.mark.integration
@pytest.mark.skipif(not services.ffmpeg_available(), reason="ffmpeg not installed on this host")
def test_transcode_two_second_sample(tmp_path: Path) -> None:
    sample = tmp_path / "sample.mp4"
    subprocess.run(
        [
            shutil.which(services.ffmpeg_binary()) or "ffmpeg",
            "-y",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc=duration=2:size=1280x720:rate=10",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=2",
            "-shortest",
            "-pix_fmt",
            "yuv420p",
            str(sample),
        ],
        check=True,
    )
    video = Video(title="sample", source=VideoSource.UPLOAD)
    video.file.save("sample.mp4", ContentFile(sample.read_bytes()), save=False)
    Video.objects.bulk_create([video])
    video = Video.objects.get(title="sample")
    services.transcode_video(video)
    video.refresh_from_db()
    assert video.status == VideoStatus.READY, video.processing_error
    assert video.duration == 2
    assert set(video.renditions) == {"720p", "480p"}
    assert video.renditions["480p"]["height"] == 480
    assert video.renditions["720p"]["height"] == 720
    assert video.rendition_url("480p").endswith("480p.mp4")
    assert video.poster is not None and video.poster.is_decorative
