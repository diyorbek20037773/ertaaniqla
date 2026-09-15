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
