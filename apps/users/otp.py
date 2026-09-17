"""Compatibility fix for wagtail-2fa 1.8 with django-otp ≥ 1.7.

django-otp 1.7 stopped trying every device when the form posts no `otp_device` and raises
"Please select a device." instead. wagtail-2fa's code form never posts one, so with the
upstream form nobody could finish the 2FA step. Our form verifies against the user's own
confirmed TOTP devices (the only kind wagtail-2fa creates). Installed in `UsersConfig.ready()`;
covered by tests/users/test_2fa.py.
"""

from __future__ import annotations

from typing import Any

from django import forms
from django_otp.plugins.otp_totp.models import TOTPDevice
from wagtail_2fa.forms import TokenForm


class DeviceAwareTokenForm(TokenForm):
    def _verify_token(self, user: Any, token: str, device: Any = None) -> Any:
        if device is not None:
            return super()._verify_token(user, token, device)
        candidates = list(TOTPDevice.objects.devices_for_user(user, confirmed=True))
        if not candidates:
            return super()._verify_token(user, token, None)  # "Please select a device."
        error: forms.ValidationError | None = None
        for candidate in candidates:
            try:
                return super()._verify_token(user, token, candidate)
            except forms.ValidationError as exc:
                error = exc
        assert error is not None
        raise error


def install() -> None:
    from wagtail_2fa import views

    views.LoginView.form_class = DeviceAwareTokenForm
