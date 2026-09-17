"""`create_demo_staff` — UAT accounts, refused outside dev/staging."""

from __future__ import annotations

from io import StringIO

import pytest
from django.core.management import CommandError, call_command
from django.test import override_settings
from django_otp.oath import totp
from django_otp.plugins.otp_totp.models import TOTPDevice

from apps.users.management.commands.create_demo_staff import DEMO_PASSWORD, DEMO_TOTP_KEY

pytestmark = pytest.mark.django_db


@override_settings(DEBUG=True, ENVIRONMENT="dev")
def test_creates_one_user_per_role_idempotently(django_user_model) -> None:
    for _ in range(2):
        out = StringIO()
        call_command("create_demo_staff", stdout=out)
    assert "demo staff ready" in out.getvalue()
    users = django_user_model.objects.filter(username__startswith="demo-")
    assert sorted(u.username for u in users) == ["demo-admin", "demo-editor", "demo-reviewer"]
    reviewer = users.get(username="demo-reviewer")
    assert reviewer.check_password(DEMO_PASSWORD)
    assert list(reviewer.groups.values_list("name", flat=True)) == ["Medical Reviewer"]
    device = TOTPDevice.objects.get(user=reviewer)
    assert device.confirmed and TOTPDevice.objects.filter(user=reviewer).count() == 1
    assert device.verify_token(f"{totp(bytes.fromhex(DEMO_TOTP_KEY)):06d}")


@override_settings(DEBUG=False, ENVIRONMENT="dev")
def test_refuses_without_debug() -> None:
    with pytest.raises(CommandError, match="DEBUG=False"):
        call_command("create_demo_staff")


@override_settings(DEBUG=True, ENVIRONMENT="production")
def test_refuses_in_production_even_when_forced() -> None:
    with pytest.raises(CommandError, match="ENVIRONMENT"):
        call_command("create_demo_staff", "--allow-non-debug")


@override_settings(DEBUG=True, ENVIRONMENT="dev")
def test_rejects_non_hex_key() -> None:
    with pytest.raises(CommandError, match="hex"):
        call_command("create_demo_staff", "--totp-key", "not-hex")


@override_settings(DEBUG=False, ENVIRONMENT="dev", SETTINGS_MODULE="config.settings.prod")
def test_refuses_prod_settings_unless_staging() -> None:
    with pytest.raises(CommandError, match="ENVIRONMENT"):
        call_command("create_demo_staff", "--allow-non-debug")
