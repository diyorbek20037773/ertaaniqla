"""Earlier channel posts from the public t.me/s/ page (D-109): the page parser (text, formatting,
emoji, photos, album, video, service messages, chat id), paging back, the import publishing like
the webhook and skipping what is already on the site."""

from __future__ import annotations

import base64
import io
import json
from typing import Any

import pytest
from django.core.management import call_command
from PIL import Image

from apps.posts import telegram, telegram_import
from apps.posts.models import PostPage, TelegramPost

CDN = "https://cdn4.telesco.pe/file/"
VIEW = base64.urlsafe_b64encode(json.dumps({"c": -2580477116, "p": 1}).encode()).decode()


def _message(post_id: int, body: str, extra: str = "", css: str = "") -> str:
    return (
        f'<div class="tgme_widget_message_wrap"><div class="tgme_widget_message {css} '
        f'js-widget_message" data-post="erta_aniqla/{post_id}" data-view="{VIEW.rstrip("=")}">'
        '<div class="tgme_widget_message_bubble">'
        f"{extra}"
        f'<div class="tgme_widget_message_text js-message_text" dir="auto">{body}</div>'
        '<div class="tgme_widget_message_footer"><a class="tgme_widget_message_date" href="#">'
        f'<time datetime="2025-12-{post_id % 28 + 1:02d}T10:00:00+00:00" class="time">10:00</time>'
        "</a></div></div></div></div>"
    )


EMOJI = (
    '<tg-emoji emoji-id="1"><i class="emoji" style="background-image:url(\'//x\')"><b>💗</b>'
    "</i></tg-emoji>"
)
PHOTO = (
    f'<a class="tgme_widget_message_photo_wrap" href="https://t.me/erta_aniqla/{{id}}" '
    f"style=\"width:800px;background-image:url('{CDN}{{name}}.jpg')\"></a>"
)
ALBUM = (
    '<div class="tgme_widget_message_grouped_wrap">'
    + "".join(
        f'<a class="tgme_widget_message_photo_wrap grouped_media_wrap" '
        f"style=\"left:0;background-image:url('{CDN}album{n}.jpg')\" "
        f'href="https://t.me/erta_aniqla/{n}?single"></a>'
        for n in (20, 21, 22)
    )
    + "</div>"
)
VIDEO = (
    '<a class="tgme_widget_message_video_player" href="https://t.me/erta_aniqla/30">'
    f'<i class="tgme_widget_message_video_thumb" style="background-image:url(\'{CDN}thumb.jpg\')">'
    '</i><time class="message_video_duration">1:06</time></a>'
)
PAGE = "".join(
    [
        _message(
            10,
            f"{EMOJI} <b>Bepul koʻrik</b> — 1-noyabr<br/><br/>Roʻyxatdan "
            '<a href="https://example.uz/reg" target="_blank">bu yerda</a> oʻting, '
            "koʻkrak bezi tekshiruvi.<br/><br/>——<br/><br/>Бесплатный осмотр<br/><br/>"
            "Запишитесь заранее, осмотр молочной железы.",
            PHOTO.format(id=10, name="photo10"),
        ),
        _message(20, "Forum lavhalari<br/><br/>Bachadon boʻyni saratoni haqida suhbat.", ALBUM),
        _message(30, "OPV haqida video<br/><br/>Emlash nega muhim — mutaxassis fikri.", VIDEO),
        _message(31, "Erta aniqla pinned a video", css="service_message"),
        _message(32, ""),
    ]
)


