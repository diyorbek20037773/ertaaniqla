"""Development settings: debug toolbar, Mailpit, plain logs, relaxed CSP for hot reload."""

from .base import *
from .base import BASE_DIR, INSTALLED_APPS, LOGGING, MIDDLEWARE, env

DEBUG = env.bool("DJANGO_DEBUG", default=True)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["*"])
INTERNAL_IPS = ["127.0.0.1", "::1", "10.0.2.2"]

INSTALLED_APPS += ["debug_toolbar", "wagtail.contrib.styleguide"]
MIDDLEWARE.insert(
    MIDDLEWARE.index("django.middleware.common.CommonMiddleware"),
    "debug_toolbar.middleware.DebugToolbarMiddleware",
)
DEBUG_TOOLBAR_CONFIG = {
    # docker: the browser IP is not in INTERNAL_IPS
    "SHOW_TOOLBAR_CALLBACK": lambda request: DEBUG and not request.headers.get("HX-Request"),
}

# Non-hashed static files while developing (no collectstatic needed)
STORAGES["staticfiles"] = {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}
WHITENOISE_AUTOREFRESH = True
WHITENOISE_USE_FINDERS = True

# 2FA can be turned off locally via CMS_2FA_REQUIRED=false
WAGTAIL_2FA_REQUIRED = env.bool("CMS_2FA_REQUIRED", default=False)
WAFFLE_FLAG_DEFAULT = True  # tools visible in dev (spec M4)

EMAIL_BACKEND = env("DJANGO_EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")

LOGGING["handlers"]["console"]["formatter"] = "plain"

# Cache falls back to local memory when Redis is not running locally
if env.bool("DEV_LOCMEM_CACHE", default=False):
    CACHES = {
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
        "renditions": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    }
    SESSION_ENGINE = "django.contrib.sessions.backends.db"

CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=True)

# Tailwind CLI watch output
TAILWIND_SRC = BASE_DIR / "static" / "src" / "input.css"
