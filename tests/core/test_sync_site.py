"""`sync_site` (EA-01, D-075): absolute URLs follow SITE_BASE_URL, never `http://localhost`."""

from __future__ import annotations

from io import StringIO

import pytest
from django.core.management import call_command
from django.test import Client, override_settings
from wagtail.models import Site

from apps.core.management.commands.sync_site import site_target

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://ertaaniqla.uz", ("ertaaniqla.uz", 443)),
        ("https://ertaaniqla.uz/", ("ertaaniqla.uz", 443)),
        ("http://localhost:8000", ("localhost", 8000)),
        ("http://staging.ertaaniqla.uz", ("staging.ertaaniqla.uz", 80)),
    ],
)
def test_site_target(url: str, expected: tuple[str, int]) -> None:
    assert site_target(url) == expected


@override_settings(SITE_BASE_URL="https://demo.example.org", ALLOWED_HOSTS=["*"])
def test_sync_site_rewrites_every_absolute_url(seeded, client: Client) -> None:
    out = StringIO()
    call_command("sync_site", stdout=out)
    assert "demo.example.org:443" in out.getvalue()
    site = Site.objects.get(is_default_site=True)
    assert (site.hostname, site.port) == ("demo.example.org", 443)

    html = client.get(
        "/uz/ayollar/ogohlik/kokrak-bezi-saratoni/", HTTP_HOST="demo.example.org", secure=True
    ).content.decode()
    assert "localhost" not in html
    assert '<link rel="canonical" href="https://demo.example.org/uz/' in html
    sitemap = client.get("/uz/sitemap.xml", HTTP_HOST="demo.example.org", secure=True)
    assert b"<loc>https://demo.example.org/uz/" in sitemap.content
    assert b"localhost" not in sitemap.content

    out = StringIO()
    call_command("sync_site", stdout=out)  # idempotent
    assert "already" in out.getvalue()
