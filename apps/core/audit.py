"""Security audit trail (ADR-0005).

Every security-relevant staff action becomes one JSON line on the `ertaaniqla.audit` logger
(→ Alloy → Loki → Grafana "logs & audit" dashboard + Loki ruler alerts → Telegram) and, when it
concerns a database object, a Wagtail log entry (CMS → Reports → Site history), so an admin sees
it without Grafana.

Recorded: logins, logouts, failed logins, axes lockouts, user created/deleted, superuser/staff/
active flag and password changes, group membership and role permission changes, 2FA devices
added/removed, moderators opening a record that holds encrypted contact data, and a copy of every
Wagtail CMS action (publish, edit, delete, workflow…).

Never recorded: passwords, OTP tokens, decrypted contact values, full client IPs (last IPv4
octet / IPv6 tail dropped), usernames that do not exist (only a short hash).
"""

from __future__ import annotations

import contextvars
import hashlib
import ipaddress
import logging
from collections.abc import Callable
from typing import Any

from django.contrib.auth import get_user_model
from django.db import models
from django.http import HttpRequest, HttpResponse
from django.utils.translation import gettext_lazy as _
from django_stubs_ext import StrOrPromise

from apps.core.antispam import client_ip
from apps.core.middleware import request_id_var

logger = logging.getLogger("ertaaniqla.audit")

ACTION_PREFIX = "ertaaniqla."

# event → (label, message) for the Wagtail log registry, shown in CMS → Reports → Site history
EVENTS: dict[str, tuple[StrOrPromise, StrOrPromise]] = {
    "auth.login": (_("Login"), _("Logged in")),
    "auth.logout": (_("Logout"), _("Logged out")),
    "auth.login_failed": (_("Failed login"), _("Failed login attempt")),
    "auth.lockout": (_("Account lockout"), _("Locked out after repeated failed logins")),
    "auth.password_changed": (_("Password change"), _("Password changed")),
    "user.created": (_("User created"), _("User account created")),
    "user.deleted": (_("User deleted"), _("User account deleted")),
    "user.superuser_changed": (_("Superuser flag"), _("Superuser status changed")),
    "user.staff_changed": (_("Staff flag"), _("Staff status changed")),
    "user.active_changed": (_("Active flag"), _("Account activated or deactivated")),
    "user.groups_changed": (_("Roles"), _("Role (group) membership changed")),
    "role.permissions_changed": (_("Role permissions"), _("Role permissions changed")),
    "2fa.device_added": (_("2FA device added"), _("Two-factor device added")),
    "2fa.device_removed": (_("2FA device removed"), _("Two-factor device removed")),
    "pii.viewed": (_("Personal data viewed"), _("Record with encrypted contact data opened")),
}

_current_request: contextvars.ContextVar[HttpRequest | None] = contextvars.ContextVar(
    "audit_request", default=None
)


