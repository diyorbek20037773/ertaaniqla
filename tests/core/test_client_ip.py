"""ClientIPMiddleware: the real client address behind trusted proxies (D-074)."""

from __future__ import annotations

import logging

import pytest
from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory, override_settings

from apps.core.logging import RequestIDFilter
from apps.core.middleware import ClientIPMiddleware


def _remote_addr(xff: str | None, proxies: int, remote: str = "100.64.0.0") -> str:
    seen: dict[str, str] = {}

    def view(request: HttpRequest) -> HttpResponse:
        seen["ip"] = request.META["REMOTE_ADDR"]
        return HttpResponse()

    extra = {"REMOTE_ADDR": remote}
    if xff is not None:
        extra["HTTP_X_FORWARDED_FOR"] = xff
    with override_settings(TRUSTED_PROXY_COUNT=proxies):
        ClientIPMiddleware(view)(RequestFactory().get("/", **extra))
    return seen["ip"]


@pytest.mark.parametrize(
    ("xff", "proxies", "expected"),
    [
        ("203.0.113.7", 1, "203.0.113.7"),  # one proxy appended the client
        ("6.6.6.6, 203.0.113.7", 1, "203.0.113.7"),  # client-sent value is ignored
        ("203.0.113.7, 10.0.0.2", 2, "203.0.113.7"),  # two proxies
        ("2001:db8::1", 1, "2001:db8::1"),
        ("203.0.113.7", 0, "100.64.0.0"),  # dev: header not trusted
        (None, 1, "100.64.0.0"),  # healthcheck / Prometheus: no header
        ("not-an-ip", 1, "100.64.0.0"),
        ("203.0.113.7", 2, "100.64.0.0"),  # fewer hops than proxies: keep REMOTE_ADDR
    ],
)
def test_client_ip_from_trusted_hop(xff: str | None, proxies: int, expected: str) -> None:
    assert _remote_addr(xff, proxies) == expected


@pytest.mark.parametrize(
    ("levelno", "level"),
    [(logging.INFO, "info"), (logging.WARNING, "warn"), (logging.ERROR, "error")],
)
def test_log_records_carry_host_level(levelno: int, level: str) -> None:
    record = logging.LogRecord("x", levelno, __file__, 1, "msg", None, None)
    RequestIDFilter().filter(record)
    assert record.level == level  # type: ignore[attr-defined]
    assert record.levelname  # Loki rules keep using levelname
