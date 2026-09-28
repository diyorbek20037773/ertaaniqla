"""Deploy checks (`manage.py check --deploy`, run by the `migrate` role before every release)."""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.checks import Error, Tags, Warning, register

# Cloudflare's documented always-pass / always-fail keys: 1x…, 2x…, 3x…
TURNSTILE_TEST_PREFIXES = ("1x0000", "2x0000", "3x0000")


@register(Tags.security, deploy=True)
def turnstile_keys(app_configs: Any = None, **kwargs: Any) -> list[Any]:
    """EA-06: test keys give no bot protection and show "For testing only" to visitors."""
    keys = (str(settings.TURNSTILE_SITE_KEY), str(settings.TURNSTILE_SECRET_KEY))
    if not any(key.startswith(TURNSTILE_TEST_PREFIXES) for key in keys):
        return []
    message = "Cloudflare Turnstile uses a public test key (no bot protection)."
    hint = "Set TURNSTILE_SITE_KEY / TURNSTILE_SECRET_KEY from the client's Cloudflare account."
    if settings.ENVIRONMENT == "prod":
        return [Error(message, hint=hint, id="ertaaniqla.E001")]
    return [Warning(message, hint=hint, id="ertaaniqla.W001")]
