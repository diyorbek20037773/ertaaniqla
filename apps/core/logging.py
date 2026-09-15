"""Logging helpers: inject the current request id into every log record."""

from __future__ import annotations

import logging

from apps.core.middleware import request_id_var


class RequestIDFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True
