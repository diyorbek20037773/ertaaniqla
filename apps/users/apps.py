from typing import Any

from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.utils.translation import gettext_lazy as _


def _ensure_roles_after_migrate(sender: Any, using: str = "default", **kwargs: Any) -> None:
    from django.db import connections

    from apps.users.roles import ensure_permissions_exist, ensure_roles

    tables = set(connections[using].introspection.table_names())
    if not {"wagtailcore_workflowpage", "users_medicalreviewtask"} <= tables:
        return  # partial migration (e.g. migrating an app backwards)
    ensure_permissions_exist(using=using)
    ensure_roles()


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.users"
    verbose_name = _("Users")

    def ready(self) -> None:
        from apps.users import otp

        otp.install()
        post_migrate.connect(
            _ensure_roles_after_migrate, sender=self, dispatch_uid="users.ensure_roles"
        )