class AuditContextMiddleware:
    """Expose the current request to signal receivers (actor + IP). Place after auth."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        token = _current_request.set(request)
        try:
            return self.get_response(request)
        finally:
            _current_request.reset(token)


def anonymise_ip(value: str) -> str:
    """203.0.113.7 → 203.0.113.0 ; 2001:db8:1:2::5 → 2001:db8:1:: (same rule as nginx logs)."""
    try:
        ip = ipaddress.ip_address(value.strip())
    except ValueError:
        return ""
    prefix = 24 if ip.version == 4 else 48
    return str(ipaddress.ip_network(f"{ip}/{prefix}", strict=False).network_address)


def username_fingerprint(username: str) -> str:
    """Short, non-reversible id for a login name that matches no account."""
    return hashlib.sha256(username.strip().lower().encode()).hexdigest()[:12]


def object_ref(obj: models.Model | None) -> str:
    if obj is None:
        return ""
    return f"{obj._meta.label_lower}:{obj.pk}"


def _actor_from(request: HttpRequest | None) -> Any:
    user = getattr(request, "user", None) if request is not None else None
    return user if user is not None and getattr(user, "is_authenticated", False) else None


def audit_event(
    event: str,
    *,
    target: models.Model | None = None,
    actor: Any = None,
    request: HttpRequest | None = None,
    record_in_cms: bool = True,
    **details: Any,
) -> None:
    """Write one audit record. Never raises: auditing must not break a login or a save."""
    try:
        request = request or _current_request.get()
        actor = actor or _actor_from(request)
        ip = client_ip(request) if request is not None else ""
        payload: dict[str, Any] = {
            "event": event,
            "actor_id": getattr(actor, "pk", None),
            "target": object_ref(target),
            "ip": anonymise_ip(ip) if ip else "",
            "audit_request_id": request_id_var.get(),
        }
        if details:
            payload["details"] = details
        logger.info(event, extra=payload)

        if record_in_cms and target is not None and target.pk is not None and event in EVENTS:
            from wagtail.log_actions import log

            log(instance=target, action=ACTION_PREFIX + event, user=actor, data=details)
    except Exception:  # pragma: no cover - defensive: auditing is best effort
        logger.exception("audit record failed", extra={"event": event})


# --- Wagtail log registry ------------------------------------------------------------------------


def register_log_actions(actions: Any) -> None:
    for event, (label, message) in EVENTS.items():
        actions.register_action(ACTION_PREFIX + event, label, message)


# --- signal receivers (connected in CoreConfig.ready) --------------------------------------------

_TRACKED_USER_FLAGS = {
    "is_superuser": "user.superuser_changed",
    "is_staff": "user.staff_changed",
    "is_active": "user.active_changed",
}


def on_user_logged_in(sender: Any, request: HttpRequest, user: Any, **kwargs: Any) -> None:
    audit_event("auth.login", target=user, actor=user, request=request)


def on_user_logged_out(sender: Any, request: HttpRequest, user: Any = None, **kwargs: Any) -> None:
    audit_event("auth.logout", target=user, actor=user, request=request)


def on_user_login_failed(
    sender: Any, credentials: dict[str, Any], request: HttpRequest | None = None, **kwargs: Any
) -> None:
    username = str(credentials.get("username", "") or "")
    user_model = get_user_model()
    user = (
        user_model._default_manager.filter(**{user_model.USERNAME_FIELD: username}).first()
        if username
        else None
    )
    if user is not None:
        audit_event("auth.login_failed", target=user, request=request)
    else:
        audit_event(
            "auth.login_failed",
            request=request,
            record_in_cms=False,
            username_hash=username_fingerprint(username) if username else "",
        )


def on_user_locked_out(
    sender: Any, request: HttpRequest | None = None, username: str | None = None, **kwargs: Any
) -> None:
    user_model = get_user_model()
    user = (
        user_model._default_manager.filter(**{user_model.USERNAME_FIELD: username}).first()
        if username
        else None
    )
    audit_event(
        "auth.lockout",
        target=user,
        request=request,
        record_in_cms=user is not None,
        username_hash=username_fingerprint(username) if username and user is None else "",
    )


def on_user_pre_save(sender: Any, instance: Any, update_fields: Any = None, **kwargs: Any) -> None:
    tracked = {*_TRACKED_USER_FLAGS, "password"}
    if instance.pk is None or (update_fields is not None and not tracked & set(update_fields)):
        instance._audit_previous = None  # e.g. last_login updates on every login: no query
        return
    instance._audit_previous = (
        sender._default_manager.filter(pk=instance.pk).values(*tracked).first()
    )


def on_user_post_save(sender: Any, instance: Any, created: bool, **kwargs: Any) -> None:
    if created:
        audit_event(
            "user.created",
            target=instance,
            is_staff=instance.is_staff,
            is_superuser=instance.is_superuser,
        )
        return
    previous = getattr(instance, "_audit_previous", None)
    if not previous:
        return
    for field, event in _TRACKED_USER_FLAGS.items():
        old, new = previous[field], getattr(instance, field)
        if old != new:
            audit_event(event, target=instance, old=old, new=new)
    if previous["password"] != instance.password:
        audit_event("auth.password_changed", target=instance)
    instance._audit_previous = None


def on_user_deleted(sender: Any, instance: Any, **kwargs: Any) -> None:
    # the row is gone: log line only (a Wagtail entry would point at a missing object)
    audit_event("user.deleted", record_in_cms=False, user_id=instance.pk)


def on_user_groups_changed(
    sender: Any,
    instance: Any,
    action: str,
    pk_set: set[int] | None = None,
    reverse: bool = False,
    **kwargs: Any,
) -> None:
    if action not in {"post_add", "post_remove", "post_clear"}:
        return
    from django.contrib.auth.models import Group

    if reverse:  # group.user_set.add(user…): instance is the Group
        names = [instance.name]
        user_model = get_user_model()
        users = list(user_model._default_manager.filter(pk__in=pk_set or ()))
    else:
        names = sorted(Group.objects.filter(pk__in=pk_set or ()).values_list("name", flat=True))
        users = [instance]
    for user in users:
        audit_event("user.groups_changed", target=user, change=action[5:], groups=names)


def on_group_permissions_changed(
    sender: Any, instance: Any, action: str, reverse: bool = False, **kwargs: Any
) -> None:
    if action in {"post_add", "post_remove", "post_clear"} and not reverse:
        audit_event(
            "role.permissions_changed",
            target=instance,
            change=action[5:],
            permission_ids=sorted(kwargs.get("pk_set") or ()),
        )


def on_page_permission_saved(sender: Any, instance: Any, **kwargs: Any) -> None:
    created = kwargs.get("created")
    change = "deleted" if created is None else ("added" if created else "changed")
    audit_event(
        "role.permissions_changed",
        target=instance.group,
        change=change,
        page_id=instance.page_id,
        permission=str(getattr(instance, "permission", "") or ""),
    )


def on_otp_device_saved(sender: Any, instance: Any, created: bool, **kwargs: Any) -> None:
    if created:
        audit_event(
            "2fa.device_added",
            target=instance.user,
            device=sender.__name__,
            confirmed=instance.confirmed,
        )


def on_otp_device_deleted(sender: Any, instance: Any, **kwargs: Any) -> None:
    audit_event("2fa.device_removed", target=instance.user, device=sender.__name__)


def on_wagtail_log_entry(sender: Any, instance: Any, created: bool, **kwargs: Any) -> None:
    """Mirror every Wagtail CMS action (publish, edit, delete, workflow…) to the audit stream."""
    if not created or str(instance.action).startswith(ACTION_PREFIX):
        return
    audit_event(
        "cms." + str(instance.action).removeprefix("wagtail."),
        actor=instance.user,
        record_in_cms=False,
        content_type=str(instance.content_type.model) if instance.content_type_id else "",
        object_id=str(instance.object_id),
    )


def before_edit_pii_snippet(request: HttpRequest, instance: Any) -> None:
    """Wagtail `before_edit_snippet` hook: a moderator opened a record with contact data."""
    contact = getattr(instance, "contact", None)
    if request.method == "GET" and contact and isinstance(instance, models.Model):
        audit_event("pii.viewed", target=instance, request=request)
