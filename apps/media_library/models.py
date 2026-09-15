"""Custom Wagtail image and document models and the `Video` snippet (spec §4.3).

The image/document models exist since M0 so `WAGTAILIMAGES_IMAGE_MODEL` /
`WAGTAILDOCS_DOCUMENT_MODEL` never have to change. `Video` carries every field the spec lists;
the ffmpeg transcoding task, VTT handling and galleries arrive in M3 (the status machine and
renditions JSON are already here so the `video` block can be built and tested now).
"""

from __future__ import annotations

import re
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.documents.models import AbstractDocument, Document
from wagtail.fields import RichTextField
from wagtail.images.models import AbstractImage, AbstractRendition, Image
from wagtail.search import index
from wagtail.snippets.models import register_snippet

from apps.core.models import TimeStampedModel


class PortalImage(AbstractImage):
    # alt text is required for accessibility (spec §9); Wagtail 7 keeps `description` for that
    credit = models.CharField(_("credit / source"), max_length=255, blank=True)
    is_decorative = models.BooleanField(
        _("decorative (no alt text needed)"),
        default=False,
        help_text=_("Only for purely decorative images. Content images must describe themselves."),
    )

    admin_form_fields = (*Image.admin_form_fields, "credit", "is_decorative")

    class Meta(AbstractImage.Meta):
        verbose_name = _("image")
        verbose_name_plural = _("images")

    @property
    def alt_text(self) -> str:
        if self.is_decorative:
            return ""
        return str(self.description or self.title)


class PortalRendition(AbstractRendition):
    image = models.ForeignKey(PortalImage, on_delete=models.CASCADE, related_name="renditions")

    class Meta(AbstractRendition.Meta):
        unique_together = (("image", "filter_spec", "focal_point_key"),)


class PortalDocument(AbstractDocument):
    is_private = models.BooleanField(
        _("private (consent forms etc.)"),
        default=False,
        help_text=_("Private documents are served only to logged-in CMS users."),
    )
    description = models.TextField(_("description"), blank=True)

    admin_form_fields = (*Document.admin_form_fields, "description", "is_private")

    class Meta(AbstractDocument.Meta):
        verbose_name = _("document")
        verbose_name_plural = _("documents")

    def clean(self) -> None:
        super().clean()
        if self.file and getattr(self.file, "_committed", True) is False:
            from apps.media_library.services import DOCUMENT_MIME_TYPES, validate_upload

            extension = self.file.name.rsplit(".", 1)[-1].lower() if "." in self.file.name else ""
            allowed = DOCUMENT_MIME_TYPES.get(extension)
            if allowed is not None:
                validate_upload(
                    self.file, allowed, settings.MAX_DOCUMENT_UPLOAD_BYTES, str(_("Document"))
                )


# ---------------------------------------------------------------------------
# Video snippet
# ---------------------------------------------------------------------------
class VideoKind(models.TextChoices):
    LONG = "long", _("Long video (doctor interview, lecture)")
    SHORT_VERTICAL = "short_vertical", _("Short vertical video (mobilograph, social media)")


class VideoSource(models.TextChoices):
    UPLOAD = "upload", _("Uploaded file")
    YOUTUBE = "youtube", _("YouTube")
    TELEGRAM = "telegram", _("Telegram")
    INSTAGRAM = "instagram", _("Instagram")
    TIKTOK = "tiktok", _("TikTok")


class VideoStatus(models.TextChoices):
    UPLOADED = "uploaded", _("Uploaded")
    PROCESSING = "processing", _("Processing")
    READY = "ready", _("Ready")
    FAILED = "failed", _("Failed")


_PROVIDER_PATTERNS: dict[str, re.Pattern[str]] = {
    VideoSource.YOUTUBE: re.compile(r"^https://(www\.)?(youtube\.com|youtu\.be)/"),
    VideoSource.TELEGRAM: re.compile(r"^https://t\.me/"),
    VideoSource.INSTAGRAM: re.compile(r"^https://(www\.)?instagram\.com/"),
    VideoSource.TIKTOK: re.compile(r"^https://(www\.)?tiktok\.com/"),
}


def video_upload_path(instance: Video, filename: str) -> str:
    return f"videos/source/{filename}"


def subtitle_upload_path(instance: Video, filename: str) -> str:
    return f"videos/subtitles/{filename}"


