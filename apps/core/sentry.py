"""Sentry `before_send` hook: strip anything that could be personal data.

Pure function — imported by config/settings/prod.py before Django apps are loaded, so it must
not import models.
"""

from __future__ import annotations

from typing import Any, cast

from sentry_sdk.types import Event, Hint

_SENSITIVE_KEYS = {
    "contact",
    "email",
    "phone",
    "name",
    "text",
    "password",
    "cookie",
    "authorization",
    "csrfmiddlewaretoken",
}


def _scrub(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            k: ("[Filtered]" if str(k).lower() in _SENSITIVE_KEYS else _scrub(v))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_scrub(v) for v in value]
    return value


def scrub_sentry_event(event: Event, hint: Hint) -> Event | None:
    data: dict[str, Any] = dict(event)
    request = data.get("request")
    if isinstance(request, dict):
        request.pop("cookies", None)
        request["headers"] = _scrub(request.get("headers", {}))
        request["data"] = _scrub(request.get("data", {}))
        request.pop("env", None)
    user = data.get("user")
    if isinstance(user, dict):
        data["user"] = {"id": user.get("id")}
    return cast(Event, data)
