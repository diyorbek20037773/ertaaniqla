"""Production settings. `manage.py check --deploy` must pass with these."""

import sentry_sdk
from django.core.exceptions import ImproperlyConfigured
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.redis import RedisIntegration

from apps.core.sentry import scrub_sentry_event

from .base import *
from .base import (
    ALLOWED_HOSTS,
    APP_RELEASE,
    ENVIRONMENT,
    PII_ENCRYPTION_KEYS,
    SECRET_KEY,
    TURNSTILE_SECRET_KEY,
    env,
)

DEBUG = False

if SECRET_KEY.startswith("insecure-"):
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set in production")
if not PII_ENCRYPTION_KEYS:
    raise ImproperlyConfigured("PII_ENCRYPTION_KEYS must be set in production")
if not TURNSTILE_SECRET_KEY:
    raise ImproperlyConfigured("TURNSTILE_SECRET_KEY must be set in production (anti-spam)")

# TLS is terminated by nginx; trust its header
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
SECURE_SSL_REDIRECT = True

# Probes that stay inside the compose network and speak plain HTTP to gunicorn: the Docker
# HEALTHCHECK (Host: localhost), Prometheus (Host: web:8000) and deploy smoke checks. nginx
# answers 444 to any Host it does not serve, so these names are unreachable from outside.
ALLOWED_HOSTS = list(dict.fromkeys([*ALLOWED_HOSTS, "localhost", "127.0.0.1", "web"]))
SECURE_REDIRECT_EXEMPT = [r"^healthz/$", r"^readyz/$", r"^metrics$"]
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
LANGUAGE_COOKIE_SECURE = True

WAGTAIL_2FA_REQUIRED = True  # never optional in prod (spec §8)
WAFFLE_FLAG_DEFAULT = False  # tools go live only after medical sign-off (spec M4)

# Anonymous HTML is cached per view (apps.core.cache) — 5 min, stale-while-revalidate 1 h
PAGE_CACHE_SECONDS = env.int("PAGE_CACHE_SECONDS", default=300)

# Sentry: errors + 10% performance, PII scrubbed
_dsn = env("SENTRY_DSN", default="")
if _dsn:
    sentry_sdk.init(
        dsn=_dsn,
        environment=ENVIRONMENT,
        release=APP_RELEASE,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
            LoggingIntegration(level=None, event_level=None),
        ],
        traces_sample_rate=env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.1),
        send_default_pii=False,
        before_send=scrub_sentry_event,
    )
