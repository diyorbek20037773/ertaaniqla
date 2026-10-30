"""Telegram webhook (D-109): the news bot's channel posts → «Yangiliklar» (apps.posts.telegram)."""

from __future__ import annotations

import json
import logging

from django.db import OperationalError
from django.http import HttpRequest, HttpResponse
from django.utils.crypto import constant_time_compare
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.posts import telegram

logger = logging.getLogger("ertaaniqla.telegram")

MAX_UPDATE_BYTES = 256 * 1024  # a post is ≤ 4096 characters; updates are a few KB


@csrf_exempt
@require_POST
def telegram_webhook(request: HttpRequest) -> HttpResponse:
    """200 once the update is handled or ignored. Only a database outage answers 500, so Telegram
    delivers the update again; a post the code cannot handle is logged and skipped, it must not
    hold up the posts after it."""
    # closed (403) until the bot is configured; a 404 would be redirected to /uz/… (i18n)
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not telegram.bot_token() or not constant_time_compare(secret, telegram.webhook_secret()):
        return HttpResponse(status=403)
    if len(request.body) > MAX_UPDATE_BYTES:
        return HttpResponse(status=413)
    try:
        update = json.loads(request.body)
    except ValueError:
        return HttpResponse(status=400)
    if not isinstance(update, dict):
        return HttpResponse(status=400)
    try:
        telegram.handle_update(update)
    except OperationalError:
        logger.exception("telegram: update %s failed, Telegram retries", update.get("update_id"))
        return HttpResponse(status=500)
    except Exception:  # a bug or a post we cannot read: logged with the traceback, skipped
        logger.exception("telegram: update %s skipped", update.get("update_id"))
    return HttpResponse(status=200)
