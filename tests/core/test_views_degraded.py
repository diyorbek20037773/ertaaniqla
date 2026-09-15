"""Failure paths of infrastructure views."""

from __future__ import annotations

from unittest import mock

import pytest
from django.test import Client, RequestFactory

from apps.core import views

pytestmark = pytest.mark.django_db


def test_readyz_reports_degraded_when_db_is_down(client: Client) -> None:
    with mock.patch("apps.core.views.connection") as conn:
        conn.cursor.side_effect = RuntimeError("db down")
        response = client.get("/readyz/")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["checks"]["db"].startswith("error:")
    assert body["checks"]["cache"] == "ok"


def test_readyz_reports_degraded_when_cache_is_down(client: Client) -> None:
    with mock.patch("apps.core.views.cache") as cache:
        cache.set.side_effect = RuntimeError("redis down")
        response = client.get("/readyz/")
    assert response.status_code == 503
    assert response.json()["checks"]["cache"].startswith("error:")


def test_readyz_reports_cache_miss(client: Client) -> None:
    with mock.patch("apps.core.views.cache") as cache:
        cache.get.return_value = None
        response = client.get("/readyz/")
    assert response.status_code == 503
    assert response.json()["checks"]["cache"] == "error: miss"


def test_ratelimited_view_renders_429() -> None:
    request = RequestFactory().get("/uz/savol-javob/")
    response = views.ratelimited(request, Exception("limited"))
    assert response.status_code == 429


def test_server_error_view_renders_without_db() -> None:
    request = RequestFactory().get("/uz/")
    response = views.server_error(request)
    assert response.status_code == 500
    assert b"<html" in response.content


def test_metrics_rejects_malformed_basic_auth(client: Client, settings) -> None:
    settings.METRICS_BASIC_AUTH = "prom:secret"
    response = client.get("/metrics", HTTP_AUTHORIZATION="Basic not-base64!!")
    assert response.status_code == 401
