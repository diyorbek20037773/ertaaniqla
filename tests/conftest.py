"""Shared pytest fixtures."""

from __future__ import annotations

import pytest
from django.test import Client


@pytest.fixture
def client() -> Client:
    return Client()


@pytest.fixture
def user(db, django_user_model):
    return django_user_model.objects.create_user(
        username="editor", email="editor@example.uz", password="correct-horse-battery-staple"
    )


@pytest.fixture
def admin_user(db, django_user_model):
    return django_user_model.objects.create_superuser(
        username="admin", email="admin@example.uz", password="correct-horse-battery-staple"
    )
