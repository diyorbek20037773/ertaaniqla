"""Celery application. Imported by config/__init__.py so tasks autodiscover on Django start."""

import os
from typing import Any

from celery import Celery
from celery.signals import beat_init, worker_process_init

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("ertaaniqla")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@worker_process_init.connect(weak=False)
def _init_worker_tracing(**kwargs: Any) -> None:
    """Tracing per prefork child (after fork). No-op without OTEL_EXPORTER_OTLP_ENDPOINT."""
    from apps.core.tracing import configure_tracing

    configure_tracing("ertaaniqla-worker")


@beat_init.connect(weak=False)
def _init_beat_tracing(**kwargs: Any) -> None:
    from apps.core.tracing import configure_tracing

    configure_tracing("ertaaniqla-beat")
