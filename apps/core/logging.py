"""Logging helpers: inject the current request id and trace id into every log record."""

from __future__ import annotations

import logging

from apps.core.middleware import request_id_var
from apps.core.tracing import current_trace_id

# `level` for hosts that read a lowercase level from JSON logs (Railway, D-074); Loki keeps
# using `levelname`
_HOST_LEVELS = {"WARNING": "warn", "CRITICAL": "error"}


class RequestIDFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        record.level = _HOST_LEVELS.get(record.levelname, record.levelname.lower())
        # links a log line to its trace in Grafana (Loki derived field → Jaeger)
        record.trace_id = current_trace_id()
        return True
