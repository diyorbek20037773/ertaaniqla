"""Wagtail hooks: the security audit trail (apps/core/audit.py, ADR-0005) and hidden sections
(D-087)."""

from __future__ import annotations

from typing import Any

from django.http import Http404
from wagtail import hooks

from apps.core import audit, visibility


def hide_switched_off_sections(page: Any, request: Any, *args: Any, **kwargs: Any) -> None:
    """A page of a hidden section answers 404 to visitors; CMS previews do not pass here."""
    if visibility.page_is_hidden(page):
        raise Http404


# call form, not decorators: wagtail.hooks is untyped (mypy strict on apps.core)
hooks.register("register_log_actions", audit.register_log_actions)
hooks.register("before_edit_snippet", audit.before_edit_pii_snippet)
hooks.register("before_serve_page", hide_switched_off_sections)
