"""Test settings: fast hashing, eager Celery, local-memory cache, locmem email, no axes/2FA."""

from .base import *
from .base import BASE_DIR, MIDDLEWARE, env

DEBUG = False
SECRET_KEY = "test-secret-key-not-for-production-use-0123456789"  # noqa: S105
ALLOWED_HOSTS = ["*"]
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Postgres is required (FTS, unaccent, JSONB). CI provides it; locally use compose or PG18.
DATABASES["default"] = env.db_url(
    "TEST_DATABASE_URL",
    default=env(
        "DATABASE_URL", default="postgres://ertaaniqla:ertaaniqla@localhost:5433/ertaaniqla"
    ),
)
DATABASES["default"]["ENGINE"] = "django.db.backends.postgresql"
DATABASES["default"]["CONN_MAX_AGE"] = 0

CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "KEY_PREFIX": "t"},
    "renditions": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
}
SESSION_ENGINE = "django.contrib.sessions.backends.db"

CELERY_TASK_ALWAYS_EAGER = True
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

STORAGES["staticfiles"] = {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}
MEDIA_ROOT = str(BASE_DIR / ".pytest_cache" / "media")
WHITENOISE_AUTOREFRESH = True

# Deterministic PII key for tests
PII_ENCRYPTION_KEYS = ["AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="]

WAGTAIL_2FA_REQUIRED = False
AXES_ENABLED = False
MIDDLEWARE.remove("django_prometheus.middleware.PrometheusBeforeMiddleware")
MIDDLEWARE.remove("django_prometheus.middleware.PrometheusAfterMiddleware")
WAFFLE_FLAG_DEFAULT = True
TURNSTILE_SITE_KEY = ""
TURNSTILE_SECRET_KEY = ""

LOGGING["root"]["level"] = "WARNING"
