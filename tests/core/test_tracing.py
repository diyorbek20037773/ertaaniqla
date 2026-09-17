"""OpenTelemetry tracing (ADR-0005): off by default, PII scrubbed from spans, trace id in logs."""

from __future__ import annotations

import logging

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from apps.core import tracing
from apps.core.logging import RequestIDFilter


@pytest.fixture
def tracer() -> tuple[TracerProvider, InMemorySpanExporter]:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return provider, exporter


def test_tracing_is_off_without_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    monkeypatch.setattr(tracing, "_configured", False)
    assert tracing.tracing_enabled() is False
    assert tracing.configure_tracing("ertaaniqla-test") is False


def test_sdk_disabled_wins_over_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://jaeger:4318")
    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
    assert tracing.tracing_enabled() is False
    monkeypatch.setenv("OTEL_SDK_DISABLED", "false")
    assert tracing.tracing_enabled() is True


@pytest.mark.parametrize(
    ("raw", "clean"),
    [
        ("/uz/qidiruv/?q=ko%27krakda+og%27riq", "/uz/qidiruv/"),
        ("https://ertaaniqla.uz/ru/?utm=1#top", "https://ertaaniqla.uz/ru/"),
        ("/uz/", "/uz/"),
    ],
)
def test_strip_query(raw: str, clean: str) -> None:
    assert tracing.strip_query(raw) == clean


def test_scrub_span_removes_query_ip_and_user_agent(
    tracer: tuple[TracerProvider, InMemorySpanExporter],
) -> None:
    provider, exporter = tracer
    span = provider.get_tracer("t").start_span("GET /uz/qidiruv/")
    span.set_attributes(
        {
            "http.target": "/uz/qidiruv/?q=symptom",
            "url.full": "https://ertaaniqla.uz/uz/qidiruv/?q=symptom",
            "url.query": "q=symptom",
            "url.path": "/uz/qidiruv/",
            "client.address": "203.0.113.7",
            "net.peer.ip": "203.0.113.7",
            "user_agent.original": "Mozilla/5.0",
            "http.route": "uz/qidiruv/",
        }
    )
    tracing.scrub_span(span, object(), object())
    span.end()

    (finished,) = exporter.get_finished_spans()
    attrs = dict(finished.attributes or {})
    assert attrs["http.target"] == "/uz/qidiruv/"
    assert attrs["url.full"] == "https://ertaaniqla.uz/uz/qidiruv/"
    assert attrs["url.path"] == "/uz/qidiruv/"
    assert attrs["http.route"] == "uz/qidiruv/"
    for key in ("url.query", "client.address", "net.peer.ip", "user_agent.original"):
        assert attrs[key] == tracing.REDACTED
    assert "symptom" not in repr(attrs)
    assert "203.0.113.7" not in repr(attrs)


def test_scrub_span_ignores_ended_spans(
    tracer: tuple[TracerProvider, InMemorySpanExporter],
) -> None:
    provider, _ = tracer
    span = provider.get_tracer("t").start_span("x", attributes={"url.query": "q=1"})
    span.end()
    tracing.scrub_span(span)  # must not raise on a non-recording span


def test_trace_id_in_log_records(tracer: tuple[TracerProvider, InMemorySpanExporter]) -> None:
    provider, _ = tracer
    record = logging.LogRecord("ertaaniqla", logging.INFO, __file__, 1, "m", None, None)
    RequestIDFilter().filter(record)
    assert record.trace_id == "-"

    with provider.get_tracer("t").start_as_current_span("request") as span:
        RequestIDFilter().filter(record)
        expected = format(span.get_span_context().trace_id, "032x")
    assert record.trace_id == expected
    assert len(record.trace_id) == 32


def test_configure_tracing_installs_instrumentations(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    def fake(name: str):  # type: ignore[no-untyped-def]
        class _Instrumentor:
            def instrument(self, **kwargs: object) -> None:
                calls.append((name, kwargs))

        return _Instrumentor

    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://127.0.0.1:9")
    monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)
    monkeypatch.setattr(tracing, "_configured", False)
    monkeypatch.setattr("opentelemetry.instrumentation.django.DjangoInstrumentor", fake("django"))
    monkeypatch.setattr(
        "opentelemetry.instrumentation.psycopg.PsycopgInstrumentor", fake("psycopg")
    )
    monkeypatch.setattr("opentelemetry.instrumentation.celery.CeleryInstrumentor", fake("celery"))
    monkeypatch.setattr(tracing.trace, "set_tracer_provider", lambda provider: None)

    assert tracing.configure_tracing("ertaaniqla-test") is True
    assert tracing.configure_tracing("ertaaniqla-test") is True  # idempotent
    assert [name for name, _ in calls] == ["django", "psycopg", "celery"]
    django_kwargs = calls[0][1]
    assert django_kwargs["response_hook"] is tracing.scrub_span
    assert "healthz" in str(django_kwargs["excluded_urls"])
    assert calls[1][1]["enable_commenter"] is False
    monkeypatch.setattr(tracing, "_configured", False)
