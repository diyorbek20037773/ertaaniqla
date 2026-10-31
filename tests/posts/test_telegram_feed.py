"""The Telegram channel's own list «Yangiliklar» (D-109, 2026-10-31): `client_update_20261031`
creates it (uz + ru), moves the posts imported so far with redirects from their old addresses,
new posts go there, the header shows it after «Foydali maʼlumotlar»."""

from __future__ import annotations

import io
import json
from typing import Any

import pytest
from django.core.management import call_command
from django.test import Client
from wagtail.contrib.redirects.models import Redirect

from apps.posts import telegram
from apps.posts.models import PostIndexPage, TelegramPost

TOKEN = "123456789:AAH-test-token-abcdefghijklmnopqrstuvwxyz"
CHAT = {"id": -1001234567890, "type": "channel", "username": "erta_aniqla"}
TEXT = (
    "Bepul mammolog koʻrigi — oʻzingizni asrang!\n\nKoʻkrak bezi tekshiruvi bepul.\n\n➖➖➖\n\n"
    "Бесплатный осмотр у маммолога\n\nОсмотр молочной железы бесплатно."
)


def _send(client: Client, message_id: int, text: str = TEXT) -> None:
    message = {"message_id": message_id, "chat": CHAT, "date": 1766667357, "text": text}
    response = client.post(
        "/telegram/webhook/",
        data=json.dumps({"update_id": message_id, "channel_post": message}),
        content_type="application/json",
        headers={"X-Telegram-Bot-Api-Secret-Token": telegram.webhook_secret()},
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_channel_list_takes_the_posts_and_the_header_link(
    seeded: Any, client: Client, settings: Any
) -> None:
    settings.TELEGRAM_NEWS_BOT_TOKEN = TOKEN
    settings.TELEGRAM_NEWS_CHANNEL = "erta_aniqla"
    _send(client, 262)  # before the update: into «Foydali maʼlumotlar»
    record = TelegramPost.objects.get(message_id=262)
    assert record.page is not None and record.ru_page is not None
    old_uz, old_ru = record.page.url, record.ru_page.url
    assert old_uz.startswith("/uz/yangiliklar/") and old_ru.startswith("/ru/novosti/")

    out = io.StringIO()
    call_command("client_update_20261031", stdout=out)
    assert "lists created" in out.getvalue() and "moved 2" in out.getvalue()
    uz_list = PostIndexPage.objects.get(locale__language_code="uz", telegram_feed=True)
    ru_list = PostIndexPage.objects.get(locale__language_code="ru", telegram_feed=True)
    assert uz_list.url == "/uz/telegram-yangiliklar/" and uz_list.title == "Yangiliklar"
    assert ru_list.url == "/ru/telegram-novosti/" and ru_list.title == "Новости"
    assert ru_list.translation_key == uz_list.translation_key and ru_list.live

    record.refresh_from_db()
    assert record.page is not None and record.ru_page is not None
    assert record.page.url.startswith("/uz/telegram-yangiliklar/")
    assert record.ru_page.url.startswith("/ru/telegram-novosti/")
    assert Redirect.objects.filter(old_path=old_uz.rstrip("/"), redirect_page=record.page).exists()
    assert client.get(old_uz).status_code == 301

    # new posts go to the channel's list; «Foydali maʼlumotlar» keeps the site's articles
    _send(client, 263, "Yangi post sarlavhasi\n\nYangi post matni.")
    new = TelegramPost.objects.get(message_id=263).page
    assert new is not None and new.get_parent().pk == uz_list.pk
    useful = client.get("/uz/yangiliklar/").content.decode()
    assert "Yangi post sarlavhasi" not in useful
    assert "Yangi post sarlavhasi" in client.get(uz_list.url).content.decode()

    home = client.get("/uz/").content.decode()
    assert 'href="/uz/yangiliklar/">Foydali maʼlumotlar</a>' in home
    assert 'href="/uz/telegram-yangiliklar/">Yangiliklar</a>' in home
    assert 'href="/ru/telegram-novosti/">Новости</a>' in client.get("/ru/").content.decode()

    call_command("client_update_20261031", stdout=out)
    assert "lists kept" in out.getvalue() and out.getvalue().rstrip().endswith("moved 0")
