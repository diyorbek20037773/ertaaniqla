"""`purge_pii`, `rotate_pii_keys`, `check_links` management commands (spec §6, §8)."""

from __future__ import annotations

from io import StringIO

import pytest
from cryptography.fernet import Fernet
from django.core.management import call_command
from django.test import override_settings
from freezegun import freeze_time

from apps.core import fields
from apps.faq.models import Question
from apps.feedback.models import FeedbackSubmission

pytestmark = pytest.mark.django_db


def _raw(model, pk: int, column: str) -> str:
    from django.db import connection

    table = model._meta.db_table
    with connection.cursor() as cursor:
        cursor.execute(f'SELECT "{column}" FROM "{table}" WHERE id = %s', [pk])
        return str(cursor.fetchone()[0])


def test_purge_pii_dry_run_then_real() -> None:
    with freeze_time("2026-01-01"):
        FeedbackSubmission.objects.create(kind="feedback", text="old", contact="a@b.uz")
    with freeze_time("2026-08-01"):
        out = StringIO()
        call_command("purge_pii", "--dry-run", stdout=out)
        assert "dry-run: 0 question contact(s), 1 feedback row(s)" in out.getvalue()
        assert FeedbackSubmission.objects.count() == 1  # rolled back
        out = StringIO()
        call_command("purge_pii", stdout=out)
        assert "purged 0 question contact(s), 1 feedback row(s)" in out.getvalue()
        assert FeedbackSubmission.objects.count() == 0


def test_rotate_pii_keys_re_encrypts_with_newest_key(settings) -> None:
    old_key = Fernet.generate_key().decode()
    new_key = Fernet.generate_key().decode()
    with override_settings(PII_ENCRYPTION_KEYS=[old_key]):
        fields.reset_key_cache()
        question = Question.objects.create(section="women", text="Savol?", contact="+998901234567")
        empty = Question.objects.create(section="women", text="Kontakt yo'q", contact="")
    cipher_old = _raw(Question, question.pk, "contact")
    assert cipher_old.startswith("enc:v1:")
    # both keys configured, newest first → rows still readable, rotation rewrites them
    with override_settings(PII_ENCRYPTION_KEYS=[new_key, old_key]):
        fields.reset_key_cache()
        out = StringIO()
        call_command("rotate_pii_keys", stdout=out)
        assert "faq.Question: 1 row(s)" in out.getvalue()
    cipher_new = _raw(Question, question.pk, "contact")
    assert cipher_new != cipher_old
    assert _raw(Question, empty.pk, "contact") == ""
    # old key dropped: value must decrypt with the new key alone
    with override_settings(PII_ENCRYPTION_KEYS=[new_key]):
        fields.reset_key_cache()
        assert Question.objects.get(pk=question.pk).contact == "+998901234567"
    fields.reset_key_cache()


def test_rotate_pii_keys_requires_keys() -> None:
    from django.core.management.base import CommandError

    with override_settings(PII_ENCRYPTION_KEYS=[]), pytest.raises(CommandError):
        call_command("rotate_pii_keys")


def test_check_links_on_seeded_tree(seeded) -> None:
    out = StringIO()
    call_command("check_links", "--limit", "12", stdout=out)
    text = out.getvalue()
    assert "pages: 12" in text and "no broken links" in text


def test_check_links_reports_broken_internal_link(seeded, monkeypatch) -> None:
    from apps.articles.models import ArticlePage

    article = ArticlePage.objects.filter(locale__language_code="uz").first()
    article.body = [
        {"type": "rich_text", "value": '<p><a href="/uz/bu-sahifa-yoq/">broken</a></p>'}
    ]
    article.save_revision().publish()
    out = StringIO()
    with pytest.raises(SystemExit):
        call_command("check_links", stdout=out)
    assert "BROKEN /uz/bu-sahifa-yoq/ → HTTP 404" in out.getvalue()


def test_find_placeholders_lists_seeded_pages_and_fails(seeded) -> None:
    from io import StringIO

    from django.core.management import CommandError, call_command

    out = StringIO()
    call_command("find_placeholders", stdout=out)
    text = out.getvalue()
    assert "/ru/zhenskiy/osvedomlennost/rak-molochnoy-zhelezy/" in text
    assert "VERIFY=" in text
    with pytest.raises(CommandError, match="still contain placeholders"):
        call_command("find_placeholders", "--fail", stdout=StringIO())


def test_find_placeholders_clean_content(seeded) -> None:
    from io import StringIO

    from django.core.management import call_command
    from wagtail.models import Page

    from apps.core.management.commands.find_placeholders import count_placeholders
    from apps.core.models import SiteSettings

    assert count_placeholders({"a": ["[[TODO: x]]", "[[VERIFY: y]] [[VERIFY: z]]"]}) == {
        "TODO": 1,
        "VERIFY": 2,
    }
    Page.objects.update(live=False)  # rolled back with the test transaction
    SiteSettings.objects.all().delete()
    out = StringIO()
    call_command("find_placeholders", "--fail", stdout=out)
    assert "no placeholders on live content" in out.getvalue()
