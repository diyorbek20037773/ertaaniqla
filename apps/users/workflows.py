"""Finish action of the moderation workflow (settings.WAGTAIL_FINISH_WORKFLOW_ACTION).

Wagtail's default action publishes the latest revision. We do the same, but when the workflow
contained an approved `MedicalReviewTask`, the published revision first gets the review stamp:
`medically_verified=True`, `last_reviewed_by=<approving doctor>`, `last_reviewed_at=<today>`.
Those fields are not editable in the page form, so this is the only way to get the badge.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.utils import timezone

if TYPE_CHECKING:
    from wagtail.models import TaskState

# NB: this module is imported by wagtail.models itself (WorkflowState.on_finish), so every
# wagtail/app model import must stay inside the functions.


def latest_medical_approval(workflow_state: Any) -> TaskState | None:
    from wagtail.models import TaskState

    from apps.users.models import MedicalReviewTask

    return (
        TaskState.objects.filter(
            workflow_state=workflow_state,
            status=TaskState.STATUS_APPROVED,
            task__in=MedicalReviewTask.objects.all(),
            finished_by__isnull=False,
        )
        .select_related("finished_by")
        .order_by("-finished_at")
        .first()
    )


def publish_with_medical_review(workflow_state: Any, user: Any = None) -> None:
    from apps.core.models import BasePage

    obj = workflow_state.content_object
    revision = obj.get_latest_revision()
    approval = latest_medical_approval(workflow_state)
    if approval is not None:
        # content_object is the base `Page`; the revision object is the specific page class
        page = revision.as_object()
        if isinstance(page, BasePage):
            reviewer = approval.finished_by
            page.medically_verified = True
            page.last_reviewed_by = reviewer
            page.last_reviewed_at = timezone.localdate()
            revision = page.save_revision(user=reviewer, clean=False, log_action=False)
    # completing the workflow is the authorisation: reviewers hold no publish permission
    revision.publish(user=user, skip_permission_checks=True)
