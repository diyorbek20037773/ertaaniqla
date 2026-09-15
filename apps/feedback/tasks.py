from __future__ import annotations

from celery import shared_task


@shared_task(name="feedback.purge_old_submissions", ignore_result=True)
def purge_old_submissions() -> int:
    from apps.feedback.services import purge_old_submissions as run

    return run()
