"""Distributed tracing with OpenTelemetry → OTLP/HTTP → Jaeger (ADR-0005).

Off unless `OTEL_EXPORTER_OTLP_ENDPOINT` is set, so dev/test pay nothing. Called once per process
*after* fork (gunicorn imports `config.wsgi` in each worker; Celery prefork children run
`worker_process_init`), because the batch exporter owns a background thread.

Sampling, service name and resource attributes use the standard OTEL_* variables
(`OTEL_TRACES_SAMPLER=parentbased_traceidratio`, `OTEL_TRACES_SAMPLER_ARG=0.1`).

Privacy (spec §8): spans keep the path and the route, never the query string (search terms can be
symptoms), client IP, user agent or SQL parameters.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from opentelemetry import trace

logger = logging.getLogger("ertaaniqla.tracing")

# attributes that can carry a query string or a visitor identifier (old + stable semconv)
_URL_ATTRIBUTES = ("http.target", "http.url", "url.full")
_DROP_ATTRIBUTES = (
    "url.query",
    "net.peer.ip",
    "client.address",
    "http.client_ip",
    "http.user_agent",
    "user_agent.original",
    "net.sock.peer.addr",
    "network.peer.address",
)
REDACTED = "[redacted]"
EXCLUDED_URLS = "healthz,readyz,metrics,static/,favicon.ico"

_configured = False


def tracing_enabled() -> bool:
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    disabled = os.environ.get("OTEL_SDK_DISABLED", "").strip().lower() == "true"
    return bool(endpoint) and not disabled


def strip_query(value: str) -> str:
    return value.split("?", 1)[0].split("#", 1)[0]


def scrub_span(span: Any, *_: Any) -> None:
    """Django request/response hook: overwrite attributes that may hold personal data.

    OpenTelemetry has no attribute removal, so values are replaced in place (the response hook
    runs just before the span ends, after every attribute the middleware sets)."""
    if not span.is_recording():
        return
    attributes = getattr(span, "attributes", None) or {}
    for key in _URL_ATTRIBUTES:
        value = attributes.get(key)
        if isinstance(value, str) and ("?" in value or "#" in value):
            span.set_attribute(key, strip_query(value))
    for key in _DROP_ATTRIBUTES:
        if key in attributes:
            span.set_attribute(key, REDACTED)


def configure_tracing(service_name: str) -> bool:
    """Install the tracer provider and the Django/psycopg/Celery instrumentations once.

    Returns True when tracing is active in this process."""
    global _configured
    if _configured:
        return True
    if not tracing_enabled():
        return False

    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.celery import CeleryInstrumentor
    from opentelemetry.instrumentation.django import DjangoInstrumentor
    from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor
    from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    resource = Resource.create(
        {
            SERVICE_NAME: os.environ.get("OTEL_SERVICE_NAME") or service_name,
            SERVICE_VERSION: os.environ.get("APP_RELEASE", "dev"),
            "deployment.environment.name": os.environ.get("ENVIRONMENT", "dev"),
        }
    )
    provider = TracerProvider(resource=resource)  # sampler from OTEL_TRACES_SAMPLER(_ARG)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)

    DjangoInstrumentor().instrument(
        tracer_provider=provider,
        request_hook=scrub_span,
        response_hook=scrub_span,
        excluded_urls=os.environ.get("OTEL_PYTHON_DJANGO_EXCLUDED_URLS", EXCLUDED_URLS),
    )
    # statements only, never bound parameters (capture_parameters defaults to False)
    PsycopgInstrumentor().instrument(tracer_provider=provider, enable_commenter=False)
    CeleryInstrumentor().instrument(tracer_provider=provider)  # type: ignore[no-untyped-call]

    _configured = True
    logger.info("tracing enabled", extra={"service": resource.attributes.get(SERVICE_NAME)})
    return True


def current_trace_id() -> str:
    """Hex trace id of the active span, or "-" (used by the log filter)."""
    context = trace.get_current_span().get_span_context()
    return format(context.trace_id, "032x") if context.is_valid else "-"
