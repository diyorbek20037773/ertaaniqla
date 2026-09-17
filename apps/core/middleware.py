"""Request-scoped helpers: request id propagation and Permissions-Policy header."""

from __future__ import annotations

import contextvars
import re
import uuid
from collections.abc import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")

REQUEST_ID_HEADER = "X-Request-ID"
_SAFE_ID = re.compile(r"^[A-Za-z0-9\-]{8,64}$")


class RequestIDMiddleware:
    """Attach a request id (from nginx `X-Request-ID` or generated) to the request, the log
    context and the response. No PII involved."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        incoming = request.headers.get(REQUEST_ID_HEADER, "")
        request_id = incoming if _SAFE_ID.fullmatch(incoming) else uuid.uuid4().hex
        request.request_id = request_id  # type: ignore[attr-defined]
        token = request_id_var.set(request_id)
        try:
            response = self.get_response(request)
        finally:
            request_id_var.reset(token)
        response[REQUEST_ID_HEADER] = request_id
        policy = getattr(settings, "PERMISSIONS_POLICY", "")
        if policy and "Permissions-Policy" not in response:
            response["Permissions-Policy"] = policy
        return response


# --- Uzbek Cyrillic site version (/oz/, DECISIONS D-049) ----------------------------------------

CYRILLIC_LANGUAGE_TAG = "uz-Cyrl"
_TAG_TOKEN_RE = re.compile(
    r"(<script\b[^>]*>.*?</script\s*>|<style\b.*?</style\s*>|<!--.*?-->|<[^>]+>)",
    re.IGNORECASE | re.DOTALL,
)
_URL_ATTR_RE = re.compile(
    r"""(\s(?:href|action|formaction|hx-get|hx-post|hx-push-url|data-url|content)=["'])"""
    r"""((?:https?:)?(?://[^/"'\s]+)?)/uz(/|["'?#])""",
    re.IGNORECASE,
)
_ABSOLUTE_URL_RE = re.compile(r"(https?://[^/\"'\s]+)/uz/")
_HTML_LANG_RE = re.compile(r"""(<html\b[^>]*\slang=["'])uz(["'])""", re.IGNORECASE)


def cyrillic_prefix() -> str:
    return "/" + str(getattr(settings, "UZ_CYRILLIC_PREFIX", "oz")).strip("/") + "/"


def is_cyrillic_request(request: HttpRequest | None) -> bool:
    return getattr(request, "uz_script", "") == "cyrl"


def latin_to_cyrillic_path(path: str) -> str:
    """`/uz/…` → `/oz/…` (other paths unchanged)."""
    if path == "/uz" or path.startswith("/uz/"):
        return cyrillic_prefix() + path[4:]
    return path


def _rewrite_urls(html: str) -> str:
    """Point internal `/uz/` links at `/oz/` — except tags marked `data-script-keep` (the Latin
    entries of the language switcher and hreflang)."""
    prefix = cyrillic_prefix()

    def tag(token: str) -> str:
        if token.startswith("<!--") or "data-script-keep" in token[:400]:
            return token
        if token[:7].lower() == "<script":
            if "json" not in token[:120].lower():
                return token
            return _ABSOLUTE_URL_RE.sub(lambda m: m.group(1) + prefix, token)
        token = _URL_ATTR_RE.sub(
            lambda m: f"{m.group(1)}{m.group(2)}{prefix[:-1]}{m.group(3)}", token
        )
        return token.replace("%2Fuz%2F", "%2F" + prefix.strip("/") + "%2F")

    return "".join(
        tag(part) if part.startswith("<") else part for part in _TAG_TOKEN_RE.split(html) if part
    )


def cyrillic_html(html: str) -> str:
    from apps.core.uzcyrl import transliterate_html

    converted = _rewrite_urls(transliterate_html(html))
    return _HTML_LANG_RE.sub(rf"\g<1>{CYRILLIC_LANGUAGE_TAG}\g<2>", converted, count=1)


class UzCyrillicMiddleware:
    """Serve the Uzbek (Latin) tree in Cyrillic under `/oz/` (client answer D-047, D-049).

    The request is rewritten to `/uz/…` before routing, so Wagtail, i18n and the page cache work
    unchanged; the response is transliterated on the way out (text only, see `apps.core.uzcyrl`),
    links are moved to `/oz/`, `lang` becomes `uz-Cyrl`. Converted HTML is cached by the hash of
    the Latin HTML (with the CSP nonce masked), so cached pages cost one hash per request.
    Place after WhiteNoise and before LocaleMiddleware / PageCacheMiddleware.
    """

    NONCE_MASK = "__csp_nonce__"

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        prefix = cyrillic_prefix()
        path = request.path_info
        if not getattr(settings, "UZ_CYRILLIC_ENABLED", True) or not (
            path.startswith(prefix) or path == prefix[:-1]
        ):
            return self.get_response(request)
        if path == prefix[:-1]:
            from django.http import HttpResponsePermanentRedirect

            query = request.META.get("QUERY_STRING", "")
            return HttpResponsePermanentRedirect(prefix + (f"?{query}" if query else ""))
        latin = "/uz/" + path[len(prefix) :]
        request.path_info = latin
        request.path = request.META.get("SCRIPT_NAME", "").rstrip("/") + latin
        request.META["PATH_INFO"] = latin
        request.uz_script = "cyrl"  # type: ignore[attr-defined]
        response = self.get_response(request)
        return self.convert_response(request, response)

    def convert_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        location = response.get("Location", "")
        if location:
            response["Location"] = _ABSOLUTE_URL_RE.sub(
                lambda m: m.group(1) + cyrillic_prefix(), latin_to_cyrillic_path(location)
            )
        if response.has_header("Content-Language"):
            response["Content-Language"] = CYRILLIC_LANGUAGE_TAG
        if response.streaming or not response.content:
            return response
        content_type = response.get("Content-Type", "")
        if content_type.startswith("text/html"):
            body = self._convert_html(request, response.content.decode(response.charset or "utf-8"))
        elif "xml" in content_type:  # per-language sitemap
            body = _ABSOLUTE_URL_RE.sub(
                lambda m: m.group(1) + cyrillic_prefix(), response.content.decode("utf-8")
            )
        else:
            return response
        response.content = body.encode(response.charset or "utf-8")
        if response.has_header("Content-Length"):
            response["Content-Length"] = str(len(response.content))
        return response

    def _convert_html(self, request: HttpRequest, html: str) -> str:
        import hashlib

        from django.core.cache import cache

        nonce = str(getattr(request, "csp_nonce", "") or "")
        masked = html.replace(nonce, self.NONCE_MASK) if nonce else html
        key = "uzcyrl:" + hashlib.sha256(masked.encode()).hexdigest()
        converted: str | None = cache.get(key)
        if converted is None:
            converted = cyrillic_html(masked)
            cache.set(key, converted, 60 * 60)
        return converted.replace(self.NONCE_MASK, nonce) if nonce else converted
