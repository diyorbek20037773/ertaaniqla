"""Private documents (consent forms) are never served to anonymous visitors."""

from __future__ import annotations

import pytest
from django.core.files.base import ContentFile
from django.test import Client

from apps.media_library.models import PortalDocument

pytestmark = pytest.mark.django_db


@pytest.fixture
def documents() -> tuple[PortalDocument, PortalDocument]:
    public = PortalDocument.objects.create(
        title="Public", file=ContentFile(b"%PDF-1.4 p", name="p.pdf")
    )
    private = PortalDocument.objects.create(
        title="Consent", file=ContentFile(b"%PDF-1.4 c", name="c.pdf"), is_private=True
    )
    return public, private


def test_anonymous_gets_public_only(documents, client: Client) -> None:
    public, private = documents
    assert client.get(public.url).status_code == 200
    assert client.get(private.url).status_code == 404


def test_editor_can_download_private(documents, admin_user, client: Client) -> None:
    _, private = documents
    client.force_login(admin_user)
    assert client.get(private.url).status_code == 200


def test_plain_user_without_permission_is_blocked(documents, user, client: Client) -> None:
    _, private = documents
    client.force_login(user)
    assert client.get(private.url).status_code == 404
