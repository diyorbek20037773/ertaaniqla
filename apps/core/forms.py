"""Shared form pieces: honeypot + Turnstile mixin, accessible widget attrs."""

from __future__ import annotations

from typing import Any

from django import forms
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from apps.core.antispam import client_ip, turnstile_enabled, verify_turnstile

HONEYPOT_FIELD = "website"
TURNSTILE_FIELD = "cf-turnstile-response"


class AntiSpamFormMixin(forms.Form):
    """Adds an invisible honeypot field and validates the Turnstile token.

    Pass `request=` to the form constructor so the client IP reaches Turnstile.
    """

    website = forms.CharField(
        required=False,
        label="",
        widget=forms.TextInput(
            attrs={
                "class": "hp-field",
                "tabindex": "-1",
                "autocomplete": "off",
                "aria-hidden": "true",
            }
        ),
    )

    def __init__(self, *args: Any, request: HttpRequest | None = None, **kwargs: Any) -> None:
        self.request = request
        super().__init__(*args, **kwargs)

    def clean_website(self) -> str:
        if self.cleaned_data.get(HONEYPOT_FIELD):
            raise forms.ValidationError(_("Spam check failed."))
        return ""

    def clean(self) -> dict[str, Any]:
        cleaned: dict[str, Any] = super().clean() or {}
        if turnstile_enabled():
            token = str(self.data.get(TURNSTILE_FIELD, "") if hasattr(self, "data") else "")
            ip = client_ip(self.request) if self.request is not None else ""
            if not verify_turnstile(token, ip):
                raise forms.ValidationError(
                    _("Please confirm you are not a robot and try again."), code="turnstile"
                )
        return cleaned


def add_error_attrs(form: forms.Form) -> None:
    """`aria-invalid` + `aria-describedby` on fields with errors (spec §9)."""
    for name, field in form.fields.items():
        if name in form.errors:
            field.widget.attrs["aria-invalid"] = "true"
            field.widget.attrs["aria-describedby"] = f"id_{name}_error"
