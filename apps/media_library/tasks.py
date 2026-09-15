"""Celery tasks for media (queue `media`, see CELERY_TASK_ROUTES)."""

from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger("ertaaniqla.media")


@shared_task(name="media_library.transcode_video", ignore_result=True)
def transcode_video(video_id: int) -> None:
    from apps.media_library.models import Video, VideoSource
    from apps.media_library.services import transcode_video as run

    video = Video.objects.filter(pk=video_id).first()
    if video is None or video.source != VideoSource.UPLOAD or not video.file:
        logger.info("transcode_video(%s): nothing to do", video_id)
        return
    run(video)
