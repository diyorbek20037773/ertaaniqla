"""Enqueue Celery tasks after the transaction commits, without failing the request (D-075).

Side effects (moderator e-mail, OG image, renditions, transcoding) must never turn a saved
question or a publish into a 500. With `CELERY_TASK_ALWAYS_EAGER` (the Railway demo host has no
worker) `.delay()` runs the task inline and `CELERY_TASK_EAGER_PROPAGATES` re-raises its error
— e.g. an unreachable SMTP server. The error is logged (and reaches Sentry) instead.
"""

from __future__ import annotations

import logging
from typing import Any

from django.db import transaction

logger = logging.getLogger("ertaaniqla.queue")


def _safe_delay(task: Any, *args: Any) -> None:
    try:
        task.delay(*args)
    except Exception:
        logger.exception("task %s%r failed to enqueue or run", task.name, args)


def enqueue_on_commit(task: Any, *args: Any) -> None:
    transaction.on_commit(lambda: _safe_delay(task, *args))
