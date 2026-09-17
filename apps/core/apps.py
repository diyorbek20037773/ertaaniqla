from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = _("Core")

    def ready(self) -> None:
        from apps.core import signals  # noqa: F401  (registers receivers)

        self._connect_audit()

    @staticmethod
    def _connect_audit() -> None:
        """Security audit trail receivers (apps/core/audit.py, ADR-0005)."""
        from axes.signals import user_locked_out
        from django.contrib.auth import get_user_model
        from django.contrib.auth.models import Group
        from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
        from django.db.models.signals import m2m_changed, post_delete, post_save, pre_save
        from django_otp.plugins.otp_totp.models import TOTPDevice
        from wagtail.models import GroupPagePermission, ModelLogEntry, PageLogEntry

        from apps.core import audit

        user_model = get_user_model()
        uid = "core.audit."
        user_logged_in.connect(audit.on_user_logged_in, dispatch_uid=uid + "login")
        user_logged_out.connect(audit.on_user_logged_out, dispatch_uid=uid + "logout")
        user_login_failed.connect(audit.on_user_login_failed, dispatch_uid=uid + "failed")
        user_locked_out.connect(audit.on_user_locked_out, dispatch_uid=uid + "lockout")
        pre_save.connect(audit.on_user_pre_save, sender=user_model, dispatch_uid=uid + "u_pre")
        post_save.connect(audit.on_user_post_save, sender=user_model, dispatch_uid=uid + "u_post")
        post_delete.connect(audit.on_user_deleted, sender=user_model, dispatch_uid=uid + "u_del")
        m2m_changed.connect(
            audit.on_user_groups_changed,
            sender=user_model.groups.through,
            dispatch_uid=uid + "u_groups",
        )
        m2m_changed.connect(
            audit.on_group_permissions_changed,
            sender=Group.permissions.through,
            dispatch_uid=uid + "g_perms",
        )
        post_save.connect(
            audit.on_page_permission_saved, sender=GroupPagePermission, dispatch_uid=uid + "gpp_s"
        )
        post_delete.connect(
            audit.on_page_permission_saved, sender=GroupPagePermission, dispatch_uid=uid + "gpp_d"
        )
        post_save.connect(audit.on_otp_device_saved, sender=TOTPDevice, dispatch_uid=uid + "otp_s")
        post_delete.connect(
            audit.on_otp_device_deleted, sender=TOTPDevice, dispatch_uid=uid + "otp_d"
        )
        for log_model in (PageLogEntry, ModelLogEntry):
            post_save.connect(
                audit.on_wagtail_log_entry,
                sender=log_model,
                dispatch_uid=uid + "wagtail." + log_model.__name__,
            )
