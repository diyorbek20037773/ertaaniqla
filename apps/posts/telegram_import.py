"""Earlier posts of the Telegram channel → «Yangiliklar» (D-109). A bot never sees posts from before
it joined, so `manage.py telegram_news import --last N` reads the channel's public page
(https://t.me/s/<channel>, newest first, `?before=<id>` for older ones) and publishes its last N
posts exactly as the webhook would: same title, languages, topic, picture, video embed, album
gallery and date. Posts already on the site are skipped, so it can run again.
"""

from __future__ import annotations

import base64
import datetime as dt
import json
import logging
import time
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any

from django.db import transaction

from apps.posts import telegram

logger = logging.getLogger("ertaaniqla.telegram")
_sleep = time.sleep  # tests replace it

PAGE_URL = "https://t.me/s/{channel}"
MAX_PAGE_BYTES = 2 * 1024 * 1024
MAX_PAGES = 30  # ≈ 20 posts a page
RETRY_PAUSES = (2.0, 5.0)
FORMAT_TAGS = {"b": "bold", "strong": "bold", "i": "italic", "em": "italic"}


@dataclass
class PublicPost:
    """One message as the public page shows it."""

    message_id: int
    chat_id: int = 0
    date: int = 0
    text: str = ""
    entities: list[dict[str, Any]] = field(default_factory=list)
    photos: list[tuple[int, str]] = field(default_factory=list)  # (message id, CDN address)
    video_thumb: str = ""
    has_video: bool = False
    service: bool = False

    def message(self, channel: str) -> dict[str, Any]:
        """The Bot API shape `telegram.read_post` expects."""
        message: dict[str, Any] = {
            "message_id": self.message_id,
            "chat": {"id": self.chat_id, "type": "channel", "username": channel},
            "date": self.date,
            "text": self.text,
            "entities": self.entities,
        }
        if self.has_video:
            message["video"] = {}  # → the post is embedded on the page
        return message


def _classes(attrs: dict[str, str | None]) -> set[str]:
    return set((attrs.get("class") or "").split())


def _background(style: str | None) -> str:
    start = (style or "").find("background-image:url('")
    if start < 0:
        return ""
    start += len("background-image:url('")
    end = (style or "").find("')", start)
    return (style or "")[start:end] if end > start else ""