@register_snippet
class Video(index.Indexed, TimeStampedModel):
    """A doctor video or a short vertical social video (spec §4.3 `Video`)."""

    title = models.CharField(_("title"), max_length=200)
    kind = models.CharField(
        _("kind"), max_length=16, choices=VideoKind.choices, default=VideoKind.LONG
    )
    source = models.CharField(
        _("source"), max_length=16, choices=VideoSource.choices, default=VideoSource.UPLOAD
    )
    file = models.FileField(
        _("video file"),
        upload_to=video_upload_path,
        blank=True,
        help_text=_("Original upload. Never served directly — transcoded renditions are."),
    )
    external_url = models.URLField(_("external URL"), blank=True)
    poster = models.ForeignKey(
        settings.WAGTAILIMAGES_IMAGE_MODEL,
        verbose_name=_("poster image"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    duration = models.PositiveIntegerField(_("duration (seconds)"), null=True, blank=True)
    doctor_name = models.CharField(_("doctor's name"), max_length=200, blank=True)
    doctor_org = models.CharField(_("doctor's organisation"), max_length=200, blank=True)
    transcript = RichTextField(_("transcript"), blank=True, editor="minimal")
    subtitles_uz = models.FileField(
        _("subtitles (uz, VTT)"), upload_to=subtitle_upload_path, blank=True
    )
    subtitles_ru = models.FileField(
        _("subtitles (ru, VTT)"), upload_to=subtitle_upload_path, blank=True
    )
    status = models.CharField(
        _("status"),
        max_length=16,
        choices=VideoStatus.choices,
        default=VideoStatus.UPLOADED,
        db_index=True,
    )
    renditions = models.JSONField(_("renditions"), default=dict, blank=True)
    processing_error = models.TextField(_("processing error"), blank=True)

    panels = [
        FieldPanel("title"),
        MultiFieldPanel([FieldPanel("kind"), FieldPanel("source")], heading=_("Type")),
        MultiFieldPanel(
            [FieldPanel("file"), FieldPanel("external_url"), FieldPanel("poster")],
            heading=_("Media"),
        ),
        MultiFieldPanel(
            [FieldPanel("doctor_name"), FieldPanel("doctor_org"), FieldPanel("duration")],
            heading=_("Speaker"),
        ),
        MultiFieldPanel(
            [FieldPanel("transcript"), FieldPanel("subtitles_uz"), FieldPanel("subtitles_ru")],
            heading=_("Accessibility"),
        ),
        MultiFieldPanel(
            [FieldPanel("status", read_only=True), FieldPanel("processing_error", read_only=True)],
            heading=_("Processing"),
        ),
    ]

    search_fields = [
        index.SearchField("title", boost=2),
        index.SearchField("doctor_name"),
        index.SearchField("transcript"),
        index.FilterField("kind"),
        index.FilterField("status"),
    ]

    class Meta:
        verbose_name = _("video")
        verbose_name_plural = _("videos")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title

    def clean(self) -> None:
        super().clean()
        from apps.media_library.services import (
            SUBTITLE_MIME_TYPES,
            VIDEO_MIME_TYPES,
            validate_upload,
            validate_vtt,
        )

        errors: dict[str, ValidationError] = {}
        for field_name in ("subtitles_uz", "subtitles_ru"):
            subtitle = getattr(self, field_name)
            if subtitle and getattr(subtitle, "_committed", True) is False:
                try:
                    validate_upload(subtitle, SUBTITLE_MIME_TYPES, 2 * 1024 * 1024, "VTT")
                    validate_vtt(subtitle)
                except ValidationError as exc:
                    errors[field_name] = exc
        if self.source == VideoSource.UPLOAD:
            if not self.file:
                raise ValidationError(
                    {"file": _("Upload a video file or choose an external source."), **errors}
                )
            if getattr(self.file, "_committed", True) is False:
                try:
                    validate_upload(
                        self.file,
                        VIDEO_MIME_TYPES,
                        settings.MAX_VIDEO_UPLOAD_BYTES,
                        str(_("Video")),
                    )
                except ValidationError as exc:
                    errors["file"] = exc
            if errors:
                raise ValidationError(errors)
        else:
            if errors:
                raise ValidationError(errors)
            if not self.external_url:
                raise ValidationError({"external_url": _("An external URL is required.")})
            pattern = _PROVIDER_PATTERNS[self.source]
            if not pattern.match(self.external_url):
                raise ValidationError(
                    {"external_url": _("The URL does not belong to the selected provider.")}
                )
            # external videos need no transcoding
            if self.status == VideoStatus.UPLOADED:
                self.status = VideoStatus.READY

    @property
    def is_external(self) -> bool:
        return self.source != VideoSource.UPLOAD

    @property
    def is_ready(self) -> bool:
        return self.status == VideoStatus.READY

    @property
    def is_vertical(self) -> bool:
        return self.kind == VideoKind.SHORT_VERTICAL

    def rendition_url(self, name: str) -> str:
        """URL of a transcoded rendition (`720p`, `480p`), empty when missing."""
        data: dict[str, Any] = self.renditions or {}
        item = data.get(name) or {}
        return str(item.get("url", ""))

    def subtitles_for(self, language: str) -> Any:
        return self.subtitles_ru if language == "ru" else self.subtitles_uz
