"""Anti-spam for public forms (spec §6, §8): honeypot + Cloudflare Turnstile + rate limit.

Turnstile verification is skipped when no secret key is configured (dev/test); production
refuses to start without one (config/settings/prod.py).
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from django.conf import settings
from django.http import HttpRequest
from django_ratelimit.core import is_ratelimited

logger = logging.getLogger("ertaaniqla.antispam")

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
FORM_RATE = "5/m"  # spec §6: 5 POSTs per minute per IP


def client_ip(request: HttpRequest) -> str:
    """Client IP as seen by Django (nginx passes the real one; no XFF trust here)."""
    return str(request.META.get("REMOTE_ADDR", "") or "")


def turnstile_enabled() -> bool:
    return bool(getattr(settings, "TURNSTILE_SECRET_KEY", ""))


def verify_turnstile(token: str, remote_ip: str = "") -> bool:
    """True when Turnstile accepts the token (or when Turnstile is not configured)."""
    if not turnstile_enabled():
        return True
    if not token:
        return False
    payload = urllib.parse.urlencode(
        {"secret": settings.TURNSTILE_SECRET_KEY, "response": token, "remoteip": remote_ip}
    ).encode()
    request = urllib.request.Request(TURNSTILE_VERIFY_URL, data=payload, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=5) as response:  # noqa: S310 - fixed https
            data: dict[str, Any] = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        logger.warning("turnstile verification failed: %s", exc)
        return False
    return bool(data.get("success"))


def form_is_ratelimited(request: HttpRequest, group: str) -> bool:
    """Increments the per-IP counter for POSTs and reports whether the limit was exceeded."""
    if request.method != "POST":
        return False
    return bool(
        is_ratelimited(
            request, group=group, key="ip", rate=FORM_RATE, method=["POST"], increment=True
        )
    )