@pytest.fixture
def pictures(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    fetched: list[str] = []

    def fake(url: str, data: Any, limit: int, what: str) -> bytes:
        fetched.append(url)
        buffer = io.BytesIO()
        Image.new("RGB", (80, 60), "pink").save(buffer, "JPEG")
        return buffer.getvalue()

    monkeypatch.setattr(telegram, "_open", fake)
    return fetched


def test_page_parser_reads_text_formatting_media_and_skips_service() -> None:
    posts = telegram_import.parse_page(PAGE)
    assert [p.message_id for p in posts] == [10, 20, 30, 32]
    first = posts[0]
    assert first.chat_id == -1002580477116 and first.date == 1765447200  # 2025-12-11 10:00 UTC
    assert first.text.startswith("💗 Bepul koʻrik — 1-noyabr\n\nRoʻyxatdan bu yerda")
    kinds = {
        (e["type"], first.text.encode("utf-16-le")[e["offset"] * 2 :].decode("utf-16-le")[:8])
        for e in first.entities
    }
    assert ("bold", "Bepul ko") in kinds and ("text_link", "bu yerda") in kinds
    assert not any(e["type"] == "italic" for e in first.entities)  # the emoji's <i> is no style
    assert first.photos == [(10, f"{CDN}photo10.jpg")]
    assert posts[1].photos == [(n, f"{CDN}album{n}.jpg") for n in (20, 21, 22)]
    assert posts[2].has_video and posts[2].video_thumb == f"{CDN}thumb.jpg"
    article = telegram.read_post(first.message("erta_aniqla")).articles["uz"]
    assert article.title == "Bepul koʻrik — 1-noyabr"
    assert '<a href="https://example.uz/reg">bu yerda</a>' in article.html


def test_recent_posts_pages_back_until_enough(monkeypatch: pytest.MonkeyPatch) -> None:
    asked: list[int | None] = []
    older = _message(5, "Eski post<br/><br/>Matn shu yerda davom etadi.")

    def fetch(channel: str, before: int | None) -> str:
        asked.append(before)
        return PAGE if before is None else (older if before == 10 else "")

    monkeypatch.setattr(telegram_import, "_fetch", fetch)
    posts = telegram_import.recent_posts("erta_aniqla", 4)
    assert asked == [None, 10]
    assert [p.message_id for p in posts] == [5, 10, 20, 30]
    assert [p.message_id for p in telegram_import.recent_posts("erta_aniqla", 2)] == [20, 30]


def test_fetch_tries_again_after_a_dropped_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    answers: list[Any] = [telegram.TelegramError("t.me: URLError"), b"<html></html>"]

    def flaky(url: str, data: Any, limit: int, what: str) -> bytes:
        answer = answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return bytes(answer)

    monkeypatch.setattr(telegram, "_open", flaky)
    monkeypatch.setattr(telegram_import, "_sleep", lambda seconds: None)
    assert telegram_import._fetch("erta_aniqla", 7) == "<html></html>"


def test_cdn_downloads_stay_on_telegram_hosts() -> None:
    for url in (
        "http://cdn4.telesco.pe/x.jpg",
        "https://evil.example/x.jpg",
        "https://cdn4.telesco.pe.evil.uz/x",
    ):
        with pytest.raises(telegram.TelegramError):
            telegram.fetch_public(url)


@pytest.mark.django_db
def test_import_publishes_like_the_webhook_and_runs_again_safely(
    seeded: Any, settings: Any, monkeypatch: pytest.MonkeyPatch, pictures: list[str]
) -> None:
    settings.TELEGRAM_NEWS_CHANNEL = "@erta_aniqla"
    monkeypatch.setattr(telegram_import, "_fetch", lambda c, b: PAGE if b is None else "")
    out = io.StringIO()
    call_command("telegram_news", "import", "--last", "20", stdout=out)
    assert "imported 3 post(s) [10, 20, 30]" in out.getvalue()

    first = TelegramPost.objects.get(message_id=10)
    assert first.page is not None and first.ru_page is not None
    assert first.page.title == "Bepul koʻrik — 1-noyabr" and first.page.live
    assert first.ru_page.title == "Бесплатный осмотр" and first.page.topic == "breast"
    assert first.page.date.isoformat() == "2025-12-11" and first.page.image_id is not None

    album = TelegramPost.objects.get(message_id=20).page
    assert album is not None and album.specific.topic == "cervical"
    gallery = [b for b in album.specific.body if b.block_type == "image_gallery"]
    assert len(gallery) == 1 and len(gallery[0].value["images"]) == 2
    assert TelegramPost.objects.filter(message_id__in=[21, 22], page=album).count() == 2

    video = TelegramPost.objects.get(message_id=30).page
    assert (
        video is not None and video.specific.body[0].value["url"] == "https://t.me/erta_aniqla/30"
    )
    assert f"{CDN}thumb.jpg" in pictures

    before = PostPage.objects.count()
    call_command("telegram_news", "import", "--last", "20", stdout=out)
    assert PostPage.objects.count() == before
    assert "imported 0 post(s)" in out.getvalue()
