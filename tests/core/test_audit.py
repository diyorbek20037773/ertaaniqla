"""Security audit trail (apps/core/audit.py, ADR-0005): what is recorded, where, what never is."""

from __future__ import annotations

import json
import logging
from typing import Any

import pytest
from axes.signals import user_locked_out
from django.contrib.auth.models import Group, Permission
from django.test import Client, RequestFactory
from django.urls import reverse
from wagtail.models import ModelLogEntry

from apps.core import audit
from apps.core.audit import EVENTS, anonymise_ip, username_fingerprint

pytestmark = pytest.mark.django_db

PASSWORD = "correct-horse-battery-staple"


@pytest.fixture
def records(caplog: pytest.LogCaptureFixture) -> pytest.LogCaptureFixture:
    """caplog.records is per test phase: always read it at assertion time."""
    caplog.set_level(logging.INFO, logger="ertaaniqla.audit")
    return caplog


def audit_records(records: pytest.LogCaptureFixture, event: str | None = None) -> list[Any]:
    return [
        r
        for r in records.records
        if r.name == "ertaaniqla.audit" and (event is None or getattr(r, "event", "") == event)
    ]


def events(records: pytest.LogCaptureFixture) -> list[str]:
    return [r.event for r in audit_records(records)]


def dump(records: pytest.LogCaptureFixture) -> str:
    return json.dumps([vars(r) for r in records.records], default=str)


def one(records: pytest.LogCaptureFixture, event: str) -> Any:
    matches = audit_records(records, event)
    assert len(matches) == 1, events(records)
    return matches[0]


def cms_actions(obj: Any) -> list[str]:
    return list(
        ModelLogEntry.objects.filter(object_id=str(obj.pk))
        .order_by("timestamp")
        .values_list("action", flat=True)
    )


@pytest.mark.parametrize(
    ("raw", "anon"),
    [
        ("203.0.113.77", "203.0.113.0"),
        ("2001:db8:1:2:3::5", "2001:db8:1::"),
        ("not-an-ip", ""),
    ],
)
def test_anonymise_ip(raw: str, anon: str) -> None:
    assert anonymise_ip(raw) == anon


def test_username_fingerprint_is_stable_and_short() -> None:
    assert username_fingerprint(" Admin ") == username_fingerprint("admin")
    assert len(username_fingerprint("admin")) == 12
    assert "admin" not in username_fingerprint("admin")


def test_every_event_is_registered_as_wagtail_log_action() -> None:
    from wagtail.log_actions import registry

    for event in EVENTS:
        assert registry.action_exists(audit.ACTION_PREFIX + event), event


def test_login_and_logout_are_recorded_with_anonymised_ip(user, records) -> None:
    client = Client(REMOTE_ADDR="198.51.100.23")
    assert client.login(username="editor", password=PASSWORD)
    client.logout()

    login = one(records, "auth.login")
    assert login.actor_id == user.pk
    assert login.target == f"users.user:{user.pk}"
    assert login.ip in {"", "198.51.100.0"}  # client.login() has no real request IP
    assert "auth.logout" in events(records)
    assert cms_actions(user) == [
        "ertaaniqla.user.created",
        "ertaaniqla.auth.login",
        "ertaaniqla.auth.logout",
    ]


def test_cms_login_view_records_real_client_ip(user, records) -> None:
    client = Client(REMOTE_ADDR="198.51.100.23")
    client.post(reverse("wagtailadmin_login"), {"username": "editor", "password": PASSWORD})
    assert one(records, "auth.login").ip == "198.51.100.0"


def test_failed_login_known_user_is_linked_but_password_never_logged(user, records) -> None:
    client = Client(REMOTE_ADDR="198.51.100.23")
    client.post(reverse("wagtailadmin_login"), {"username": "editor", "password": "wrong-secret"})

    failed = one(records, "auth.login_failed")
    assert failed.target == f"users.user:{user.pk}"
    assert failed.ip == "198.51.100.0"
    assert "ertaaniqla.auth.login_failed" in cms_actions(user)
    assert "wrong-secret" not in dump(records)


def test_failed_login_unknown_username_is_hashed(records) -> None:
    Client().post(reverse("wagtailadmin_login"), {"username": "someone@mail.uz", "password": "x"})
    failed = one(records, "auth.login_failed")
    assert failed.target == ""
    assert failed.details == {"username_hash": username_fingerprint("someone@mail.uz")}
    assert "someone@mail.uz" not in dump(records)


def test_axes_lockout_is_recorded(user, records) -> None:
    request = RequestFactory().post("/cms/login/", REMOTE_ADDR="192.0.2.9")
    user_locked_out.send("axes", request=request, username="editor", ip_address="192.0.2.9")
    lockout = one(records, "auth.lockout")
    assert lockout.target == f"users.user:{user.pk}"
    assert lockout.ip == "192.0.2.0"
    assert "ertaaniqla.auth.lockout" in cms_actions(user)


