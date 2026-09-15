"""Media processing (spec §3 video, §8 uploads): ffmpeg transcoding, ffprobe metadata,
MIME validation with libmagic, EXIF stripping. Pure functions — the Celery task and the
signals are thin wrappers around these."""

from __future__ import annotations

import contextlib
import io
import json
import logging
import shutil
import subprocess  # ffmpeg is invoked with a fixed argv, never a shell
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.utils.translation import gettext_lazy as _
from PIL import Image, ImageOps

logger = logging.getLogger("ertaaniqla.media")

VIDEO_MIME_TYPES = frozenset(
    {"video/mp4", "video/quicktime", "video/x-matroska", "video/webm", "video/x-msvideo"}
)
SUBTITLE_MIME_TYPES = frozenset({"text/plain", "text/vtt", "application/octet-stream"})
DOCUMENT_MIME_TYPES: dict[str, frozenset[str]] = {
    "pdf": frozenset({"application/pdf"}),
    "docx": frozenset(
        {
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/zip",
        }
    ),
    "xlsx": frozenset(
        {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/zip"}
    ),
    "pptx": frozenset(
        {
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "application/zip",
        }
    ),
    "odt": frozenset({"application/vnd.oasis.opendocument.text", "application/zip"}),
    "txt": frozenset({"text/plain"}),
    "csv": frozenset({"text/plain", "text/csv", "application/csv"}),
    "vtt": frozenset({"text/plain", "text/vtt"}),
    "srt": frozenset({"text/plain", "application/x-subrip"}),
    "zip": frozenset({"application/zip"}),
}
RENDITIONS: dict[str, int] = {"720p": 720, "480p": 480}


# ---------------------------------------------------------------------------
# MIME / content validation
# ---------------------------------------------------------------------------
def sniff_mime(file_obj: Any) -> str:
    """MIME type from the first bytes of an uploaded file (libmagic), '' if unreadable."""
    try:
        import magic
    except ImportError:  # pragma: no cover - libmagic missing on the host
        logger.warning("python-magic unavailable; MIME sniffing skipped")
        return ""
    try:
        position = file_obj.tell()
    except (AttributeError, OSError):
        position = None
    try:
        if hasattr(file_obj, "open"):
            file_obj.open("rb")
        file_obj.seek(0)
        head = file_obj.read(4096)
    except (OSError, ValueError):
        return ""
    finally:
        if position is not None:
            with contextlib.suppress(OSError, ValueError):
                file_obj.seek(position)
    if not head:
        return ""
    return str(magic.from_buffer(head, mime=True))


def validate_upload(file_obj: Any, allowed: frozenset[str], max_bytes: int, label: str) -> None:
    """Raise ValidationError when the size or the sniffed MIME type is not acceptable."""
    size = getattr(file_obj, "size", None)
    if size is not None and size > max_bytes:
        raise ValidationError(
            _("%(label)s is too large (max %(mb)d MB).")
            % {"label": label, "mb": max_bytes // (1024 * 1024)}
        )
    mime = sniff_mime(file_obj)
    if mime and mime not in allowed:
        raise ValidationError(
            _("%(label)s content type %(mime)s is not allowed.") % {"label": label, "mime": mime}
        )


def validate_vtt(file_obj: Any) -> None:
    try:
        file_obj.seek(0)
        head = file_obj.read(16)
    except (OSError, ValueError):
        return
    if isinstance(head, bytes):
        head = head.decode("utf-8", errors="replace")
    if not head.lstrip("﻿").startswith("WEBVTT"):
        raise ValidationError(_("Subtitle files must be WebVTT (start with 'WEBVTT')."))


# ---------------------------------------------------------------------------
# EXIF stripping (GPS!) — spec §8
# ---------------------------------------------------------------------------
def strip_exif(file_obj: Any, filename: str) -> ContentFile | None:
    """Re-encode a JPEG/PNG/WebP without metadata, honouring the EXIF orientation.
    Returns a new ContentFile or None when nothing had to change (SVG, GIF, no EXIF)."""
    try:
        file_obj.seek(0)
        image = Image.open(file_obj)
        image.load()
    except (OSError, ValueError):
        return None
    fmt = (image.format or "").upper()
    if fmt not in {"JPEG", "PNG", "WEBP"}:
        return None
    has_exif = bool(image.getexif()) or "exif" in image.info or "xmp" in image.info
    if not has_exif and fmt != "JPEG":
        return None
    transposed: Image.Image = ImageOps.exif_transpose(image) or image
    clean = Image.new(transposed.mode, transposed.size)
    clean.putdata(list(transposed.getdata()))
    if fmt == "PNG" and "transparency" in transposed.info:
        clean.info["transparency"] = transposed.info["transparency"]
    buffer = io.BytesIO()
    save_kwargs: dict[str, Any] = {"format": fmt}
    if fmt == "JPEG":
        save_kwargs.update(quality=90, optimize=True)
    clean.save(buffer, **save_kwargs)
    return ContentFile(buffer.getvalue(), name=Path(filename).name)


# ---------------------------------------------------------------------------
# ffmpeg
# ---------------------------------------------------------------------------
@dataclass
class ProbeResult:
    duration: int
    width: int
    height: int

    @property
    def vertical(self) -> bool:
        return self.height > self.width


def ffmpeg_binary() -> str:
    return str(getattr(settings, "FFMPEG_BINARY", "ffmpeg"))


def ffprobe_binary() -> str:
    binary = ffmpeg_binary()
    if binary.endswith("ffmpeg.exe"):
        return binary[: -len("ffmpeg.exe")] + "ffprobe.exe"
    if binary.endswith("ffmpeg"):
        return binary[: -len("ffmpeg")] + "ffprobe"
    return "ffprobe"


def ffmpeg_available() -> bool:
    return shutil.which(ffmpeg_binary()) is not None


def _run(argv: list[str], timeout: int = 60 * 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 — fixed argv list, no shell
        argv, capture_output=True, text=True, timeout=timeout, check=False
    )


def probe(path: str) -> ProbeResult:
    result = _run(
        [
            ffprobe_binary(),
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height:format=duration",
            "-of",
            "json",
            path,
        ],
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr.strip()[:300]}")
    data = json.loads(result.stdout or "{}")
    stream = (data.get("streams") or [{}])[0]
    duration = float((data.get("format") or {}).get("duration") or 0)
    return ProbeResult(
        duration=round(duration),
        width=int(stream.get("width") or 0),
        height=int(stream.get("height") or 0),
    )


def _scale_filter(target: int, vertical: bool) -> str:
    # keep aspect ratio, never upscale, even dimensions for H.264
    if vertical:
        return f"scale='min({target},iw)':-2"
    return f"scale=-2:'min({target},ih)'"


def transcode_file(source_path: str, out_dir: Path) -> dict[str, Any]:
    """Produce 720p/480p H.264 MP4 renditions + a poster JPEG. Returns metadata."""
    info = probe(source_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    renditions: dict[str, Any] = {}
    for name, target in RENDITIONS.items():
        if (
            min(info.width, info.height)
            and target > max(info.width, info.height)
            and name != "480p"
        ):
            continue  # do not upscale tiny sources to 720p
        target_path = out_dir / f"{name}.mp4"
        result = _run(
            [
                ffmpeg_binary(),
                "-y",
                "-v",
                "error",
                "-i",
                source_path,
                "-vf",
                _scale_filter(target, info.vertical),
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "23",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                "-movflags",
                "+faststart",
                str(target_path),
            ]
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg {name} failed: {result.stderr.strip()[:300]}")
        rendition_info = probe(str(target_path))
        renditions[name] = {
            "path": str(target_path),
            "width": rendition_info.width,
            "height": rendition_info.height,
            "size": target_path.stat().st_size,
        }
    poster_path = out_dir / "poster.jpg"
    poster_time = "1" if info.duration > 1 else "0"
    result = _run(
        [
            ffmpeg_binary(),
            "-y",
            "-v",
            "error",
            "-ss",
            poster_time,
            "-i",
            source_path,
            "-frames:v",
            "1",
            "-q:v",
            "3",
            str(poster_path),
        ],
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg poster failed: {result.stderr.strip()[:300]}")
    return {"duration": info.duration, "renditions": renditions, "poster": str(poster_path)}


def transcode_video(video: Any) -> None:
    """Run the full pipeline for a `Video` instance and persist the outcome (status machine)."""
    from django.core.files.storage import default_storage

    from apps.media_library.models import PortalImage, VideoStatus

    video.status = VideoStatus.PROCESSING
    video.processing_error = ""
    video.save(update_fields=["status", "processing_error", "updated_at"])
    try:
        if not ffmpeg_available():
            raise RuntimeError(f"ffmpeg binary not found: {ffmpeg_binary()}")
        with tempfile.TemporaryDirectory(prefix="ea-video-") as tmp:
            source = Path(tmp) / "source"
            with video.file.open("rb") as src, open(source, "wb") as dst:
                shutil.copyfileobj(src, dst)
            meta = transcode_file(str(source), Path(tmp) / "out")
            stored: dict[str, Any] = {}
            for name, item in meta["renditions"].items():
                target = f"videos/renditions/{video.pk}/{name}.mp4"
                if default_storage.exists(target):
                    default_storage.delete(target)  # re-transcode overwrites, no suffixed copies
                with open(item["path"], "rb") as fh:
                    saved = default_storage.save(target, fh)
                stored[name] = {
                    "url": default_storage.url(saved),
                    "name": saved,
                    "width": item["width"],
                    "height": item["height"],
                    "size": item["size"],
                }
            if not video.poster_id:
                with Image.open(meta["poster"]) as poster_image:
                    poster_width, poster_height = poster_image.size
                with open(meta["poster"], "rb") as fh:
                    poster = PortalImage(
                        title=f"Poster: {video.title}"[:255],
                        is_decorative=True,
                        width=poster_width,
                        height=poster_height,
                    )
                    poster.file.save(
                        f"video-{video.pk}-poster.jpg", ContentFile(fh.read()), save=False
                    )
                    # Django re-reads dimensions from storage on assignment; on slow/bind-mounted
                    # storage that read can miss — keep the values we already know.
                    poster.width = poster.width or poster_width
                    poster.height = poster.height or poster_height
                    poster.save()
                video.poster = poster
            video.renditions = stored
            video.duration = meta["duration"] or video.duration
            video.status = VideoStatus.READY
    except Exception as exc:  # any failure is recorded on the video, never lost
        logger.exception("video %s transcoding failed", video.pk)
        video.status = VideoStatus.FAILED
        video.processing_error = str(exc)[:1000]
    video.save()
