"""2FA is mandatory for every CMS user (spec §8). Test settings switch it off globally; these
tests switch it back on to prove the middleware chain enforces it."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import Group
from django.test import Client, override_settings
from django_otp.oath import totp
from django_otp.plugins.otp_totp.models import TOTPDevice

from apps.users.roles import EDITOR

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("home")]

PASSWORD = "correct-horse-battery-staple"


@pytest.fixture
def staff(django_user_model):
    user = django_user_model.objects.create_user(username="editor2fa", password=PASSWORD)
    user.groups.add(Group.objects.get(name=EDITOR))
    return user


def login(user) -> Client:
    client = Client()
    assert client.login(username=user.username, password=PASSWORD)
    return client


@override_settings(WAGTAIL_2FA_REQUIRED=True)
def test_staff_without_device_is_sent_to_device_setup(staff) -> None:
    client = login(staff)
    response = client.get("/cms/")
    assert response.status_code == 302
    assert "/cms/2fa/devices/new" in response["Location"]
    response = client.get("/cms/pages/")
    assert response.status_code == 302
    assert "/cms/2fa/devices/new" in response["Location"]


@override_settings(WAGTAIL_2FA_REQUIRED=True)
def test_staff_with_device_must_enter_code(staff) -> None:
    device = TOTPDevice.objects.create(user=staff, name="phone", confirmed=True)
    client = login(staff)
    response = client.get("/cms/")
    assert response.status_code == 302
    assert "/cms/2fa/auth" in response["Location"]

    wrong = client.post("/cms/2fa/auth?next=/cms/", {"otp_token": "000000"})
    assert wrong.status_code == 200  # form re-rendered with an error
    assert client.get("/cms/").status_code == 302

    device.refresh_from_db()
    device.throttle_reset()  # django-otp throttles right after a failed attempt
    token = f"{totp(device.bin_key, device.step, device.t0, device.digits, device.drift):06d}"
    ok = client.post("/cms/2fa/auth?next=/cms/", {"otp_token": token})
    assert ok.status_code == 302, ok.context["form"].errors if ok.context else ok
    assert client.get("/cms/").status_code == 200


@override_settings(WAGTAIL_2FA_REQUIRED=True)
def test_visitors_unaffected_unverified_staff_forced_everywhere(staff) -> None:
    assert Client().get("/uz/").status_code == 200
    # an unverified staff session is pushed to 2FA even on public pages (wagtail-2fa default)
    response = login(staff).get("/uz/")
    assert response.status_code == 302
    assert "/cms/2fa/devices/new" in response["Location"]


@override_settings(WAGTAIL_2FA_REQUIRED=True)
def test_code_from_second_device_is_accepted(staff) -> None:
    TOTPDevice.objects.create(user=staff, name="old phone", confirmed=True)
    new = TOTPDevice.objects.create(user=staff, name="new phone", confirmed=True)
    TOTPDevice.objects.create(user=staff, name="unconfirmed", confirmed=False)
    client = login(staff)
    token = f"{totp(new.bin_key, new.step, new.t0, new.digits, new.drift):06d}"
    response = client.post("/cms/2fa/auth?next=/cms/", {"otp_token": token})
    assert response.status_code == 302
    assert client.get("/cms/").status_code == 200


@override_settings(WAGTAIL_2FA_REQUIRED=True)
def test_code_of_another_users_device_is_rejected(staff, django_user_model) -> None:
    TOTPDevice.objects.create(user=staff, name="phone", confirmed=True)
    other = django_user_model.objects.create_user(username="other", password=PASSWORD)
    foreign = TOTPDevice.objects.create(user=other, name="phone", confirmed=True)
    client = login(staff)
    token = f"{totp(foreign.bin_key, foreign.step, foreign.t0, foreign.digits, foreign.drift):06d}"
    assert client.post("/cms/2fa/auth?next=/cms/", {"otp_token": token}).status_code == 200
    assert client.get("/cms/").status_code == 302
