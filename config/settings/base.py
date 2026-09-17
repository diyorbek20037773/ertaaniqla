"""Base settings shared by every environment.

Everything configurable comes from the environment (django-environ); see `.env.example`
for the full list. Environment-specific overrides live in dev.py / prod.py / test.py.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import environ
from celery.schedules import crontab
from csp.constants import NONCE, NONE, SELF
from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
# .env is optional (containers get real env vars); read it when present.
environ.Env.read_env(BASE_DIR / ".env")

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
SECRET_KEY = env("DJANGO_SECRET_KEY", default="insecure-dev-key-change-me")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])
SITE_BASE_URL = env("SITE_BASE_URL", default="http://localhost:8000")
ENVIRONMENT = env("ENVIRONMENT", default="dev")
APP_RELEASE = env("APP_RELEASE", default="dev")
CMS_URL_PREFIX = env("CMS_URL_PREFIX", default="cms").strip("/")

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "users.User"
SITE_ID = 1

INSTALLED_APPS = [
    # project apps first so their templates/static override third-party ones
    "apps.core",
    "apps.users",
    "apps.home",
    "apps.sections",
    "apps.articles",
    "apps.media_library",
    "apps.directory",
    "apps.tools",
    "apps.stories",
    "apps.faq",
    "apps.glossary",
    "apps.feedback",
    "apps.search",
    "apps.analytics",
    # wagtail
    "wagtail_localize",
    "wagtail_localize.locales",
    "wagtail.contrib.forms",
    "wagtail.contrib.redirects",
    "wagtail.contrib.settings",
    "wagtail.contrib.table_block",
    "wagtail.contrib.typed_table_block",
    "wagtail.contrib.routable_page",
    "wagtail.embeds",
    "wagtail.sites",
    "wagtail.users",
    "wagtail.snippets",
    "wagtail.documents",
    "wagtail.images",
    "wagtail.search",
    "wagtail.admin",
    "wagtail",
    "modelcluster",
    "taggit",
    # security / auth
    "django_otp",
    "django_otp.plugins.otp_totp",
    "wagtail_2fa",
    "axes",
    "csp",
    # misc third-party
    "crispy_forms",
    "crispy_tailwind",
    "waffle",
    "django_prometheus",
    "django_extensions",
    # django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    "django.contrib.postgres",
]

MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "apps.core.middleware.RequestIDMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "wagtail_2fa.middleware.VerifyUserMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "csp.middleware.CSPMiddleware",
    "apps.core.cache.PageCacheMiddleware",  # anonymous HTML cache (PAGE_CACHE_SECONDS)
    "axes.middleware.AxesMiddleware",
    "waffle.middleware.WaffleMiddleware",
    "wagtail.contrib.redirects.middleware.RedirectMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "wagtail.contrib.settings.context_processors.settings",
                "apps.core.context_processors.site_context",
            ],
        },
    },
]

# ---------------------------------------------------------------------------
# Database / cache / sessions
# ---------------------------------------------------------------------------
DATABASES = {
    "default": env.db_url(
        "DATABASE_URL",
        default="postgres://ertaaniqla:ertaaniqla@localhost:5433/ertaaniqla",
    ),
}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=60)
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True
DATABASES["default"]["ENGINE"] = "django_prometheus.db.backends.postgresql"

REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "KEY_PREFIX": "ea",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            # Fail soft: if Redis is down the site keeps serving (errors logged, not raised)
            "IGNORE_EXCEPTIONS": True,
        },
    },
    "renditions": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "KEY_PREFIX": "ea-rend",
        "TIMEOUT": 60 * 60 * 24,
        "OPTIONS": {"IGNORE_EXCEPTIONS": True},
    },
}
DJANGO_REDIS_LOG_IGNORED_EXCEPTIONS = True

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"
SESSION_COOKIE_AGE = 60 * 60 * 8  # 8 h CMS session timeout (spec §8)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = False  # HTMX reads it for the X-CSRFToken header
CSRF_COOKIE_SAMESITE = "Lax"

# ---------------------------------------------------------------------------
# Auth / security
# ---------------------------------------------------------------------------
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LOGIN_URL = f"/{CMS_URL_PREFIX}/login/"

# django-axes: lock out after 5 failed attempts for 1 hour, per username+IP
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1  # hours
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_TEMPLATE = "core/lockout.html"
AXES_ENABLE_ACCESS_FAILURE_LOG = True

# wagtail-2fa
WAGTAIL_2FA_REQUIRED = env.bool("CMS_2FA_REQUIRED", default=True)
WAGTAIL_2FA_OTP_TOTP_NAME = "Erta aniqla CMS"

# PII encryption (Fernet, comma-separated keys newest first). Empty = generated per-process
# in dev/test only; prod refuses to start without keys (checked in prod.py).
PII_ENCRYPTION_KEYS = [k for k in env.list("PII_ENCRYPTION_KEYS", default=[]) if k]

# Content Security Policy (django-csp 4.x). Nonce-based; embeds explicitly allowed.
CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": [SELF],
        "script-src": [SELF, NONCE, "https://mc.yandex.ru", "https://challenges.cloudflare.com"],
        "style-src": [SELF, NONCE],
        "img-src": [
            SELF,
            "data:",
            "blob:",
            "https://mc.yandex.ru",
            "https://*.tile.openstreetmap.org",
        ],
        "font-src": [SELF],
        "connect-src": [SELF, "https://mc.yandex.ru", "https://challenges.cloudflare.com"],
        "media-src": [SELF, "blob:"],
        "frame-src": [
            "https://www.youtube-nocookie.com",
            "https://www.youtube.com",
            "https://t.me",
            "https://www.instagram.com",
            "https://www.tiktok.com",
            "https://challenges.cloudflare.com",
        ],
        "frame-ancestors": [NONE],
        "form-action": [SELF],
        "base-uri": [SELF],
        "object-src": [NONE],
        "upgrade-insecure-requests": True,
    },
    "EXCLUDE_URL_PREFIXES": (f"/{CMS_URL_PREFIX}/", "/django-admin/"),
}

X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
# Permissions-Policy is emitted by nginx (docker/nginx/snippets/security.conf) and by
# apps.core.middleware.PermissionsPolicyMiddleware for non-nginx setups.
PERMISSIONS_POLICY = "camera=(), microphone=(), geolocation=(self), payment=(), usb=()"

# django-ratelimit uses the default cache (Redis)
RATELIMIT_USE_CACHE = "default"
RATELIMIT_VIEW = "apps.core.views.ratelimited"

# Cloudflare Turnstile (empty = disabled, only allowed outside prod)
TURNSTILE_SITE_KEY = env("TURNSTILE_SITE_KEY", default="")
TURNSTILE_SECRET_KEY = env("TURNSTILE_SECRET_KEY", default="")

# ---------------------------------------------------------------------------
# i18n (spec §7): uz (Latin) default, ru; uz-Cyrl / en can be added later
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "uz"
LANGUAGES = [
    ("uz", "Oʻzbekcha"),
    ("ru", "Русский"),
]
WAGTAIL_CONTENT_LANGUAGES = LANGUAGES
WAGTAIL_I18N_ENABLED = True
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "Asia/Tashkent"
USE_I18N = True
USE_TZ = True
LANGUAGE_COOKIE_NAME = "lang"
LANGUAGE_COOKIE_AGE = 60 * 60 * 24 * 365
LANGUAGE_COOKIE_SAMESITE = "Lax"

# ---------------------------------------------------------------------------
# Static / media
# ---------------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]
MEDIA_URL = "/media/"
MEDIA_ROOT = env("MEDIA_ROOT", default=str(BASE_DIR / "media"))
WHITENOISE_MAX_AGE = 60 * 60 * 24 * 365

MEDIA_STORAGE = env("MEDIA_STORAGE", default="local")
if MEDIA_STORAGE == "s3":
    _s3_options = {
        "endpoint_url": env("S3_ENDPOINT_URL"),
        "bucket_name": env("S3_BUCKET_NAME"),
        "access_key": env("S3_ACCESS_KEY_ID"),
        "secret_key": env("S3_SECRET_ACCESS_KEY"),
        "region_name": env("S3_REGION", default=""),
        "default_acl": "private",
        "querystring_auth": True,
        "file_overwrite": False,
    }
    _default_storage = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": _s3_options,
    }
else:
    _default_storage = {"BACKEND": "django.core.files.storage.FileSystemStorage"}

STORAGES = {
    "default": _default_storage,
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

DATA_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024
MAX_IMAGE_UPLOAD_BYTES = env.int("MAX_IMAGE_UPLOAD_BYTES", default=20 * 1024 * 1024)
MAX_VIDEO_UPLOAD_BYTES = env.int("MAX_VIDEO_UPLOAD_BYTES", default=512 * 1024 * 1024)
MAX_DOCUMENT_UPLOAD_BYTES = env.int("MAX_DOCUMENT_UPLOAD_BYTES", default=50 * 1024 * 1024)
FFMPEG_BINARY = env("FFMPEG_BINARY", default="ffmpeg")
OG_IMAGE_FONT_DIR = BASE_DIR / "static" / "fonts"  # DejaVu (Latin + Cyrillic + U+02BB)
CLAMAV_HOST = env("CLAMAV_HOST", default="")
CLAMAV_PORT = env.int("CLAMAV_PORT", default=3310)

# ---------------------------------------------------------------------------
# Wagtail
# ---------------------------------------------------------------------------
WAGTAIL_SITE_NAME = "Erta aniqla"
WAGTAILADMIN_BASE_URL = SITE_BASE_URL
WAGTAILADMIN_PATH = f"/{CMS_URL_PREFIX}/"
WAGTAIL_FRONTEND_LOGIN_URL = LOGIN_URL
WAGTAILIMAGES_MAX_UPLOAD_SIZE = MAX_IMAGE_UPLOAD_BYTES
WAGTAILIMAGES_EXTENSIONS = ["gif", "jpg", "jpeg", "png", "webp", "avif", "svg"]
WAGTAILIMAGES_IMAGE_MODEL = "media_library.PortalImage"
WAGTAILIMAGES_FORMAT_CONVERSIONS = {"bmp": "jpeg", "webp": "webp", "jpeg": "jpeg", "png": "png"}
WAGTAILDOCS_DOCUMENT_MODEL = "media_library.PortalDocument"
WAGTAILDOCS_EXTENSIONS = ["pdf", "docx", "xlsx", "pptx", "odt", "txt", "csv", "vtt", "srt", "zip"]
WAGTAILDOCS_SERVE_METHOD = "serve_view"  # private consent documents need a permission check
WAGTAILEMBEDS_RESPONSIVE_HTML = True
WAGTAIL_ALLOW_UNICODE_SLUGS = False
WAGTAIL_PASSWORD_RESET_ENABLED = True
WAGTAIL_MODERATION_ENABLED = False  # legacy moderation off; workflows are used instead
WAGTAIL_WORKFLOW_ENABLED = True
# publish + stamp "verified by a doctor" when the medical review task approved (apps.users.roles)
WAGTAIL_FINISH_WORKFLOW_ACTION = "apps.users.workflows.publish_with_medical_review"
WAGTAIL_ENABLE_UPDATE_CHECK = False
WAGTAILADMIN_RICH_TEXT_EDITORS = {
    "default": {
        "WIDGET": "wagtail.admin.rich_text.DraftailRichTextArea",
        "OPTIONS": {
            "features": [
                "h2",
                "h3",
                "bold",
                "italic",
                "ol",
                "ul",
                "link",
                "document-link",
                "image",
                "embed",
            ]
        },
    },
    "minimal": {
        "WIDGET": "wagtail.admin.rich_text.DraftailRichTextArea",
        "OPTIONS": {"features": ["bold", "italic", "link"]},
    },
}
WAGTAILSEARCH_BACKENDS = {
    "default": {
        "BACKEND": "wagtail.search.backends.database",
        "SEARCH_CONFIG": "ertaaniqla",  # custom text search config with unaccent (core migration)
    }
}
WAGTAIL_LOCALIZE_DEFAULT_TRANSLATION_MODE = "simple"
WAGTAIL_I18N_LANGUAGE_SWITCH_FALLBACK = True

# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/1")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://localhost:6379/2")
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_TIME_LIMIT = 60 * 30  # video transcoding
CELERY_TASK_SOFT_TIME_LIMIT = 60 * 25
CELERY_TIMEZONE = TIME_ZONE
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_TASK_DEFAULT_QUEUE = "default"
CELERY_TASK_ROUTES = {
    "media_library.*": {"queue": "media"},
    "core.generate_og_image": {"queue": "media"},
}
CELERY_BEAT_SCHEDULE: dict[str, dict[str, object]] = {
    # PII retention (spec §8): question contacts 90 d after the answer, feedback 180 d
    "faq-purge-contacts": {"task": "faq.purge_contacts", "schedule": crontab(hour=3, minute=0)},
    "feedback-purge": {
        "task": "feedback.purge_old_submissions",
        "schedule": crontab(hour=3, minute=15),
    },
}

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
_email = env.email_url("EMAIL_URL", default="smtp://localhost:1025")
EMAIL_BACKEND = _email["EMAIL_BACKEND"]
EMAIL_HOST = _email.get("EMAIL_HOST", "localhost")
EMAIL_PORT = _email.get("EMAIL_PORT", 1025)
EMAIL_HOST_USER = _email.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = _email.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = _email.get("EMAIL_USE_TLS", False)
EMAIL_USE_SSL = _email.get("EMAIL_USE_SSL", False)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@ertaaniqla.uz")
SERVER_EMAIL = DEFAULT_FROM_EMAIL
MODERATION_EMAIL = env("MODERATION_EMAIL", default="editor@ertaaniqla.uz")
WAGTAILADMIN_NOTIFICATION_FROM_EMAIL = DEFAULT_FROM_EMAIL

# ---------------------------------------------------------------------------
# Forms / misc
# ---------------------------------------------------------------------------
CRISPY_ALLOWED_TEMPLATE_PACKS = "tailwind"
CRISPY_TEMPLATE_PACK = "tailwind"
WAFFLE_FLAG_DEFAULT = False
WAFFLE_CREATE_MISSING_FLAGS = True
PROMETHEUS_EXPORT_MIGRATIONS = False
METRICS_BASIC_AUTH = env("METRICS_BASIC_AUTH", default="")

# Analytics (loaded only after consent; see apps.analytics)
YANDEX_METRIKA_ID = env("YANDEX_METRIKA_ID", default="")
YANDEX_WEBMASTER_VERIFICATION = env("YANDEX_WEBMASTER_VERIFICATION", default="")
GOOGLE_SITE_VERIFICATION = env("GOOGLE_SITE_VERIFICATION", default="")

# Anonymous page cache (spec §4.5); 0 disables (dev/test), prod sets 300
PAGE_CACHE_SECONDS = env.int("PAGE_CACHE_SECONDS", default=0)

# Data retention (days) — spec §8
PII_RETENTION_QUESTION_CONTACT_DAYS = 90
PII_RETENTION_FEEDBACK_DAYS = 180

# Domains: canonical + alias (TZ mentions both)
CANONICAL_DOMAIN = "ertaaniqla.uz"
ALIAS_DOMAINS = ["oncoportal.uz"]

# ---------------------------------------------------------------------------
# Logging: JSON to stdout, request id, no PII
# ---------------------------------------------------------------------------
LOG_LEVEL = env("LOG_LEVEL", default="INFO")
LOGGING: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_id": {"()": "apps.core.logging.RequestIDFilter"},
    },
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.json.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(request_id)s %(message)s",
        },
        "plain": {"format": "%(levelname)s %(name)s [%(request_id)s] %(message)s"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "filters": ["request_id"],
        },
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {
        "django": {"level": LOG_LEVEL},
        "django.request": {"level": "WARNING"},
        "django.security": {"level": "WARNING"},
        "axes": {"level": "INFO"},
        "celery": {"level": LOG_LEVEL},
        "ertaaniqla": {"level": LOG_LEVEL},
    },
}

# Human-readable names used in admin and emails
PROJECT_NAME_UZ = _("Erta aniqla")
