"""Wagtail hooks for the security audit trail (apps/core/audit.py, ADR-0005)."""

from __future__ import annotations

from wagtail import hooks

from apps.core import audit

# call form, not decorators: wagtail.hooks is untyped (mypy strict on apps.core)
hooks.register("register_log_actions", audit.register_log_actions)
hooks.register("before_edit_snippet", audit.before_edit_pii_snippet)
