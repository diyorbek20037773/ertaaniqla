"""FAQ business logic: submission, moderator notification, retention purge."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.translation import get_language

from apps.faq.models import Question, QuestionStatus

logger = logging.getLogger("ertaaniqla.faq")


def submit_question(form: Any, request: Any) -> Question:
    question: Question = form.save(commit=False)
    question.language = get_language() or settings.LANGUAGE_CODE
    question.save()
    from apps.faq.tasks import notify_moderators

    transaction.on_commit(lambda: notify_moderators.delay(question.pk))
    logger.info("question %s submitted (section=%s)", question.pk, question.section)
    return question


def purge_contacts(now: Any = None) -> int:
    """Blank the encrypted contact of answered/published/rejected questions older than the
    retention window (spec §8: 90 days after the answer). Returns the number purged."""
    now = now or timezone.now()
    cutoff = now - timedelta(days=settings.PII_RETENTION_QUESTION_CONTACT_DAYS)
    answered = Question.objects.filter(
        status__in=[QuestionStatus.ANSWERED, QuestionStatus.PUBLISHED],
        answered_at__lte=cutoff,
        contact_purged_at__isnull=True,
    )
    rejected = Question.objects.filter(
        status=QuestionStatus.REJECTED, updated_at__lte=cutoff, contact_purged_at__isnull=True
    )
    count = 0
    for question in list(answered) + list(rejected):
        question.purge_contact()
        count += 1
    if count:
        logger.info("purged %d question contact(s)", count)
    return count
