"""Telegram channel → «Yangiliklar» (D-109): post parsing (title, summary, formatting, languages),
the webhook's secret, published uz + ru items, photos, videos, albums, edits, repeated deliveries,
the Bot API client keeping the token out of errors, and the setup command."""

from __future__ import annotations

import io
import json
import urllib.error
from typing import Any

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client
from PIL import Image
from wagtail.contrib.redirects.models import Redirect

from apps.core.sentry import scrub_sentry_event
from apps.media_library.models import PortalImage
from apps.posts import telegram
from apps.posts.models import PostPage, TelegramPost

TOKEN = "123456789:AAH-test-token-abcdefghijklmnopqrstuvwxyz"
CHAT = {"id": -1001234567890, "type": "channel", "username": "erta_aniqla", "title": "Erta aniqla"}
UZ_RU = (
    "🙏Bemor yaqiningizga qanday suyanch boʻlishni bilmayapsizmi?\n\n"
    "Yaqin insoningizni kasallik davrida qo‘llab-quvvatlash har doim oson boʻlavermaydi. "
    "Ushbu videoda psixologning tavsiyalarini tinglashingiz mumkin.\n\n"
    "➖➖➖\n\n"
    "🙏Как быть опорой для тех, кто проходит лечение\n\n"
    "Поддержка близкого человека во время болезни не всегда даётся легко.\n\n"
    "#ertaaniqla @erta_aniqla"
)


@pytest.fixture
def bot(settings: Any) -> Any:
    settings.TELEGRAM_NEWS_BOT_TOKEN = TOKEN
    settings.TELEGRAM_NEWS_CHANNEL = "https://t.me/erta_aniqla"
    return settings


