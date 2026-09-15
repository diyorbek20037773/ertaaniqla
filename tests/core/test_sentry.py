"""Sentry PII scrubbing hook."""

from __future__ import annotations

from typing import Any, cast

from apps.core.sentry import scrub_sentry_event


def test_scrub_removes_cookies_and_filters_sensitive_keys() -> None:
    event: dict[str, Any] = {
        "request": {
            "cookies": {"sessionid": "abc"},
            "headers": {"Authorization": "Basic xyz", "Accept": "text/html"},
            "data": {
                "name": "Ali",
                "text": "hello",
                "page_url": "/uz/",
                "nested": [{"phone": "1"}],
            },
            "env": {"REMOTE_ADDR": "1.2.3.4"},
        },
        "user": {"id": 7, "email": "a@b.uz", "ip_address": "1.2.3.4"},
        "message": "boom",
    }
    out = cast(dict[str, Any], scrub_sentry_event(cast(Any, event), {}))
    request = out["request"]
    assert "cookies" not in request
    assert "env" not in request
    assert request["headers"] == {"Authorization": "[Filtered]", "Accept": "text/html"}
    assert request["data"]["name"] == "[Filtered]"
    assert request["data"]["text"] == "[Filtered]"
    assert request["data"]["page_url"] == "/uz/"
    assert request["data"]["nested"] == [{"phone": "[Filtered]"}]
    assert out["user"] == {"id": 7}
    assert out["message"] == "boom"


def test_scrub_is_noop_without_request_or_user() -> None:
    assert scrub_sentry_event(cast(Any, {"message": "x"}), {}) == {"message": "x"}
