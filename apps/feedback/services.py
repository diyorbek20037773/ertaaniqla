from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.utils import timezone
from django.utils.translation import get_language

from apps.feedback.models import FeedbackSubmission

logger = logging.getLogger("ertaaniqla.feedback")


def submit_feedback(form: Any, request: Any) -> FeedbackSubmission:
    submission: FeedbackSubmission = form.save(commit=False)
    submission.language = get_language() or settings.LANGUAGE_CODE
    submission.user_agent = str(request.META.get("HTTP_USER_AGENT", ""))[:300]
    submission.save()
    logger.info("feedback %s submitted (kind=%s)", submission.pk, submission.kind)
    return submission


def purge_old_submissions(now: Any = None) -> int:
    """Delete submissions older than the retention window (spec §8: 180 days)."""
    now = now or timezone.now()
    cutoff = now - timedelta(days=settings.PII_RETENTION_FEEDBACK_DAYS)
    deleted, _ = FeedbackSubmission.objects.filter(created_at__lte=cutoff).delete()
    if deleted:
        logger.info("purged %d feedback submission(s)", deleted)
    return int(deleted)
