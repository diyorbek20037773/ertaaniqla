"""CMS users, roles (Wagtail groups, see `apps.users.roles`) and the medical review task."""

from __future__ import annotations

from typing import Any

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.models import AbstractGroupApprovalTask, TaskState


class User(AbstractUser):
    organisation = models.CharField(
        _("organisation"),
        max_length=200,
        blank=True,
        help_text=_("e.g. RONC, Mother & Child Health Centre — shown on the 'verified by' badge"),
    )
    job_title = models.CharField(_("job title"), max_length=200, blank=True)

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        ordering = ["username"]

    def __str__(self) -> str:
        return self.get_full_name() or self.username

    @property
    def display_name(self) -> str:
        return str(self)


class MedicalReviewTask(AbstractGroupApprovalTask):
    """Workflow step approved by a doctor (spec §1.1 "Medical reviewer").

    Unlike Wagtail's `GroupApprovalTask`, only members of the chosen groups may act — a superuser
    who is not a reviewer cannot approve, so the "Verified by a doctor" badge always names a real
    reviewer. On workflow completion `apps.users.workflows.publish_with_medical_review` stamps the
    page with the approving reviewer and the date.
    """

    def _is_reviewer(self, user: Any) -> bool:
        return bool(user.is_authenticated and self._user_in_groups(user))

    def user_can_access_editor(self, obj: Any, user: Any) -> bool:
        return self._is_reviewer(user)

    def locked_for_user(self, obj: Any, user: Any) -> bool:
        return not (user.is_superuser or self._is_reviewer(user))

    def get_actions(self, obj: Any, user: Any) -> list[tuple[str, Any, bool]]:
        if not self._is_reviewer(user):
            return []
        return [
            ("reject", _("Request changes"), True),
            ("approve", _("Approve as medically verified"), False),
            ("approve", _("Approve with comment"), True),
        ]

    def get_task_states_user_can_moderate(self, user: Any, **kwargs: Any) -> Any:
        if self._is_reviewer(user):
            return self.task_states.filter(status=TaskState.STATUS_IN_PROGRESS)
        return TaskState.objects.none()

    @classmethod
    def get_description(cls) -> Any:
        return _(
            "Members of the chosen groups (doctors) approve the page; approval marks it as "
            "medically verified with the reviewer's name and date."
        )

    class Meta:
        verbose_name = _("medical review task")
        verbose_name_plural = _("medical review tasks")
