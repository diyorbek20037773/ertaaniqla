"""Application-level PII encryption (spec §8).

`EncryptedTextField` stores Fernet ciphertext in a TextField. Keys come from
`settings.PII_ENCRYPTION_KEYS` (newest first) so rotation = prepend a key, run
`manage.py rotate_pii_keys`, drop the old key. Values are opaque in the DB, in dumps and in
Django admin list views. Not searchable by design.
"""

from __future__ import annotations

from collections.abc import Sequence
from functools import lru_cache
from typing import Any

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models

_PREFIX = "enc:v1:"


@lru_cache(maxsize=1)
def _fernet() -> MultiFernet:
    keys: list[str] = list(getattr(settings, "PII_ENCRYPTION_KEYS", []))
    if not keys:
        if not settings.DEBUG and getattr(settings, "ENVIRONMENT", "dev") == "prod":
            raise ImproperlyConfigured("PII_ENCRYPTION_KEYS is empty")
        # dev/test convenience: a per-process key — data does not survive restarts
        keys = [Fernet.generate_key().decode()]
    return MultiFernet([Fernet(k.encode() if isinstance(k, str) else k) for k in keys])


def reset_key_cache() -> None:
    """For tests and the rotation command."""
    _fernet.cache_clear()


def encrypt(plaintext: str) -> str:
    return _PREFIX + _fernet().encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt(stored: str) -> str:
    if not stored.startswith(_PREFIX):
        # legacy/plain value (should not happen) — return as is rather than crash
        return stored
    token = stored[len(_PREFIX) :].encode("ascii")
    try:
        return _fernet().decrypt(token).decode("utf-8")
    except InvalidToken as exc:  # pragma: no cover - only with wrong keys
        raise ValueError("PII value cannot be decrypted with the configured keys") from exc


def rotate(stored: str) -> str:
    """Re-encrypt with the newest key (used by `rotate_pii_keys`)."""
    if not stored.startswith(_PREFIX):
        return encrypt(stored)
    token = stored[len(_PREFIX) :].encode("ascii")
    return _PREFIX + _fernet().rotate(token).decode("ascii")


class EncryptedTextField(models.TextField):
    """TextField whose value is Fernet-encrypted at rest. Empty strings stay empty."""

    description = "Encrypted text (Fernet)"

    def get_prep_value(self, value: Any) -> Any:
        if isinstance(value, str) and value.startswith(_PREFIX):
            return value  # already ciphertext (e.g. re-saving an unchanged instance)
        value = super().get_prep_value(value)
        if value is None or value == "":
            return value
        return encrypt(str(value))

    def from_db_value(self, value: Any, expression: Any, connection: Any) -> Any:
        if value is None or value == "":
            return value
        return decrypt(value)

    def to_python(self, value: Any) -> Any:
        if isinstance(value, str) and value.startswith(_PREFIX):
            return decrypt(value)
        return super().to_python(value)


class EncryptedCharField(EncryptedTextField):
    """Same as EncryptedTextField but validated to `max_length` characters of plaintext
    (ciphertext is longer, so it is still stored in a TEXT column)."""

    def __init__(self, *args: Any, max_length: int = 255, **kwargs: Any) -> None:
        self.plaintext_max_length = max_length
        kwargs.pop("max_length", None)
        super().__init__(*args, **kwargs)

    def deconstruct(self) -> tuple[str, str, Sequence[Any], dict[str, Any]]:
        name, path, args, kwargs = super().deconstruct()
        kwargs["max_length"] = self.plaintext_max_length
        return name, path, args, kwargs

    def formfield(self, **kwargs: Any) -> Any:
        from django import forms

        defaults: dict[str, Any] = {
            "max_length": self.plaintext_max_length,
            "widget": forms.TextInput,
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)
