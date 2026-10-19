"""Per-view page cache for anonymous HTML (spec §4.5, D-093).

Key = (build, version, language, script, path, query, HX-Request). The version is bumped on
every publish/unpublish/move/delete and on Site-settings save (`bump_page_cache`), so stale pages
never survive an edit; the build id (static manifest + release) changes with every deploy, so
cached HTML never points at hashed CSS/JS files the new release no longer has. /uz/ and its
Cyrillic view /oz/ (rewritten to /uz/ before this middleware) are separate entries: their
language switch differs. The CSP nonce baked into the cached HTML is swapped for the current
request's nonce on every hit. Only 200 text/html GET/HEAD responses without cookies are cached;
nothing is cached for logged-in users or when `PAGE_CACHE_SECONDS` is 0.

Browsers (D-093): `public, max-age=0, must-revalidate, s-maxage=<shared>` with a weak ETag of
the page without its nonce. Every navigation asks the server, an unchanged page answers
304 Not Modified (a few hundred bytes, no body), and right after a deploy everyone gets the new
release instead of a copy kept for up to an hour. A 304 carries no Content-Security-Policy: the
browser re-renders its stored copy, whose inline nonce matches the policy stored with it, and a
new policy on the 304 would replace that one. `s-maxage` lets the nginx micro-cache keep a page
for `PAGE_CACHE_SHARED_SECONDS` (spec §4.5.1).
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from functools import cache as memoize
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse, HttpResponseNotModified
from django.utils import translation
from django.utils.http import parse_etags

VERSION_KEY = "page-cache:version"
REVALIDATED_HEADERS = ("Cache-Control", "ETag", "Vary", "Content-Language", "X-Page-Cache")


def cache_seconds() -> int:
    return int(getattr(settings, "PAGE_CACHE_SECONDS", 0) or 0)


def html_cache_control() -> str:
    """Browsers revalidate every use (the ETag makes that a 304); shared caches (nginx) may
    keep the page for `PAGE_CACHE_SHARED_SECONDS`."""
    shared = int(getattr(settings, "PAGE_CACHE_SHARED_SECONDS", 10) or 0)
    return f"public, max-age=0, must-revalidate, s-maxage={shared}"


@memoize
def build_id() -> str:
    """Identity of the deployed release: hash of the staticfiles manifest plus APP_RELEASE (a
    deploy that changes code or templates but no static file still gets new keys and ETags).
    Without a manifest (dev, tests) it is APP_RELEASE."""
    release = str(getattr(settings, "APP_RELEASE", "dev"))
    manifest = Path(settings.STATIC_ROOT or "") / "staticfiles.json"
    try:
        data = manifest.read_bytes()
    except OSError:
        return release
    return hashlib.sha256(data + b"|" + release.encode()).hexdigest()[:12]


def page_etag(body: bytes, nonce: str) -> str:
    """Weak ETag of a page: its body without this response's CSP nonce, plus the release."""
    masked = body.replace(nonce.encode(), b"") if nonce else body
    digest = hashlib.sha256(build_id().encode() + b"|" + masked).hexdigest()[:20]
    return f'W/"{digest}"'


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
            build_id(),
            str(page_cache_version()),
            translation.get_language() or "",
            str(getattr(request, "uz_script", "")),  # /oz/ is served from the /uz/ view
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


def _not_modified(request: HttpRequest, headers: dict[str, str]) -> HttpResponse | None:
    """304 when the browser already holds this version (If-None-Match, weak comparison).
    If-Match / If-Unmodified-Since are ignored on purpose: they would turn a weak ETag into 412s."""
    etag = headers.get("ETag", "")
    tags = parse_etags(request.headers.get("If-None-Match", ""))
    if not etag or not tags:
        return None
    if tags != ["*"] and etag.removeprefix("W/") not in {t.removeprefix("W/") for t in tags}:
        return None
    response = HttpResponseNotModified()
    for header in REVALIDATED_HEADERS:
        if header in headers:
            response[header] = headers[header]
    response._csp_exempt = True  # type: ignore[attr-defined]  # django-csp: no policy on a 304
    return response


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
            headers = {**entry["headers"], "X-Page-Cache": "HIT"}
            not_modified = _not_modified(request, headers)
            if not_modified is not None:
                return not_modified  # before the nonce swap of a 36 KB body
            body: bytes = entry["body"]
            if entry["nonce"] and nonce:
                body = body.replace(entry["nonce"].encode(), nonce.encode())
            response = HttpResponse(body, status=200, content_type=entry["content_type"])
            for header, value in headers.items():
                response[header] = value
            return response
        response = self.get_response(request)
        if request.META.get("CSRF_COOKIE_NEEDS_UPDATE"):
            # The page rendered {% csrf_token %}: CsrfViewMiddleware adds the cookie only after
            # this middleware, so caching it would hand the next visitor someone else's token
            # and no cookie — a 403 on submit (EA-25).
            response["Cache-Control"] = "private, no-cache"
            return response
        if _cacheable_response(response):
            response["Cache-Control"] = html_cache_control()
            # the ETag comes from the content, so a returning browser gets a 304 even after its
            # server entry expired or was evicted
            response["ETag"] = page_etag(response.content, nonce)
            headers = {
                h: response[h]
                for h in ("Content-Language", "Vary", "Cache-Control", "ETag")
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
                cache_seconds(),
            )
            response["X-Page-Cache"] = "MISS"
            not_modified = _not_modified(request, {**headers, "X-Page-Cache": "MISS"})
            if not_modified is not None:
                return not_modified
        return response
