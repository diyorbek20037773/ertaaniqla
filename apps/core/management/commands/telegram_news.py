"""The news bot (D-109): `setup` checks the bot and the channel and points Telegram at
`<SITE_BASE_URL>/telegram/webhook/`; `status` shows what Telegram reports; `remove` stops it.

    python manage.py telegram_news setup
    python manage.py telegram_news status
    python manage.py telegram_news remove
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.urls import reverse


class Command(BaseCommand):
    help = "Connect the Telegram news bot to the site (setup / status / remove)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("action", choices=["setup", "status", "remove"])

    def handle(self, *args: Any, **options: Any) -> None:
        from apps.posts import telegram

        try:
            getattr(self, f"_{options['action']}")(telegram)
        except telegram.TelegramError as error:
            raise CommandError(str(error)) from None

    def _setup(self, telegram: Any) -> None:
        name = telegram.channel_name()
        if not name:
            raise CommandError("TELEGRAM_NEWS_CHANNEL is not set")
        bot = telegram.api("getMe")
        chat_id = name if name.lstrip("-").isdigit() else f"@{name}"
        chat = telegram.api("getChat", chat_id=chat_id)
        member = telegram.api("getChatMember", chat_id=chat["id"], user_id=bot["id"])
        if member.get("status") not in ("administrator", "creator"):
            raise CommandError(
                f"@{bot.get('username')} is not an admin of {chat.get('title')}: add it as an "
                "administrator of the channel first"
            )
        url = settings.SITE_BASE_URL.rstrip("/") + reverse("telegram_webhook")
        if not url.startswith("https://"):
            raise CommandError(f"Telegram needs an https address, SITE_BASE_URL gives {url}")
        telegram.api(
            "setWebhook",
            url=url,
            secret_token=telegram.webhook_secret(),
            allowed_updates=list(telegram.ALLOWED_UPDATES),
            max_connections=1,  # one update at a time: an album's photos never race
        )
        self.stdout.write(
            f"telegram_news: @{bot.get('username')} → {chat.get('title')} "
            f"(@{chat.get('username') or chat.get('id')}) → {url}"
        )

    def _status(self, telegram: Any) -> None:
        info = telegram.api("getWebhookInfo")
        for key in ("url", "pending_update_count", "last_error_date", "last_error_message"):
            if key in info:
                self.stdout.write(f"{key}: {info[key]}")

    def _remove(self, telegram: Any) -> None:
        telegram.api("deleteWebhook")
        self.stdout.write("telegram_news: webhook removed")
