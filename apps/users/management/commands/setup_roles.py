"""Create/refresh the CMS roles (Editor, Medical Reviewer, Admin) and the "Medical review"
workflow. Idempotent; also runs automatically after `migrate`."""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create the CMS groups, their permissions and the medical review workflow."

    def handle(self, *args: Any, **options: Any) -> None:
        from wagtail.models import GroupPagePermission

        from apps.users.roles import ensure_permissions_exist, ensure_roles

        ensure_permissions_exist()
        groups = ensure_roles()
        for name, group in groups.items():
            self.stdout.write(
                f"{name}: {group.permissions.count()} permission(s), "
                f"{GroupPagePermission.objects.filter(group=group).count()} page permission(s), "
                f"{group.user_set.count()} member(s)"
            )
        self.stdout.write(self.style.SUCCESS("roles and workflow are up to date"))
