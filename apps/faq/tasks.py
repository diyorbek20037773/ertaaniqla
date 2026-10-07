from __future__ import annotations

from celery import shared_task
from django.conf import settings
from django.utils import translation
from django.utils.translation import gettext as _


@shared_task(name="faq.notify_moderators", ignore_result=True)
def notify_moderators(question_id: int) -> None:
    from apps.core.mail import send_email
    from apps.faq.models import Question

    question = Question.objects.filter(pk=question_id).first()
    if question is None:
        return
    # the e-mail never contains the contact or the full text — moderators open the CMS;
    # written in the site's default language whatever page the visitor used
    with translation.override(settings.LANGUAGE_CODE):
        section = str(question.get_section_display())
        send_email(
            subject=_("[Erta aniqla] New question #%(id)s (%(section)s)")
            % {"id": question.pk, "section": section},
            template="new_question",
            context={
                "question_id": question.pk,
                "section": section,
                "language": question.language,
                "excerpt": question.text[:120],
                "cms_url": (
                    f"{settings.WAGTAILADMIN_BASE_URL}/{settings.CMS_URL_PREFIX}"
                    f"/snippets/faq/question/edit/{question.pk}/"
                ),
            },
            to=list(settings.MODERATION_EMAILS),
        )


@shared_task(name="faq.purge_contacts", ignore_result=True)
def purge_contacts() -> int:
    from apps.faq.services import purge_contacts as run

    return run()
