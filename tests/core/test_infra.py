"""Infrastructure views and middleware (M0)."""

from __future__ import annotations

import pytest
from django.test import Client, override_settings

pytestmark = pytest.mark.django_db


def test_healthz_is_plain_ok_and_uncached(client: Client) -> None:
    response = client.get("/healthz/")
    assert response.status_code == 200
    assert response.content == b"ok"
    assert "no-cache" in response["Cache-Control"]


def test_readyz_reports_db_and_cache(client: Client) -> None:
    response = client.get("/readyz/")
    assert response.status_code == 200
    body = response.json()
    assert body == {"status": "ok", "checks": {"db": "ok", "cache": "ok"}}


def test_root_redirects_to_default_language(client: Client) -> None:
    response = client.get("/")
    assert response.status_code == 302
    assert response["Location"] == "/uz/"


def test_root_honours_accept_language(client: Client) -> None:
    response = client.get("/", HTTP_ACCEPT_LANGUAGE="ru-RU,ru;q=0.9")
    assert response["Location"] == "/ru/"


def test_root_honours_language_cookie_over_header(client: Client) -> None:
    client.cookies["lang"] = "ru"
    response = client.get("/", HTTP_ACCEPT_LANGUAGE="uz")
    assert response["Location"] == "/ru/"


def test_root_honours_uzbek_cyrillic_preference(client: Client) -> None:
    response = client.get("/", HTTP_ACCEPT_LANGUAGE="uz-Cyrl,uz;q=0.9,ru;q=0.8")
    assert response["Location"] == "/oz/"
    assert client.get("/", HTTP_ACCEPT_LANGUAGE="uz-Latn,uz-Cyrl;q=0.5")["Location"] == "/uz/"


def test_root_ignores_unsupported_language(client: Client) -> None:
    response = client.get("/", HTTP_ACCEPT_LANGUAGE="de")
    assert response["Location"] == "/uz/"


def test_robots_txt_hides_cms_and_lists_sitemap(client: Client) -> None:
    response = client.get("/robots.txt")
    assert response.status_code == 200
    text = response.content.decode()
    assert "Disallow: /cms/" in text
    assert "Sitemap: http://testserver/sitemap.xml" in text


def test_sitemap_index_lists_languages(client: Client) -> None:
    response = client.get("/sitemap.xml")
    assert response.status_code == 200
    text = response.content.decode()
    assert "/uz/sitemap.xml" in text
    assert "/oz/sitemap.xml" in text  # Uzbek Cyrillic (D-049)
    assert "/ru/sitemap.xml" in text


def test_language_sitemap_renders(client: Client) -> None:
    assert client.get("/uz/sitemap.xml").status_code == 200
    assert client.get("/ru/sitemap.xml").status_code == 200


def test_request_id_generated_and_echoed(client: Client) -> None:
    response = client.get("/healthz/")
    assert len(response["X-Request-ID"]) == 32


def test_request_id_from_proxy_is_kept_when_safe(client: Client) -> None:
    response = client.get("/healthz/", HTTP_X_REQUEST_ID="abc-123-def-456")
    assert response["X-Request-ID"] == "abc-123-def-456"


def test_request_id_from_proxy_is_replaced_when_unsafe(client: Client) -> None:
    response = client.get("/healthz/", HTTP_X_REQUEST_ID="<script>")
    assert response["X-Request-ID"] != "<script>"


def test_permissions_policy_header_present(client: Client) -> None:
    response = client.get("/healthz/")
    assert "camera=()" in response["Permissions-Policy"]


def test_metrics_disabled_without_credentials_setting(client: Client) -> None:
    assert client.get("/metrics").status_code == 403


@override_settings(METRICS_BASIC_AUTH="prom:secret")
def test_metrics_requires_basic_auth(client: Client) -> None:
    assert client.get("/metrics").status_code == 401
    import base64

    token = base64.b64encode(b"prom:secret").decode()
    response = client.get("/metrics", HTTP_AUTHORIZATION=f"Basic {token}")
    assert response.status_code == 200
    assert b"django_http_requests" in response.content or b"python_info" in response.content


def test_cms_admin_login_page_available(client: Client) -> None:
    response = client.get("/cms/login/")
    assert response.status_code == 200


def test_old_admin_url_is_not_used(client: Client) -> None:
    # LocaleMiddleware may first redirect to /uz/admin/; the final answer must be 404
    assert client.get("/admin/", follow=True).status_code == 404
    assert client.get("/uz/admin/").status_code == 404


def test_csp_header_is_nonce_based(client: Client) -> None:
    # any page rendered through base.html requests a nonce; the 404 page is always available
    response = client.get("/uz/no-such-page/")
    assert response.status_code == 404
    csp = response.get("Content-Security-Policy", "")
    assert "'nonce-" in csp
    assert "frame-ancestors 'none'" in csp