def test_user_created_and_privilege_flags(django_user_model, records) -> None:
    member = django_user_model.objects.create_user(username="new", password=PASSWORD)
    assert one(records, "user.created").details == {"is_staff": False, "is_superuser": False}

    member.is_superuser = True
    member.is_staff = True
    member.save()
    superuser = one(records, "user.superuser_changed")
    assert superuser.details == {"old": False, "new": True}
    assert "user.staff_changed" in events(records)

    member.set_password("another-long-password-123")
    member.save()
    assert "auth.password_changed" in events(records)

    member.is_active = False
    member.save(update_fields=["is_active"])
    assert "user.active_changed" in events(records)

    member_pk = member.pk
    member.delete()
    assert one(records, "user.deleted").details == {"user_id": member_pk}


def test_last_login_update_does_not_query_or_record(
    user, records, django_assert_num_queries
) -> None:
    from django.utils import timezone

    user.last_login = timezone.now()
    with django_assert_num_queries(1):  # the UPDATE only, no snapshot SELECT
        user.save(update_fields=["last_login"])
    assert events(records) == []


def test_group_membership_both_directions(user, records) -> None:
    editors = Group.objects.create(name="Audit editors")
    user.groups.add(editors)
    added = one(records, "user.groups_changed")
    assert added.details == {"change": "add", "groups": ["Audit editors"]}

    editors.user_set.remove(user)
    changes = audit_records(records, "user.groups_changed")
    assert changes[-1].details == {"change": "remove", "groups": ["Audit editors"]}
    assert changes[-1].target == f"users.user:{user.pk}"


def test_role_permission_changes(records) -> None:
    from wagtail.models import GroupPagePermission, Page

    group = Group.objects.create(name="Audit role")
    permission = Permission.objects.get(codename="add_page")
    group.permissions.add(permission)
    assert one(records, "role.permissions_changed").details["permission_ids"] == [permission.pk]

    root = Page.get_first_root_node()
    gpp = GroupPagePermission.objects.create(
        group=group, page=root, permission=Permission.objects.get(codename="publish_page")
    )
    gpp.delete()
    changes = [r.details["change"] for r in audit_records(records, "role.permissions_changed")]
    assert changes == ["add", "added", "deleted"]


def test_totp_device_added_and_removed(user, records) -> None:
    from django_otp.plugins.otp_totp.models import TOTPDevice

    device = TOTPDevice.objects.create(user=user, name="phone", confirmed=True)
    assert one(records, "2fa.device_added").details == {"device": "TOTPDevice", "confirmed": True}
    device.delete()
    assert one(records, "2fa.device_removed").target == f"users.user:{user.pk}"
    blob = dump(records)
    assert device.key not in blob


def test_wagtail_cms_actions_are_mirrored(admin_user, records) -> None:
    from wagtail.log_actions import log

    group = Group.objects.create(name="Mirror")
    log(instance=group, action="wagtail.edit", user=admin_user)
    mirrored = one(records, "cms.edit")
    assert mirrored.actor_id == admin_user.pk
    assert mirrored.details["content_type"] == "group"
    # our own entries are not mirrored twice
    audit.audit_event("user.groups_changed", target=admin_user, actor=admin_user)
    assert "cms.ertaaniqla.user.groups_changed" not in events(records)


def test_opening_question_with_contact_records_pii_view(admin_user, records) -> None:
    from apps.faq.models import Question

    question = Question.objects.create(
        section="women", text="[[TODO: test question]]", contact="+998 90 000-00-00"
    )
    client = Client(REMOTE_ADDR="203.0.113.50")
    client.force_login(admin_user)
    url = reverse("wagtailsnippets_faq_question:edit", args=[question.pk])
    assert client.get(url).status_code == 200

    viewed = one(records, "pii.viewed")
    assert viewed.actor_id == admin_user.pk
    assert viewed.target == f"faq.question:{question.pk}"
    assert viewed.ip == "203.0.113.0"
    assert "ertaaniqla.pii.viewed" in cms_actions(question)
    assert "+998 90 000-00-00" not in dump(records)


def test_question_without_contact_is_not_a_pii_view(admin_user, records) -> None:
    from apps.faq.models import Question

    question = Question.objects.create(section="women", text="[[TODO: test question]]")
    client = Client()
    client.force_login(admin_user)
    client.get(reverse("wagtailsnippets_faq_question:edit", args=[question.pk]))
    assert "pii.viewed" not in events(records)


def test_audit_failure_never_breaks_the_caller(monkeypatch: pytest.MonkeyPatch, user) -> None:
    def boom(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("log backend down")

    monkeypatch.setattr("wagtail.log_actions.log", boom)
    audit.audit_event("auth.login", target=user, actor=user)  # must not raise