def _utf16(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


class ChannelPage(HTMLParser):
    """The messages of one t.me/s/ page: text with bold / italic / links (as Bot API entities,
    UTF-16 offsets), photos, video, date and the chat id (from `data-view`)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.posts: list[PublicPost] = []
        self._post: PublicPost | None = None
        self._depth = 0  # open <div>s
        self._text_depth = 0  # the depth of the open message-text <div>, 0 = outside
        self._stack: list[tuple[str, str, int, str]] = []  # tag, entity kind, offset, url
        self._emoji = 0  # inside <tg-emoji> / <i class="emoji">: no formatting

    def handle_starttag(self, tag: str, attr_list: list[tuple[str, str | None]]) -> None:
        attrs = dict(attr_list)
        classes = _classes(attrs)
        if tag == "div":
            self._depth += 1
            if "tgme_widget_message" in classes and attrs.get("data-post"):
                self._start_post(attrs)
                if self._post is not None and "service_message" in classes:
                    self._post.service = True  # «pinned a video», «live stream finished»
            elif self._post is not None:
                # the post's own text, once (not a reply's quote)
                if "tgme_widget_message_text" in classes and not (
                    self._text_depth or self._post.text
                ):
                    self._text_depth = self._depth
                if "service_message" in classes:
                    self._post.service = True
        if self._post is None:
            return
        if self._text_depth:
            self._text_tag(tag, attrs, classes)
            return
        if tag == "a" and "tgme_widget_message_photo_wrap" in classes:
            url = _background(attrs.get("style"))
            href = attrs.get("href") or ""
            tail = href.split("?", 1)[0].rstrip("/").rsplit("/", 1)[-1]
            if url:
                message_id = int(tail) if tail.isdigit() else self._post.message_id
                self._post.photos.append((message_id, url))
        elif tag == "a" and classes & {
            "tgme_widget_message_video_player",
            "tgme_widget_message_roundvideo_player",
            "tgme_widget_message_document_wrap",
        }:
            self._post.has_video = True
        elif tag == "i" and "tgme_widget_message_video_thumb" in classes:
            self._post.video_thumb = self._post.video_thumb or _background(attrs.get("style"))
        elif tag == "time" and "time" in classes and not self._post.date:
            try:
                stamp = dt.datetime.fromisoformat(attrs.get("datetime") or "")
                self._post.date = int(stamp.timestamp())
            except ValueError:
                pass

    def _start_post(self, attrs: dict[str, str | None]) -> None:
        tail = str(attrs.get("data-post")).rsplit("/", 1)[-1]
        if not tail.isdigit():
            self._post = None
            return
        self._post = PublicPost(message_id=int(tail))
        self.posts.append(self._post)
        try:  # {"c": -2580477116, "p": 262, …}: the channel's id without its -100 prefix
            view = attrs.get("data-view") or ""
            data = json.loads(base64.urlsafe_b64decode(view + "=" * (-len(view) % 4)))
            self._post.chat_id = int(f"-100{abs(int(data['c']))}")
        except (ValueError, KeyError, TypeError):
            pass

    def _text_tag(self, tag: str, attrs: dict[str, str | None], classes: set[str]) -> None:
        assert self._post is not None
        if tag == "br":
            self._post.text += "\n"
            return
        if tag in ("img", "hr"):  # void elements never close
            return
        if tag == "tg-emoji" or "emoji" in classes or self._emoji:
            self._emoji += 1
            self._stack.append((tag, "", 0, ""))
            return
        offset = _utf16(self._post.text)
        if tag == "a" and (attrs.get("href") or "").startswith(("http://", "https://")):
            self._stack.append((tag, "text_link", offset, str(attrs["href"])))
        else:
            self._stack.append((tag, FORMAT_TAGS.get(tag, ""), offset, ""))

    def handle_endtag(self, tag: str) -> None:
        open_tag = self._stack[-1][0] if self._stack else ""
        if self._post is not None and self._text_depth and tag != "div" and open_tag == tag:
            _, kind, offset, url = self._stack.pop()
            length = _utf16(self._post.text) - offset
            if self._emoji:
                self._emoji -= 1
            elif kind and length > 0:
                entity: dict[str, Any] = {"type": kind, "offset": offset, "length": length}
                if url:
                    entity["url"] = url
                self._post.entities.append(entity)
        if tag == "div":
            if self._text_depth and self._depth == self._text_depth:
                self._text_depth = 0
                self._stack.clear()
                self._emoji = 0
            self._depth -= 1

    def handle_data(self, data: str) -> None:
        if self._post is not None and self._text_depth:
            self._post.text += data


def parse_page(html: str) -> list[PublicPost]:
    page = ChannelPage()
    page.feed(html)
    page.close()
    return [post for post in page.posts if not post.service]


def _fetch(channel: str, before: int | None) -> str:
    """One page, tried again after a dropped connection (seen now and then on 2026-10-30)."""
    url = PAGE_URL.format(channel=channel) + (f"?before={before}" if before else "")
    for pause in (*RETRY_PAUSES, None):
        try:
            return telegram._open(url, None, MAX_PAGE_BYTES, "t.me").decode("utf-8", "replace")
        except telegram.TelegramError:
            if pause is None:
                raise
            _sleep(pause)
    raise AssertionError("unreachable")


def recent_posts(channel: str, limit: int) -> list[PublicPost]:
    """The channel's last `limit` posts that have words (oldest first)."""
    found: dict[int, PublicPost] = {}
    before: int | None = None
    for _ in range(MAX_PAGES):
        posts = parse_page(_fetch(channel, before))
        if not posts:
            break
        for post in posts:
            if post.text.strip():
                found.setdefault(post.message_id, post)
        oldest = min(post.message_id for post in posts)
        if len(found) >= limit or oldest <= 1 or oldest == before:
            break
        before = oldest
    return sorted(found.values(), key=lambda p: p.message_id)[-limit:]


def import_post(item: PublicPost, channel: str) -> bool:
    """Publish one earlier post unless it is on the site already; True when published."""
    from apps.posts.models import TelegramPost

    if TelegramPost.objects.filter(chat_id=item.chat_id, message_id=item.message_id).exists():
        return False
    message = item.message(channel)
    post = telegram.read_post(message)
    if not post.articles:
        return False
    pictures = item.photos or ([(item.message_id, item.video_thumb)] if item.video_thumb else [])
    title = next(iter(post.articles.values())).title
    name = f"telegram-{abs(item.chat_id)}-{item.message_id}"
    image = telegram._image(pictures[0][1], title, name) if pictures else None
    uz_page, ru_page = telegram._create(post, message, image)
    record = TelegramPost.objects.create(
        chat_id=item.chat_id, message_id=item.message_id, page=uz_page, ru_page=ru_page
    )
    for message_id, url in pictures[1:]:  # the album's other photos → the gallery
        if message_id != item.message_id:
            TelegramPost.objects.get_or_create(
                chat_id=item.chat_id,
                message_id=message_id,
                defaults={"page": uz_page, "ru_page": ru_page},
            )
        telegram._add_photo(record, url, f"telegram-{abs(item.chat_id)}-{message_id}")
    return True


def import_recent(limit: int) -> list[int]:
    """`manage.py telegram_news import --last N`: ids of the posts published now."""
    channel = telegram.channel_name()
    if not channel or channel.lstrip("-").isdigit():
        raise telegram.TelegramError("TELEGRAM_NEWS_CHANNEL must be the public @name")
    published = []
    for item in recent_posts(channel, limit):
        if not item.chat_id:
            continue
        with transaction.atomic():
            if import_post(item, channel):
                published.append(item.message_id)
    logger.info("telegram: imported %d earlier post(s): %s", len(published), published)
    return published
