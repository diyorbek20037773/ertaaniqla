"""Private documents (consent forms) are served only to CMS users (spec §4.3, §8)."""

from __future__ import annotations

from typing import Any

from django.http import Http404, HttpRequest, HttpResponse
from wagtail import hooks


@hooks.register("before_serve_document")
def block_private_documents(document: Any, request: HttpRequest) -> HttpResponse | None:
    if getattr(document, "is_private", False):
        user = request.user
        if not (user.is_authenticated and user.has_perm("wagtaildocs.choose_document")):
            # 404, not 403: do not reveal that a consent document exists
            raise Http404
    return None
