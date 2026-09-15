"""Production settings must refuse insecure configuration and pass `check --deploy`."""

from __future__ import annotations

import importlib
import os
import sys
from collections.abc import Iterator

import pytest
from django.core.exceptions import ImproperlyConfigured

PROD_ENV = {
    "DJANGO_SECRET_KEY": "test-only-secret-key-with-more-than-fifty-characters-0123456789",
    "DJANGO_ALLOWED_HOSTS": "ertaaniqla.uz",
    "DJANGO_CSRF_TRUSTED_ORIGINS": "https://ertaaniqla.uz",
    "PII_ENCRYPTION_KEYS": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
    "TURNSTILE_SECRET_KEY": "dummy",
    "SENTRY_DSN": "",
}


@pytest.fixture
def prod_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for key, value in PROD_ENV.items():
        monkeypatch.setenv(key, value)
    # base.py is import-time cached; drop both so env vars are re-read
    sys.modules.pop("config.settings.prod", None)
    sys.modules.pop("config.settings.base", None)
    yield
    sys.modules.pop("config.settings.prod", None)
    sys.modules.pop("config.settings.base", None)


def _load_prod():
    return importlib.import_module("config.settings.prod")


def test_prod_settings_are_hardened(prod_env: None) -> None:
    prod = _load_prod()
    assert prod.DEBUG is False
    assert prod.SECURE_SSL_REDIRECT is True
    assert prod.SECURE_HSTS_SECONDS >= 31536000
    assert prod.SESSION_COOKIE_SECURE and prod.CSRF_COOKIE_SECURE
    assert prod.WAGTAIL_2FA_REQUIRED is True
    assert prod.WAFFLE_FLAG_DEFAULT is False
    assert prod.X_FRAME_OPTIONS == "DENY"


@pytest.mark.parametrize(
    "missing",
    ["DJANGO_SECRET_KEY", "PII_ENCRYPTION_KEYS", "TURNSTILE_SECRET_KEY"],
)
def test_prod_refuses_to_start_without_secrets(
    prod_env: None, monkeypatch: pytest.MonkeyPatch, missing: str
) -> None:
    monkeypatch.setenv(missing, "insecure-x" if missing == "DJANGO_SECRET_KEY" else "")
    with pytest.raises(ImproperlyConfigured):
        _load_prod()


def test_prod_check_deploy_passes(prod_env: None) -> None:
    """`manage.py check --deploy` with prod settings in a subprocess (settings are import-time)."""
    import subprocess

    env = {**os.environ, **PROD_ENV, "DJANGO_SETTINGS_MODULE": "config.settings.prod"}
    result = subprocess.run(
        [sys.executable, "manage.py", "check", "--deploy", "--fail-level", "WARNING"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
