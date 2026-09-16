"""Feedback form (F5) + 180-day retention."""

from __future__ import annotations

import pytest
from django.test import Client
from freezegun import freeze_time

from apps.feedback.models import FeedbackPage, FeedbackSubmission
from apps.feedback.services import purge_old_submissions

pytestmark = pytest.mark.django_db

VALID = {
    "kind": "bug",
    "text": "Xarita ochilmayapti",
    "contact": "me@example.uz",
    "page_url": "/uz/ayollar/",
    "consent_privacy": "on",
    "website": "",
}


@pytest.fixture
def page(seeded) -> FeedbackPage:
    return FeedbackPage.objects.get(locale__language_code="uz")


def test_render_both_languages_and_prefilled_page(seeded, client: Client) -> None:
    assert client.get("/ru/obratnaya-svyaz/").status_code == 200
    html = client.get("/uz/qayta-aloqa/?from=/uz/bolalar/").content.decode()
    assert 'value="/uz/bolalar/"' in html


def test_submit_stores_submission(page, client: Client) -> None:
    response = client.post(page.url, VALID, HTTP_USER_AGENT="Mozilla/5.0 test")
    assert "form-success" in response.content.decode()
    item = FeedbackSubmission.objects.get()
    assert item.kind == "bug" and item.contact == "me@example.uz"
    assert item.page_url == "/uz/ayollar/" and item.user_agent.startswith("Mozilla")
    assert item.language == "uz"
    assert str(item).startswith(f"#{item.pk}")


def test_external_page_url_is_dropped_and_validation(page, client: Client) -> None:
    client.post(page.url, {**VALID, "page_url": "https://evil.example/"})
    assert FeedbackSubmission.objects.get().page_url == ""
    response = client.post(page.url, {**VALID, "text": "hi"}, HTTP_HX_REQUEST="true")
    assert response.status_code == 400


@freeze_time("2026-01-01 12:00:00")  # django-ratelimit windows are wall-clock based
def test_rate_limit(page, client: Client) -> None:
    for _ in range(5):
        client.post(page.url, VALID)
    assert client.post(page.url, VALID).status_code == 429


def test_purge_after_180_days() -> None:
    with freeze_time("2026-01-01"):
        FeedbackSubmission.objects.create(kind="feedback", text="old")
    with freeze_time("2026-06-01"):
        FeedbackSubmission.objects.create(kind="feedback", text="new")
        assert purge_old_submissions() == 0
    with freeze_time("2026-07-15"):
        assert purge_old_submissions() == 1
    assert FeedbackSubmission.objects.get().text == "new"
    from apps.feedback.tasks import purge_old_submissions as task

    assert task() == 0
