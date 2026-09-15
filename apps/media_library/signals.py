"""Media signals: EXIF stripping on image upload (spec §8) and transcoding on video upload."""

from __future__ import annotations

from typing import Any

from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.media_library.models import PortalImage, Video, VideoSource, VideoStatus
from apps.media_library.services import strip_exif


@receiver(pre_save, sender=PortalImage)
def _strip_image_metadata(sender: Any, instance: PortalImage, **kwargs: Any) -> None:
    file_obj = instance.file
    if not file_obj or getattr(file_obj, "_committed", True):
        # only freshly uploaded (uncommitted) files carry user metadata
        return
    cleaned = strip_exif(file_obj, file_obj.name)
    if cleaned is not None:
        width, height = instance.width, instance.height
        instance.file.save(cleaned.name, cleaned, save=False)
        # keep known dimensions if the post-save re-read from storage came back empty
        instance.width = instance.width or width
        instance.height = instance.height or height


@receiver(post_save, sender=Video)
def _enqueue_transcoding(sender: Any, instance: Video, **kwargs: Any) -> None:
    if instance.source != VideoSource.UPLOAD or not instance.file:
        return
    if instance.status != VideoStatus.UPLOADED:
        return
    from apps.media_library.tasks import transcode_video

    transaction.on_commit(lambda: transcode_video.delay(instance.pk))
