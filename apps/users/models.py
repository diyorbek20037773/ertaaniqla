"""CMS users. Roles are Wagtail groups (Editor / Medical Reviewer / Admin, created in M7)."""

from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


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
