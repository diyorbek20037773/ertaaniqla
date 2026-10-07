from __future__ import annotations

from celery import shared_task
from django.conf import settings
from django.utils import translation
from django.utils.translation import gettext as _


@shared_task(name="feedback.notify_moderators", ignore_result=True)
def notify_moderators(submission_id: int) -> None:
    from apps.core.mail import send_email
    from apps.feedback.models import FeedbackSubmission

    submission = FeedbackSubmission.objects.filter(pk=submission_id).first()
    if submission is None:
        return
    # no message text and no contact in the e-mail (either may hold personal data) — moderators
    # read it in the CMS
    with translation.override(settings.LANGUAGE_CODE):
        kind = str(submission.get_kind_display())
        send_email(
            subject=_("[Erta aniqla] New feedback #%(id)s (%(kind)s)")
            % {"id": submission.pk, "kind": kind},
            template="new_feedback",
            context={
                "submission_id": submission.pk,
                "kind": kind,
                "language": submission.language,
                "page_url": submission.page_url,
                "cms_url": (
                    f"{settings.WAGTAILADMIN_BASE_URL}/{settings.CMS_URL_PREFIX}"
                    f"/snippets/feedback/feedbacksubmission/edit/{submission.pk}/"
                ),
            },
            to=list(settings.MODERATION_EMAILS),
        )


@shared_task(name="feedback.purge_old_submissions", ignore_result=True)
def purge_old_submissions() -> int:
    from apps.feedback.services import purge_old_submissions as run

    return run()
