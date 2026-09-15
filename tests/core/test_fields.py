"""PII encryption field (spec §8)."""

from __future__ import annotations

import pytest
from cryptography.fernet import Fernet
from django.test import override_settings

from apps.core import fields


@pytest.fixture(autouse=True)
def _reset_keys():
    fields.reset_key_cache()
    yield
    fields.reset_key_cache()


def test_roundtrip() -> None:
    stored = fields.encrypt("+998 90 123-45-67")
    assert stored.startswith("enc:v1:")
    assert "998" not in stored
    assert fields.decrypt(stored) == "+998 90 123-45-67"


def test_unicode_roundtrip() -> None:
    text = "Oʻzbekcha matn, русский текст"
    assert fields.decrypt(fields.encrypt(text)) == text


def test_rotation_reads_old_key_and_writes_newest() -> None:
    old_key = Fernet.generate_key().decode()
    new_key = Fernet.generate_key().decode()
    with override_settings(PII_ENCRYPTION_KEYS=[old_key]):
        fields.reset_key_cache()
        stored_old = fields.encrypt("secret")
    with override_settings(PII_ENCRYPTION_KEYS=[new_key, old_key]):
        fields.reset_key_cache()
        assert fields.decrypt(stored_old) == "secret"
        rotated = fields.rotate(stored_old)
    with override_settings(PII_ENCRYPTION_KEYS=[new_key]):
        fields.reset_key_cache()
        assert fields.decrypt(rotated) == "secret"
        with pytest.raises(ValueError):
            fields.decrypt(stored_old)


def test_field_prep_and_from_db() -> None:
    field = fields.EncryptedCharField(max_length=50)
    prepped = field.get_prep_value("hello")
    assert prepped.startswith("enc:v1:")
    assert field.get_prep_value(prepped) == prepped  # idempotent
    assert field.from_db_value(prepped, None, None) == "hello"
    assert field.get_prep_value("") == ""
    assert field.from_db_value(None, None, None) is None
    assert field.to_python(prepped) == "hello"


def test_char_field_deconstruct_keeps_plaintext_max_length() -> None:
    field = fields.EncryptedCharField(max_length=42)
    _, _, _, kwargs = field.deconstruct()
    assert kwargs["max_length"] == 42
    assert field.formfield().max_length == 42
