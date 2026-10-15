"""Template context available on every page."""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.http import HttpRequest

from apps.core.visibility import hidden_sections


def site_context(request: HttpRequest) -> dict[str, Any]:
    return {
        "SITE_BASE_URL": settings.SITE_BASE_URL,
        "CANONICAL_DOMAIN": settings.CANONICAL_DOMAIN,
        "APP_RELEASE": settings.APP_RELEASE,
        "ENVIRONMENT": settings.ENVIRONMENT,
        "YANDEX_METRIKA_ID": settings.YANDEX_METRIKA_ID,
        "TURNSTILE_SITE_KEY": settings.TURNSTILE_SITE_KEY,
        "request_id": getattr(request, "request_id", ""),
        # D-087: called (cached) only by templates that ask, e.g. section filter options
        "hidden_sections": hidden_sections,
    }
