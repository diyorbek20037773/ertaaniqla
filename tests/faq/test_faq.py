"""Ask-a-question flow (A3): form validation, anti-spam, rate limit, encryption, moderation,
publication with consent, purge job."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.core import mail
from django.db import connection
from django.test import Client, override_settings
from django.utils import timezone
from freezegun import freeze_time

from apps.faq.models import FAQPage, Question, QuestionStatus
from apps.faq.services import purge_contacts

pytestmark = pytest.mark.django_db

VALID = {
    "section": "women",
    "text": "Qachon mammografiya qilishim kerak?",
    "contact": "+998901234567",
    "consent_to_publish": "on",
    "consent_privacy": "on",
    "website": "",
}


@pytest.fixture
def page(seeded) -> FAQPage:
    return FAQPage.objects.get(locale__language_code="uz")


def test_pages_render_in_both_languages(seeded, client: Client) -> None:
    for url in ("/uz/savol-javob/", "/ru/voprosy-otvety/"):
        html = client.get(url).content.decode()
        assert 'name="text"' in html and "hp-field" in html


def test_submit_creates_encrypted_question_and_emails_moderators(
    page, client: Client, django_capture_on_commit_callbacks
) -> None:
    with django_capture_on_commit_callbacks(execute=True):
        response = client.post(page.url, VALID)
    assert response.status_code == 200
    assert "form-success" in response.content.decode()
    question = Question.objects.get()
    assert question.status == QuestionStatus.NEW
    assert question.contact == "+998901234567"
    assert question.language == "uz"
    with connection.cursor() as cur:
        cur.execute("SELECT contact FROM faq_question WHERE id = %s", [question.pk])
        assert cur.fetchone()[0].startswith("enc:v1:")
    assert len(mail.outbox) == 1
    assert "+998" not in mail.outbox[0].body
    assert f"#{question.pk}" in mail.outbox[0].subject


def test_htmx_submit_returns_partial(page, client: Client) -> None:
    response = client.post(page.url, VALID, HTTP_HX_REQUEST="true")
    assert response.status_code == 200
    assert "<html" not in response.content.decode()
    assert "form-success" in response.content.decode()


def test_validation_errors(page, client: Client) -> None:
    data = {**VALID, "text": "short", "consent_privacy": ""}
    response = client.post(page.url, data, HTTP_HX_REQUEST="true")
    assert response.status_code == 400
    html = response.content.decode()
    assert "form-errors" in html
    assert 'id="id_text_error"' in html
    assert Question.objects.count() == 0


def test_honeypot_blocks_bots(page, client: Client) -> None:
    response = client.post(page.url, {**VALID, "website": "http://spam.example"})
    assert Question.objects.count() == 0
    assert "form-errors" in response.content.decode()


@override_settings(TURNSTILE_SECRET_KEY="secret")
def test_turnstile_required_when_configured(page, client: Client, monkeypatch) -> None:
    from apps.core import antispam

    monkeypatch.setattr(antispam, "verify_turnstile", lambda token, ip="": token == "ok")
    from apps.core import forms as core_forms

    monkeypatch.setattr(core_forms, "verify_turnstile", lambda token, ip="": token == "ok")
    assert Question.objects.count() == 0
    client.post(page.url, VALID)
    assert Question.objects.count() == 0
    client.post(page.url, {**VALID, "cf-turnstile-response": "ok"})
    assert Question.objects.count() == 1


@freeze_time("2026-01-01 12:00:00")  # django-ratelimit windows are wall-clock based
def test_rate_limit_after_five_posts(page, client: Client) -> None:
    for _ in range(5):
        assert client.post(page.url, VALID).status_code == 200
    response = client.post(page.url, VALID)
    assert response.status_code == 429
    assert Question.objects.count() == 5


def test_publication_requires_consent_and_shows_on_page(page, user, client: Client) -> None:
    q = Question.objects.create(section="women", text="Savol matni", consent_to_publish=False)
    q.status = QuestionStatus.PUBLISHED
    q.answer = "<p>Javob</p>"
    q.answered_by = user
    q.save()
    q.refresh_from_db()
    assert q.status == QuestionStatus.ANSWERED  # downgraded, no consent
    assert q.answered_at is not None and q.published_at is None
    q.consent_to_publish = True
    q.status = QuestionStatus.PUBLISHED
    q.public_question = "Anonim savol"
    q.save()
    html = client.get(page.url).content.decode()
    assert "Anonim savol" in html and "Javob" in html and "Savol matni" not in html
    assert "Anonim savol" not in client.get(page.url + "?section=children").content.decode()
    assert str(q).startswith(f"#{q.pk}")


def test_purge_contacts_after_90_days() -> None:
    with freeze_time("2026-01-01"):
        answered = Question.objects.create(section="other", text="a", contact="+998900000001")
        answered.status = QuestionStatus.ANSWERED
        answered.save()
        rejected = Question.objects.create(
            section="other", text="r", contact="x@y.uz", status=QuestionStatus.REJECTED
        )
        fresh_new = Question.objects.create(section="other", text="n", contact="keep")
    with freeze_time("2026-03-01"):
        assert purge_contacts() == 0
    with freeze_time("2026-04-15"):
        assert purge_contacts() == 2
    for q in (answered, rejected):
        q.refresh_from_db()
        assert q.contact == "" and q.contact_purged_at is not None
    fresh_new.refresh_from_db()
    assert fresh_new.contact == "keep"
    assert purge_contacts(timezone.now() + timedelta(days=400)) == 0  # never twice


def test_purge_task_wrapper() -> None:
    from apps.faq.tasks import purge_contacts as task

    assert task() == 0
