"""Infrastructure views: health checks, language redirect, robots, sitemaps, metrics."""

from __future__ import annotations

import base64
import hmac
import logging
from typing import Any, cast

from django.conf import settings
from django.contrib.sitemaps.views import sitemap as sitemap_view
from django.core.cache import cache
from django.db import connection
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.utils import translation
from django.utils.translation import get_language_from_request
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET
from wagtail.contrib.sitemaps import Sitemap

from apps.core.sitemaps import LocaleSitemap

logger = logging.getLogger("ertaaniqla.core")


@never_cache
@require_GET
def healthz(request: HttpRequest) -> HttpResponse:
    """Process is up. Used by nginx / docker HEALTHCHECK. Never touches DB or Redis."""
    return HttpResponse("ok", content_type="text/plain")


@never_cache
@require_GET
def readyz(request: HttpRequest) -> JsonResponse:
    """DB + Redis ping. Used by deploy `--wait`. 503 when a dependency is down."""
    checks: dict[str, str] = {}
    ok = True
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
        checks["db"] = "ok"
    except Exception as exc:
        checks["db"] = f"error: {exc.__class__.__name__}"
        ok = False
    try:
        cache.set("readyz", "1", 5)
        checks["cache"] = "ok" if cache.get("readyz") == "1" else "error: miss"
        ok = ok and checks["cache"] == "ok"
    except Exception as exc:
        checks["cache"] = f"error: {exc.__class__.__name__}"
        ok = False
    status = 200 if ok else 503
    return JsonResponse({"status": "ok" if ok else "degraded", "checks": checks}, status=status)


def language_redirect(request: HttpRequest) -> HttpResponseRedirect:
    """`/` → `/uz/` or `/ru/`: cookie first, then Accept-Language, then default."""
    lang = get_language_from_request(request, check_path=False)
    supported = {code for code, _ in settings.LANGUAGES}
    if lang not in supported:
        lang = settings.LANGUAGE_CODE
    target = f"/{lang}/"
    if lang == "uz" and _prefers_uzbek_cyrillic(request):
        from apps.core.middleware import cyrillic_prefix

        target = cyrillic_prefix()
    response = HttpResponseRedirect(target)
    response["Vary"] = "Accept-Language, Cookie"
    return response


def _prefers_uzbek_cyrillic(request: HttpRequest) -> bool:
    """Accept-Language names uz-Cyrl before any other Uzbek variant (no language cookie set)."""
    from django.utils.translation.trans_real import parse_accept_lang_header

    if not getattr(settings, "UZ_CYRILLIC_ENABLED", True):
        return False
    if request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME):
        return False
    for tag, _quality in parse_accept_lang_header(request.headers.get("Accept-Language", "")):
        if tag.startswith("uz"):
            return tag == "uz-cyrl"
    return False


@require_GET
def robots_txt(request: HttpRequest) -> HttpResponse:
    host = request.get_host()
    lines = [
        "User-agent: *",
        f"Disallow: /{settings.CMS_URL_PREFIX}/",
        "Disallow: /django-admin/",
        "Disallow: /documents/",
        "Disallow: /i18n/",
        "Disallow: /*?q=",
        "",
        f"Sitemap: {request.scheme}://{host}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain")


def _sitemaps(request: HttpRequest) -> dict[str, type[Sitemap[Any]] | Sitemap[Any]]:
    return {"pages": LocaleSitemap}


def sitemap_index(request: HttpRequest) -> HttpResponse:
    """One sitemap per language (spec §7), listed in the index."""
    base = f"{request.scheme}://{request.get_host()}"
    prefixes = [f"/{code}/" for code, _ in settings.LANGUAGES]
    if getattr(settings, "UZ_CYRILLIC_ENABLED", True):
        from apps.core.middleware import cyrillic_prefix

        prefixes.insert(1, cyrillic_prefix())
    entries = "".join(
        f"<sitemap><loc>{base}{prefix}sitemap.xml</loc></sitemap>" for prefix in prefixes
    )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"{entries}</sitemapindex>"
    )
    return HttpResponse(xml, content_type="application/xml")


def sitemap_language(request: HttpRequest) -> HttpResponse:
    return sitemap_view(request, _sitemaps(request))


def ratelimited(request: HttpRequest, exception: Exception) -> HttpResponse:
    """django-ratelimit target view: plain 429 page in the current language."""
    return render(request, "429.html", status=429)


def metrics(request: HttpRequest) -> HttpResponse:
    """Prometheus scrape endpoint behind basic auth (`METRICS_BASIC_AUTH=user:pass`)."""
    expected = settings.METRICS_BASIC_AUTH
    if not expected:
        # 403 rather than 404: a 404 would be turned into a language redirect by LocaleMiddleware
        return HttpResponse("metrics disabled", status=403, content_type="text/plain")
    header = request.headers.get("Authorization", "")
    provided = ""
    if header.startswith("Basic "):
        try:
            provided = base64.b64decode(header[6:]).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            provided = ""
    if not hmac.compare_digest(provided, expected):
        response = HttpResponse(status=401)
        response["WWW-Authenticate"] = 'Basic realm="metrics"'
        return response
    from django_prometheus.exports import ExportToDjangoView

    return cast(HttpResponse, ExportToDjangoView(request))


def server_error(request: HttpRequest) -> HttpResponse:
    """500 handler that does not depend on the DB (base template must stay DB-free)."""
    with translation.override(translation.get_language() or settings.LANGUAGE_CODE):
        return render(request, "500.html", status=500)
