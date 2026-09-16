"""Per-view page cache for anonymous HTML (spec §4.5).

Key = (version, language, path, query, HX-Request). The version is bumped on every
publish/unpublish/move/delete and on Site-settings save (`bump_page_cache`), so stale pages
never survive an edit. The CSP nonce baked into the cached HTML is swapped for the current
request's nonce on every hit. Only 200 text/html GET/HEAD responses without cookies are
cached; nothing is cached for logged-in users or when `PAGE_CACHE_SECONDS` is 0.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse
from django.utils import translation

VERSION_KEY = "page-cache:version"
STALE_WHILE_REVALIDATE = 3600


def cache_seconds() -> int:
    return int(getattr(settings, "PAGE_CACHE_SECONDS", 0) or 0)


def page_cache_version() -> int:
    version = cache.get(VERSION_KEY)
    if version is None:
        cache.set(VERSION_KEY, 1, None)
        return 1
    return int(version)


def bump_page_cache() -> int:
    version = page_cache_version() + 1
    cache.set(VERSION_KEY, version, None)
    return version


def page_cache_key(request: HttpRequest) -> str:
    raw = "|".join(
        [
            str(page_cache_version()),
            translation.get_language() or "",
            request.path,
            request.META.get("QUERY_STRING", ""),
            "hx" if request.headers.get("HX-Request") else "",
        ]
    )
    return "page-cache:" + hashlib.sha256(raw.encode()).hexdigest()


def _cacheable_request(request: HttpRequest) -> bool:
    if cache_seconds() <= 0 or request.method not in ("GET", "HEAD"):
        return False
    if request.COOKIES.get(settings.SESSION_COOKIE_NAME) or request.COOKIES.get("csrftoken"):
        return False
    if getattr(request, "user", None) is not None and request.user.is_authenticated:
        return False
    prefixes = tuple(f"/{code}/" for code, _ in settings.LANGUAGES)
    return request.path.startswith(prefixes)


def _cacheable_response(response: HttpResponse) -> bool:
    if response.status_code != 200 or response.streaming:
        return False
    if not response.get("Content-Type", "").startswith("text/html"):
        return False
    if response.has_header("Set-Cookie") or "no-store" in response.get("Cache-Control", ""):
        return False
    return "private" not in response.get("Cache-Control", "")


class PageCacheMiddleware:
    """Place after CSPMiddleware (so the nonce exists) — see settings MIDDLEWARE."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if not _cacheable_request(request):
            return self.get_response(request)
        key = page_cache_key(request)
        entry: dict[str, Any] | None = cache.get(key)
        # django-csp's lazy nonce is falsy until evaluated — never use `or ""` here
        nonce = str(getattr(request, "csp_nonce", ""))
        if entry is not None:
            body: bytes = entry["body"]
            if entry["nonce"] and nonce:
                body = body.replace(entry["nonce"].encode(), nonce.encode())
            response = HttpResponse(body, status=200, content_type=entry["content_type"])
            for header, value in entry["headers"].items():
                response[header] = value
            response["X-Page-Cache"] = "HIT"
            return response
        response = self.get_response(request)
        if _cacheable_response(response):
            seconds = cache_seconds()
            response["Cache-Control"] = (
                f"public, max-age={seconds}, stale-while-revalidate={STALE_WHILE_REVALIDATE}"
            )
            headers = {
                h: response[h]
                for h in ("Content-Language", "Vary", "Cache-Control", "Content-Security-Policy")
                if response.has_header(h)
            }
            cache.set(
                key,
                {
                    "body": response.content,
                    "nonce": nonce,
                    "content_type": response.get("Content-Type", "text/html; charset=utf-8"),
                    "headers": headers,
                },
                seconds + STALE_WHILE_REVALIDATE,
            )
            response["X-Page-Cache"] = "MISS"
        return response
