"""The Telegram channel's own list «Yangiliklar» (D-109): new posts go there, the header shows it
after «Foydali maʼlumotlar», and `client_update_20261101` gives it the plain address
/uz/yangiliklar/ (2026-11-01) — «Foydali maʼlumotlar» moving to /uz/foydali-malumotlar/, old
addresses redirecting. `client_update_20261031` (which made the list) changes nothing on a tree
that has it."""

from __future__ import annotations

import io
import json
from typing import Any

import pytest
from django.core.management import call_command
from django.test import Client

from apps.posts import telegram
from apps.posts.models import PostIndexPage, PostKind, TelegramPost

TOKEN = "123456789:AAH-test-token-abcdefghijklmnopqrstuvwxyz"
CHAT = {"id": -1001234567890, "type": "channel", "username": "erta_aniqla"}
TEXT = (
    "Bepul mammolog koʻrigi — oʻzingizni asrang!\n\nKoʻkrak bezi tekshiruvi bepul.\n\n➖➖➖\n\n"
    "Бесплатный осмотр у маммолога\n\nОсмотр молочной железы бесплатно."
)


@pytest.fixture
def bot(settings: Any) -> Any:
    settings.TELEGRAM_NEWS_BOT_TOKEN = TOKEN
    settings.TELEGRAM_NEWS_CHANNEL = "erta_aniqla"
    return settings


def _send(client: Client, message_id: int, text: str = TEXT) -> None:
    message = {"message_id": message_id, "chat": CHAT, "date": 1766667357, "text": text}
    response = client.post(
        "/telegram/webhook/",
        data=json.dumps({"update_id": message_id, "channel_post": message}),
        content_type="application/json",
        headers={"X-Telegram-Bot-Api-Secret-Token": telegram.webhook_secret()},
    )
    assert response.status_code == 200


def _list(language: str, channel: bool) -> PostIndexPage:
    return PostIndexPage.objects.get(
        locale__language_code=language, kind=PostKind.NEWS, telegram_feed=channel
    )


def _set_slug(page: PostIndexPage, slug: str) -> None:
    page.slug = slug
    page.save_revision().publish()


@pytest.mark.django_db
def test_new_posts_go_to_the_channel_list_shown_in_the_header(
    seeded: Any, client: Client, bot: Any
) -> None:
    _send(client, 262)
    record = TelegramPost.objects.get(message_id=262)
    assert record.page is not None and record.ru_page is not None
    assert record.page.url.startswith("/uz/yangiliklar/")
    assert record.ru_page.url.startswith("/ru/novosti/")
    assert "Bepul mammolog" in client.get("/uz/yangiliklar/").content.decode()
    assert "Bepul mammolog" not in client.get("/uz/foydali-malumotlar/").content.decode()

    home = client.get("/uz/").content.decode()
    assert 'href="/uz/foydali-malumotlar/">Foydali maʼlumotlar</a>' in home
    assert 'href="/uz/yangiliklar/">Yangiliklar</a>' in home
    assert 'href="/ru/novosti/">Новости</a>' in client.get("/ru/").content.decode()

    out = io.StringIO()
    call_command("client_update_20261031", stdout=out)  # the list is there already
    assert "lists kept" in out.getvalue() and out.getvalue().rstrip().endswith("moved 0")


@pytest.mark.django_db
def test_update_gives_the_channel_list_the_plain_address(
    seeded: Any, client: Client, bot: Any, django_capture_on_commit_callbacks: Any
) -> None:
    # production before 2026-11-01: «Foydali maʼlumotlar» at /yangiliklar/, the channel's list
    # at /telegram-yangiliklar/, one post imported into it
    useful_uz, useful_ru = _list("uz", False), _list("ru", False)
    channel_uz, channel_ru = _list("uz", True), _list("ru", True)
    channel_uz.lead = "«Erta aniqla» Telegram kanalidagi xabarlar."
    _set_slug(channel_uz, "telegram-yangiliklar")
    _set_slug(channel_ru, "telegram-novosti")
    _set_slug(useful_uz, "yangiliklar")
    _set_slug(useful_ru, "novosti")
    _send(client, 262)
    post = TelegramPost.objects.get(message_id=262).page
    assert post is not None and post.url.startswith("/uz/telegram-yangiliklar/")
    old_post_url = post.url

    out = io.StringIO()
    # Wagtail makes the redirects once the slug change is committed
    with django_capture_on_commit_callbacks(execute=True):
        call_command("client_update_20261101", stdout=out)
    assert "renamed 4" in out.getvalue()
    for page in (useful_uz, useful_ru, channel_uz, channel_ru, post):
        page.refresh_from_db()
    assert useful_uz.url == "/uz/foydali-malumotlar/"
    assert useful_ru.url == "/ru/poleznaya-informatsiya/"
    assert channel_uz.url == "/uz/yangiliklar/" and channel_ru.url == "/ru/novosti/"
    assert channel_uz.lead == "«Erta aniqla» loyihasining soʻnggi yangiliklari."
    assert "Telegram" not in client.get("/uz/yangiliklar/").content.decode().split("<main", 1)[1]
    assert post.url == old_post_url.replace("/telegram-yangiliklar/", "/yangiliklar/")

    response = client.get(old_post_url)
    assert response.status_code == 301 and response["Location"].endswith(post.url)
    assert client.get("/uz/telegram-yangiliklar/").status_code == 301
    assert "Bepul mammolog" in client.get("/uz/yangiliklar/").content.decode()
    assert client.get("/uz/foydali-malumotlar/").status_code == 200

    call_command("client_update_20261101", stdout=out)
    assert out.getvalue().rstrip().endswith("renamed 0")


@pytest.mark.django_db
def test_update_leaves_a_list_with_an_editors_draft(seeded: Any, admin_user: Any) -> None:
    channel_uz = _list("uz", True)
    _set_slug(channel_uz, "telegram-yangiliklar")
    useful_uz = _list("uz", False)
    _set_slug(useful_uz, "yangiliklar")
    useful_uz.title = "Muharrir qoralamasi"
    useful_uz.save_revision(user=admin_user)  # not published
    out = io.StringIO()
    call_command("client_update_20261101", stdout=out)
    assert "skipped" in out.getvalue()
    useful_uz.refresh_from_db()
    assert useful_uz.slug == "yangiliklar"
