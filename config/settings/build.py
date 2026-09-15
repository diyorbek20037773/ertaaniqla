"""Settings used only inside `docker build` (collectstatic / compilemessages).

No DB, no Redis, no secrets are available at build time, so this is `base` with dummies.
Never used at runtime.
"""

from .base import *

DEBUG = False
SECRET_KEY = "build-only-not-a-secret"  # noqa: S105
CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"},
    "renditions": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"},
}