@pytest.fixture
def photos(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """`download` answers a small PNG and records which file ids were fetched."""
    fetched: list[str] = []

    def fake_download(file_id: str) -> bytes:
        fetched.append(file_id)
        buffer = io.BytesIO()
        Image.new("RGB", (64, 48), "pink").save(buffer, "PNG")
        return buffer.getvalue()

    monkeypatch.setattr(telegram, "download", fake_download)
    return fetched


def _post(message_id: int, text: str = "", **extra: Any) -> dict[str, Any]:
    message: dict[str, Any] = {"message_id": message_id, "chat": CHAT, "date": 1793260800}
    if text and not any(k in extra for k in ("photo", "video")):
        message["text"] = text
    elif text:
        message["caption"] = text
    message.update(extra)
    return message


def _send(client: Client, update: dict[str, Any], secret: str | None = None) -> Any:
    return client.post(
        "/telegram/webhook/",
        data=json.dumps(update),
        content_type="application/json",
        headers={"X-Telegram-Bot-Api-Secret-Token": secret or telegram.webhook_secret()},
    )


def _page(message_id: int) -> PostPage:
    page = TelegramPost.objects.get(message_id=message_id).page
    assert page is not None
    return page.specific


# --- parsing -----------------------------------------------------------------------------------
def test_title_summary_and_body_from_the_post() -> None:
    post = telegram.read_post(_post(1, UZ_RU))
    uz, ru = post.articles["uz"], post.articles["ru"]
    assert uz.title == "Bemor yaqiningizga qanday suyanch boʻlishni bilmayapsizmi?"
    assert uz.summary.startswith("Yaqin insoningizni kasallik davrida qoʻllab-quvvatlash")
    assert "qoʻllab" in uz.html and "‘" not in uz.html  # the site's Uzbek apostrophes
    assert ru.title == "Как быть опорой для тех, кто проходит лечение"
    assert ru.html == "<p>Поддержка близкого человека во время болезни не всегда даётся легко.</p>"
    assert "#ertaaniqla" not in uz.html + ru.html  # hashtag / mention lines dropped
    assert post.date.isoformat() == "2026-10-29"
    assert post.topic == ""  # no disease named: «Barchasi» only


def test_formatting_survives_with_emoji_before_it() -> None:
    text = "💗 Sarlavha\n\n👉 Ro'yxatdan o'tish: bu yerda va qalin matn\n2-qator"
    # UTF-16 offsets: 💗 and 👉 count twice
    entities = [
        {"type": "text_link", "offset": 35, "length": 8, "url": "https://example.uz/reg"},
        {"type": "bold", "offset": 47, "length": 5},
        {"type": "text_link", "offset": 0, "length": 2, "url": "javascript:alert(1)"},
    ]
    article = telegram.read_post(_post(1, text, entities=entities)).articles["uz"]
    assert article.title == "Sarlavha"
    assert article.html == (
        '<p>👉 Roʻyxatdan oʻtish: <a href="https://example.uz/reg">bu yerda</a> va '
        "<b>qalin</b> matn<br/>2-qator</p>"
    )
    assert "javascript" not in article.html


def test_summary_is_not_repeated_in_the_body() -> None:
    text = "Sarlavha\n\nQisqa mazmun shu yerda.\n\nAsosiy matn birinchi xatboshi."
    article = telegram.read_post(_post(1, text)).articles["uz"]
    assert article.summary == "Qisqa mazmun shu yerda."
    assert article.html == "<p>Asosiy matn birinchi xatboshi.</p>"
    long_lead = "Uzun " + "soʻz " * 80
    article = telegram.read_post(_post(2, f"Sarlavha\n\n{long_lead}\n\nOxiri.")).articles["uz"]
    assert article.summary.endswith("…") and article.html.startswith("<p>Uzun")  # cut: kept


def test_long_first_line_is_cut_at_a_sentence() -> None:
    sentence = "Koʻkrak bezi saratoni haqida bilishingiz kerak boʻlgan eng muhim gaplar."
    rest = " Bu ikkinchi gap. " * 12
    article = telegram.read_post(_post(1, sentence + rest)).articles["uz"]
    assert article.title == sentence.rstrip(".")
    assert article.html.startswith("<p>Bu ikkinchi gap.")
    one_line = "soʻz " * 60
    article = telegram.read_post(_post(2, one_line)).articles["uz"]
    assert article.title.endswith("…") and len(article.title) <= telegram.TITLE_MAX


def test_languages_of_unsplit_posts() -> None:
    ru_only = "А когда вы в последний раз делали УЗИ молочных желез?\n\nВрач делится мнением."
    assert set(telegram.read_post(_post(1, ru_only)).articles) == {"ru"}
    uz_cyrillic = "Кўкрак бези саратони ҳақида\n\nМуҳим маълумотлар ва тавсиялар"
    assert set(telegram.read_post(_post(2, uz_cyrillic)).articles) == {"uz"}
    signature = "OPV vaksinasi haqida muhim maʼlumot\n\nMatn shu yerda davom etadi.\n____\n💗"
    assert set(telegram.read_post(_post(3, signature)).articles) == {"uz"}
    assert telegram.read_post(_post(4, "#ertaaniqla")).articles == {}


def test_bilingual_posts_with_a_short_separator_or_none() -> None:
    uz = (
        "Bepul mammolog koʻrigi — oʻzingizni asrang!\n\n"
        "Har bir ayol oʻz sogʻligʻiga eʼtibor berishi kerak, koʻrik bepul."
    )
    ru = (
        "Бесплатный осмотр у маммолога — позаботьтесь о себе!\n\n"
        "Каждая женщина заслуживает внимания и заботы."
    )
    for text in (f"{uz}\n\n——\n\n{ru}", f"{uz}\n\n{ru}"):
        articles = telegram.read_post(_post(1, text)).articles
        assert articles["uz"].title == "Bepul mammolog koʻrigi — oʻzingizni asrang!"
        assert articles["ru"].title == "Бесплатный осмотр у маммолога — позаботьтесь о себе!"
    # an Uzbek post quoting one short Russian line stays one Uzbek item
    quote = f"{uz}\n\nВрач сказал: важно."
    assert set(telegram.read_post(_post(2, quote)).articles) == {"uz"}


def test_slug_spells_russian_in_latin_letters(seeded: Any) -> None:
    index = telegram._news_index("ru")
    assert index is not None
    assert telegram._slug(index, "Как быть опорой", 7) == "kak-byt-oporoy"


# --- webhook -----------------------------------------------------------------------------------
@pytest.mark.django_db
def test_webhook_is_closed_without_token_or_secret(client: Client, settings: Any) -> None:
    settings.TELEGRAM_NEWS_BOT_TOKEN = ""
    assert (
        client.post("/telegram/webhook/", data="{}", content_type="application/json").status_code
        == 403
    )
    settings.TELEGRAM_NEWS_BOT_TOKEN = TOKEN
    assert _send(client, {}, secret="wrong").status_code == 403
    assert client.get("/telegram/webhook/").status_code == 405
    assert _send(client, {"update_id": 1}).status_code == 200


@pytest.mark.django_db
def test_bilingual_post_publishes_uz_item_and_its_russian_version(
    seeded: Any, client: Client, bot: Any, photos: list[str]
) -> None:
    photo = [
        {"file_id": "small", "width": 90, "height": 60, "file_size": 1000},
        {"file_id": "big", "width": 1280, "height": 853, "file_size": 90000},
    ]
    response = _send(client, {"update_id": 10, "channel_post": _post(41, UZ_RU, photo=photo)})
    assert response.status_code == 200
    record = TelegramPost.objects.get(message_id=41)
    uz, ru = record.page, record.ru_page
    assert uz is not None and ru is not None
    assert uz.live and ru.live and uz.locale.language_code == "uz"
    assert ru.translation_key == uz.translation_key and ru.locale.language_code == "ru"
    assert uz.slug == "bemor-yaqiningizga-qanday-suyanch-bolishni-bilmayapsizmi"
    assert ru.title.startswith("Как быть опорой") and ru.slug.startswith("kak-byt-oporoy")
    assert not Redirect.objects.filter(redirect_page=ru).exists()  # its uz slug was never public
    assert photos == ["big"] and uz.image_id is not None and ru.image_id == uz.image_id
    assert PortalImage.objects.get(pk=uz.image_id).credit == "Telegram"
    html = client.get(uz.url).content.decode()
    assert "Bemor yaqiningizga qanday suyanch" in html
    assert "Bemor yaqiningizga" in client.get("/uz/yangiliklar/").content.decode()
    assert "Как быть опорой" in client.get(ru.url).content.decode()
    # Telegram delivers the same post again: nothing new
    assert _send(client, {"update_id": 10, "channel_post": _post(41, UZ_RU)}).status_code == 200
    assert TelegramPost.objects.count() == 1
    assert PostPage.objects.filter(title__startswith="Bemor yaqiningizga").count() == 1


@pytest.mark.django_db
def test_video_post_embeds_the_telegram_post_and_guesses_the_topic(
    seeded: Any, client: Client, bot: Any, photos: list[str]
) -> None:
    video = {"file_id": "v1", "duration": 60, "thumbnail": {"file_id": "thumb", "width": 320}}
    text = "OPVga qarshi vaksina haqida\n\nBachadon boʻyni saratonining oldini olish."
    _send(client, {"update_id": 11, "channel_post": _post(42, text, video=video)})
    page = _page(42)
    assert page.topic == "cervical"
    assert photos == ["thumb"]
    assert [block.block_type for block in page.body] == ["embed", "rich_text"]
    assert page.body[0].value["url"] == "https://t.me/erta_aniqla/42"
    assert 'src="https://t.me/erta_aniqla/42?embed=1"' in client.get(page.url).content.decode()


@pytest.mark.django_db
def test_russian_only_post_is_published_in_russian(seeded: Any, client: Client, bot: Any) -> None:
    text = "Кольпоскопия — важный этап заботы о женском здоровье\n\nЭксперт делится мнением."
    _send(client, {"update_id": 12, "channel_post": _post(43, text)})
    record = TelegramPost.objects.get(message_id=43)
    assert record.page is None and record.ru_page is not None
    assert record.ru_page.live and record.ru_page.get_parent().url_path.endswith("/novosti/")
    assert record.ru_page.topic == "cervical"


@pytest.mark.django_db
def test_album_photos_join_the_captioned_item(
    seeded: Any, client: Client, bot: Any, photos: list[str]
) -> None:
    def photo(file_id: str) -> list[dict[str, Any]]:
        return [{"file_id": file_id, "width": 800, "height": 600, "file_size": 5000}]

    text = "Mammolog koʻrigi — 1-noyabr\n\nKoʻkrak bezi tekshiruvi bepul."
    # caption first, then two more photos
    _send(
        client,
        {"update_id": 1, "channel_post": _post(50, text, photo=photo("a"), media_group_id="g1")},
    )
    _send(
        client, {"update_id": 2, "channel_post": _post(51, photo=photo("b"), media_group_id="g1")}
    )
    _send(
        client, {"update_id": 3, "channel_post": _post(52, photo=photo("c"), media_group_id="g1")}
    )
    page = _page(50)
    assert page.topic == "breast" and page.image_id is not None
    gallery = [b for b in page.body if b.block_type == "image_gallery"]
    assert len(gallery) == 1 and len(gallery[0].value["images"]) == 2
    assert set(TelegramPost.objects.filter(media_group_id="g1").values_list("page", flat=True)) == {
        page.pk
    }
    # a photo before the caption becomes the picture of a video's caption
    _send(
        client, {"update_id": 4, "channel_post": _post(60, photo=photo("p"), media_group_id="g2")}
    )
    assert TelegramPost.objects.get(message_id=60).photo_file_id == "p"
    video = {"file_id": "v", "duration": 5}
    _send(
        client, {"update_id": 5, "channel_post": _post(61, text, video=video, media_group_id="g2")}
    )
    page = _page(61)
    assert page.image_id is not None and photos[-1] == "p"
    assert TelegramPost.objects.get(message_id=60).page_id == page.pk


@pytest.mark.django_db
def test_photo_without_words_is_not_news(seeded: Any, client: Client, bot: Any) -> None:
    before = PostPage.objects.count()
    _send(client, {"update_id": 1, "channel_post": _post(70, photo=[{"file_id": "x"}])})
    assert PostPage.objects.count() == before


@pytest.mark.django_db
def test_edit_updates_the_item_until_an_editor_changes_it(
    seeded: Any, client: Client, bot: Any, admin_user: Any
) -> None:
    _send(client, {"update_id": 1, "channel_post": _post(80, "Eski sarlavha\n\nEski matn.")})
    page = _page(80)
    _send(
        client, {"update_id": 2, "edited_channel_post": _post(80, "Yangi sarlavha\n\nYangi matn.")}
    )
    page.refresh_from_db()
    assert page.title == "Yangi sarlavha" and page.summary == "Yangi matn."
    assert page.live and not page.has_unpublished_changes
    # an editor's revision wins over later edits in the channel
    page.title = "Muharrir sarlavhasi"
    page.save_revision(user=admin_user).publish()
    _send(client, {"update_id": 3, "edited_channel_post": _post(80, "Uchinchi\n\nMatn.")})
    page.refresh_from_db()
    assert page.title == "Muharrir sarlavhasi"
    # an edit of a post the bot never saw makes a new item
    _send(client, {"update_id": 4, "edited_channel_post": _post(81, "Eski post\n\nMatn.")})
    assert TelegramPost.objects.get(message_id=81).page is not None


@pytest.mark.django_db
def test_other_chats_are_ignored(seeded: Any, client: Client, bot: Any) -> None:
    other = {**CHAT, "username": "someone_else", "id": -100999}
    group = {**CHAT, "type": "supergroup"}
    for chat in (other, group):
        message = {**_post(90, "Begona kanal\n\nMatn."), "chat": chat}
        assert _send(client, {"update_id": 1, "channel_post": message}).status_code == 200
    assert _send(client, {"update_id": 2, "message": _post(91, "Shaxsiy xabar")}).status_code == 200
    assert not TelegramPost.objects.exists()


@pytest.mark.django_db
def test_broken_update_is_skipped_not_retried(seeded: Any, client: Client, bot: Any) -> None:
    message = _post(95, "Sarlavha\n\nMatn.")
    message["message_id"] = "not-a-number"
    assert _send(client, {"update_id": 1, "channel_post": message}).status_code == 200
    assert _send(client, {"update_id": 2, "channel_post": []}).status_code == 200
    bad = client.post(
        "/telegram/webhook/",
        data="not json",
        content_type="application/json",
        headers={"X-Telegram-Bot-Api-Secret-Token": telegram.webhook_secret()},
    )
    assert bad.status_code == 400


@pytest.mark.django_db
def test_database_outage_asks_telegram_to_retry(
    client: Client, bot: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from django.db import OperationalError

    def down(update: dict[str, Any]) -> None:
        raise OperationalError("connection refused")

    monkeypatch.setattr(telegram, "handle_update", down)
    assert _send(client, {"update_id": 1, "channel_post": _post(1, "Matn")}).status_code == 500


# --- Bot API client ----------------------------------------------------------------------------
class _Answer(io.BytesIO):
    def __enter__(self) -> _Answer:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


def test_api_errors_never_carry_the_token(bot: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []

    def refuse(request: Any, timeout: float) -> Any:
        seen.append(request.full_url)
        body = io.BytesIO(b'{"ok": false, "description": "Bad Request: chat not found"}')
        raise urllib.error.HTTPError(request.full_url, 400, "Bad Request", {}, body)  # type: ignore[arg-type]

    monkeypatch.setattr(telegram._OPENER, "open", refuse)
    with pytest.raises(telegram.TelegramError) as caught:
        telegram.api("getChat", chat_id="@nobody")
    assert seen == [f"https://api.telegram.org/bot{TOKEN}/getChat"]
    assert str(caught.value) == "getChat: HTTP 400 Bad Request: chat not found"
    assert TOKEN not in str(caught.value) and caught.value.__cause__ is None

    def timeout(request: Any, timeout: float) -> Any:
        raise urllib.error.URLError(TimeoutError(f"timed out {request.full_url}"))

    monkeypatch.setattr(telegram._OPENER, "open", timeout)
    with pytest.raises(telegram.TelegramError) as caught:
        telegram.api("getMe")
    assert TOKEN not in str(caught.value)


def test_download_goes_to_the_file_endpoint(bot: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    urls: list[str] = []

    def answer(request: Any, timeout: float) -> Any:
        urls.append(request.full_url)
        if request.full_url.endswith("/getFile"):
            assert json.loads(request.data) == {"file_id": "abc"}
            return _Answer(b'{"ok": true, "result": {"file_path": "photos/file_1.jpg"}}')
        return _Answer(b"JPEGDATA")

    monkeypatch.setattr(telegram._OPENER, "open", answer)
    assert telegram.download("abc") == b"JPEGDATA"
    assert urls[1] == f"https://api.telegram.org/file/bot{TOKEN}/photos/file_1.jpg"
    monkeypatch.setattr(
        telegram, "api", lambda *a, **k: {"file_path": "../../etc/passwd", "file_size": 1}
    )
    with pytest.raises(telegram.TelegramError):
        telegram.download("abc")


def test_channel_name_forms(settings: Any) -> None:
    for value in ("erta_aniqla", "@erta_aniqla", "https://t.me/erta_aniqla/", "t.me/erta_aniqla"):
        settings.TELEGRAM_NEWS_CHANNEL = value
        assert telegram.channel_name() == "erta_aniqla"
        assert telegram.is_our_channel({**CHAT, "username": "Erta_Aniqla"})
    settings.TELEGRAM_NEWS_CHANNEL = ""
    assert not telegram.is_our_channel(CHAT)


def test_sentry_events_lose_the_bot_token() -> None:
    event: Any = {
        "exception": {"values": [{"value": f"GET https://api.telegram.org/bot{TOKEN}/getFile"}]},
        "request": {"headers": {"X-Telegram-Bot-Api-Secret-Token": "s3cret"}},
    }
    scrubbed = json.dumps(scrub_sentry_event(event, {}))
    assert TOKEN not in scrubbed and "s3cret" not in scrubbed


# --- setup command -----------------------------------------------------------------------------
@pytest.mark.django_db
def test_setup_command_registers_the_webhook(bot: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    bot.SITE_BASE_URL = "https://ertaaniqla.uz"
    calls: list[tuple[str, dict[str, Any]]] = []
    status = {"value": "administrator"}

    def fake_api(method: str, **params: Any) -> Any:
        calls.append((method, params))
        return {
            "getMe": {"id": 7, "username": "ertaaniqla_news_bot"},
            "getChat": {"id": CHAT["id"], "title": "Erta aniqla", "username": "erta_aniqla"},
            "getChatMember": {"status": status["value"]},
            "setWebhook": True,
            "getWebhookInfo": {
                "url": "https://ertaaniqla.uz/telegram/webhook/",
                "pending_update_count": 0,
            },
            "deleteWebhook": True,
        }[method]

    monkeypatch.setattr(telegram, "api", fake_api)
    out = io.StringIO()
    call_command("telegram_news", "setup", stdout=out)
    assert "https://ertaaniqla.uz/telegram/webhook/" in out.getvalue()
    method, params = calls[-1]
    assert method == "setWebhook" and params["secret_token"] == telegram.webhook_secret()
    assert params["allowed_updates"] == ["channel_post", "edited_channel_post"]
    assert calls[1] == ("getChat", {"chat_id": "@erta_aniqla"})
    call_command("telegram_news", "status", stdout=out)
    assert "pending_update_count: 0" in out.getvalue()
    status["value"] = "member"
    with pytest.raises(CommandError, match="not an admin"):
        call_command("telegram_news", "setup", stdout=out)
    status["value"] = "administrator"
    bot.SITE_BASE_URL = "http://localhost:8000"
    with pytest.raises(CommandError, match="https"):
        call_command("telegram_news", "setup", stdout=out)
    call_command("telegram_news", "remove", stdout=out)
    assert calls[-1][0] == "deleteWebhook"
