"""The Russian home page keeps the brand slogan in Uzbek (client 2026-10-20, D-102)."""

from __future__ import annotations

import pytest
from django.core.management import call_command
from django.test import Client

from apps.home.models import HomePage

pytestmark = pytest.mark.django_db

NEW = "Эрта аниқла – ҳаётни сақла"


def test_russian_home_shows_the_uzbek_slogan(seeded, client: Client) -> None:
    html = client.get("/ru/").content.decode()
    assert f"<title>{NEW}</title>" in html
    assert "ҳаётни" in html and "сақла" in html
    assert "сохрани жизнь" not in html


def test_update_replaces_only_the_seeded_wording(seeded) -> None:
    home = HomePage.objects.get(locale__language_code="ru")
    home.hero_title = "Эрта аниқла – сохрани жизнь"  # what live sites were seeded with
    home.save_revision().publish()
    call_command("client_update_20261020b")
    home.refresh_from_db()
    assert home.hero_title == NEW

    home.hero_title = "Свой вариант редактора"
    home.save_revision().publish()
    call_command("client_update_20261020b")
    home.refresh_from_db()
    assert home.hero_title == "Свой вариант редактора"  # an editor's wording is kept
