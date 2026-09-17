"""WSGI entry point (gunicorn)."""

import os

from django.core.wsgi import get_wsgi_application

from apps.core.tracing import configure_tracing

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")

# gunicorn imports this module in each worker (no --preload), i.e. after fork: safe for the
# exporter thread. Must run before the WSGI handler loads MIDDLEWARE. No-op without OTLP endpoint.
configure_tracing("ertaaniqla-web")

application = get_wsgi_application()
