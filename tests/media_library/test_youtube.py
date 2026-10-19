"""YouTube channel → «Videoroliklar» (D-085): feed parsing, topic guess, import once, covers kept
as our own images, the channel id from either URL form; the feed's 404s tried again, the channel
page as the fallback, the throttle shortened after a failed run, requests kept on YouTube."""

from __future__ import annotations

import http.client
import json
import time
import urllib.request
from collections.abc import Callable
from io import BytesIO
from typing import Any

import pytest
from django.core.cache import cache
from PIL import Image

from apps.media_library import youtube
from apps.media_library.models import PortalImage, Video, VideoKind, VideoSource, VideoStatus

CHANNEL = "https://www.youtube.com/channel/UChtzDub2Q1cTIC3Nl_Uk9Cg"
CID = "UChtzDub2Q1cTIC3Nl_Uk9Cg"
FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015"
 xmlns:media="http://search.yahoo.com/mrss/" xmlns="http://www.w3.org/2005/Atom">
 <entry>
  <yt:videoId>AAAAAAAAAAA</yt:videoId>
  <title>Ko\xe2\x80\x98krak bezi saratoni diagnostikasi</title>
  <published>2026-09-28T08:40:31+00:00</published>
  <media:group><media:description>Mammografiya haqida</media:description></media:group>
 </entry>
 <entry>
  <yt:videoId>BBBBBBBBBBB</yt:videoId>
  <title>Forum lavhalari</title>
  <published>2026-10-13T07:40:35+00:00</published>
  <media:group><media:description>Toshkent</media:description></media:group>
 </entry>
</feed>"""
# the start of YouTube's real answer when the feed is down (2026-10-16)
FEED_404 = (
    b"<!DOCTYPE html>\n<html lang=en>\n  <meta charset=utf-8>\n  <title>Error 404 (Not Found)!!1"
)


def _lockup(video_id: str, title: str, kind: str = "LOCKUP_CONTENT_TYPE_VIDEO") -> dict[str, Any]:
    meta = {"lockupMetadataViewModel": {"title": {"content": title}}}
    return {"lockupViewModel": {"contentId": video_id, "contentType": kind, "metadata": meta}}


def _page(items: list[dict[str, Any]], tab_url: str = "/@ertaaniqla/videos") -> bytes:
    """A channel page as YouTube serves it: `ytInitialData` in a script, the selected tab's grid."""

    def endpoint(url: str) -> dict[str, Any]:
        return {"commandMetadata": {"webCommandMetadata": {"url": url}}}

    grid = {"richGridRenderer": {"contents": [{"richItemRenderer": {"content": i}} for i in items]}}
    tabs = [
        {"tabRenderer": {"title": "Home", "endpoint": endpoint("/@ertaaniqla/featured")}},
        {"tabRenderer": {"selected": True, "endpoint": endpoint(tab_url), "content": grid}},
    ]
    data = {"contents": {"twoColumnBrowseResultsRenderer": {"tabs": tabs}}}
    return f"<html><script>var ytInitialData = {json.dumps(data)};</script></html>".encode()


PAGE = _page(
    [
        _lockup("CCCCCCCCCCC", "Bachadon boʻyni saratoni skriningi"),
        _lockup("PL" + "x" * 32, "Pleylist", "LOCKUP_CONTENT_TYPE_PLAYLIST"),
        {"videoRenderer": {"videoId": "DDDDDDDDDDD", "title": {"runs": [{"text": "Forum "}]}}},
        {
            "shortsLockupViewModel": {
                "onTap": {"innertubeCommand": {"reelWatchEndpoint": {"videoId": "EEEEEEEEEEE"}}},
                "overlayMetadata": {"primaryText": {"content": "Qisqa video"}},
            }
        },
    ]
)


def _jpeg() -> bytes:
    buffer = BytesIO()
    Image.effect_noise((640, 360), 60).convert("RGB").save(buffer, "JPEG")
    return buffer.getvalue()


def _youtube(
    feed: bytes | None = FEED,
    page: bytes | None = PAGE,
    cover: bytes | None = None,
    calls: list[str] | None = None,
) -> Callable[[str], bytes]:
    """A stand-in for `youtube._get`: the feed, the channel page, covers; None answers 404."""

    def fake_get(url: str) -> bytes:
        if calls is not None:
            calls.append(url)
        if "feeds/videos.xml" in url:
            body = feed
        elif url.endswith("/videos"):
            body = page
        else:
            body = cover
        if body is None:
            raise youtube.FetchError(url, "HTTP 404", 404)
        return body

    return fake_get


def _expires_in(key: str) -> float:
    """Seconds left on a key of the test cache (LocMemCache keeps each key's expiry)."""
    return float(cache._expire_info[cache.make_key(key)]) - time.time()


@pytest.fixture(autouse=True)
def sleeps(monkeypatch) -> list[float]:
    """No real pauses between tries; the pauses asked for are recorded."""
    asked: list[float] = []
    monkeypatch.setattr(youtube, "_sleep", asked.append)
    return asked


def test_parse_feed_and_topic() -> None:
    videos = youtube.parse_feed(FEED)
    assert [v.video_id for v in videos] == ["AAAAAAAAAAA", "BBBBBBBBBBB"]
    assert videos[0].title.startswith("Ko")
    assert youtube.guess_topic(f"{videos[0].title} {videos[0].description}") == "breast"
    assert youtube.guess_topic("Bachadon boʻyni saratoni va HPV") == "cervical"
    assert youtube.guess_topic("Bolalar onkologiyasi") == "children"
    assert youtube.guess_topic("Forum lavhalari") == ""


def test_parse_feed_skips_bad_entries_and_refuses_what_is_not_a_feed() -> None:
    feed = FEED.replace(b"BBBBBBBBBBB", b"../../x").replace(b"2026-09-28T08:40:31", b"kecha")
    videos = youtube.parse_feed(feed)
    assert [v.video_id for v in videos] == ["AAAAAAAAAAA"]
    assert videos[0].published is None
    for body in (FEED_404, b'<?xml version="1.0"?><!DOCTYPE f [<!ENTITY a "a">]><f>&a;</f>'):
        with pytest.raises(ValueError):
            youtube.parse_feed(body)


def test_parse_feed_marks_shorts() -> None:
    short = b'<link rel="alternate" href="https://www.youtube.com/shorts/BBBBBBBBBBB"/>'
    feed = FEED.replace(b"<title>Forum", short + b"<title>Forum")
    assert [v.short for v in youtube.parse_feed(feed)] == [False, True]


def test_parse_videos_page() -> None:
    videos = youtube.parse_videos_page(PAGE.decode())
    assert [(v.video_id, v.title, v.short) for v in videos] == [
        ("CCCCCCCCCCC", "Bachadon boʻyni saratoni skriningi", False),
        ("DDDDDDDDDDD", "Forum", False),
        ("EEEEEEEEEEE", "Qisqa video", True),
    ]  # the playlist is not a video
    assert videos[0].description == "" and videos[0].published is None


@pytest.mark.parametrize(
    "html",
    [
        "<html><title>Before you continue to YouTube</title></html>",  # consent or error page
        _page([_lockup("CCCCCCCCCCC", "x")], tab_url="/@ertaaniqla/featured").decode(),
        _page([]).decode(),  # YouTube renamed its renderers
        "<script>var ytInitialData = " + "[" * 100_000 + "</script>",  # deeper than json allows
        '<script>var ytInitialData = {"contents": </script>',  # cut off
    ],
    ids=["consent-page", "other-tab", "no-renderers", "too-deep", "cut-off"],
)
def test_parse_videos_page_refuses_a_page_without_videos(html: str) -> None:
    with pytest.raises(ValueError):
        youtube.parse_videos_page(html)


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "http://www.youtube.com/feeds/videos.xml",
        "https://example.com/",
        "https://www.youtube.com.example.com/",
        "https://user@www.youtube.com/",
        "https://www.youtube.com:8443/",
    ],
)
def test_get_refuses_other_schemes_and_hosts(url: str) -> None:
    with pytest.raises(ValueError):
        youtube._get(url)


def test_redirects_stay_on_youtube() -> None:
    handler = youtube._YouTubeRedirects()
    request = urllib.request.Request("https://www.youtube.com/@ertaaniqla")
    for target in ("http://169.254.169.254/latest/", "https://consent.youtube.com/m?continue=x"):
        with pytest.raises(youtube.FetchError):
            handler.redirect_request(
                request, BytesIO(), 302, "Found", http.client.HTTPMessage(), target
            )
    moved = handler.redirect_request(
        request, BytesIO(), 301, "Moved", http.client.HTTPMessage(), CHANNEL
    )
    assert moved is not None and moved.full_url == CHANNEL


def test_get_caps_the_size(monkeypatch) -> None:
    asked: list[urllib.request.Request] = []

    class Opener:
        def open(self, request: urllib.request.Request, timeout: float) -> BytesIO:
            asked.append(request)
            return BytesIO(b"x" * (youtube.MAX_IMAGE_BYTES + 1))

    monkeypatch.setattr(youtube, "_OPENER", Opener())
    with pytest.raises(youtube.FetchError):
        youtube._get("https://i.ytimg.com/vi/AAAAAAAAAAA/hqdefault.jpg")
    assert len(youtube._get(f"{CHANNEL}/videos")) == youtube.MAX_IMAGE_BYTES + 1
    assert asked[0].get_header("Cookie") is None  # the cover host gets no cookie
    assert asked[1].get_header("Cookie") == youtube.CONSENT_COOKIE


def test_channel_id_from_url(monkeypatch) -> None:
    assert youtube.channel_id(CHANNEL) == CID
    page = b'<script>{"externalId":"UChtzDub2Q1cTIC3Nl_Uk9Cg"}</script>'
    monkeypatch.setattr(youtube, "_get", lambda url: page)
    assert youtube.channel_id("https://www.youtube.com/@ertaaniqla") == CID
    assert youtube.channel_id("https://example.com/video") == ""


def test_channel_id_from_any_handle_url(monkeypatch) -> None:
    asked: list[str] = []
    canonical = (
        b'<link rel="canonical" href="https://www.youtube.com/channel/UChtzDub2Q1cTIC3Nl_Uk9Cg">'
    )
    monkeypatch.setattr(youtube, "_get", lambda url: asked.append(url) or canonical)
    assert youtube.channel_id("https://youtube.com/@ertaaniqla/videos?si=x") == CID
    assert youtube.channel_id("https://m.youtube.com/@ertaaniqla") == CID  # cached
    assert asked == ["https://www.youtube.com/@ertaaniqla"]
    # a featured channel's bare "channelId" is not taken for the channel's own
    monkeypatch.setattr(youtube, "_get", lambda url: b'{"channelId":"UC' + b"x" * 22 + b'"}')
    assert youtube.channel_id("https://www.youtube.com/@boshqa") == ""


def test_feed_404s_are_tried_again(monkeypatch, sleeps) -> None:
    answers = iter([None, None, FEED])

    def flaky(url: str) -> bytes:
        body = next(answers)
        if body is None:
            raise youtube.FetchError(url, "HTTP 404", 404)
        return body

    monkeypatch.setattr(youtube, "_get", flaky)
    videos, source = youtube.fetch_videos(CID)
    assert source == "feed" and len(videos) == 2
    assert sleeps == list(youtube.FEED_RETRY_DELAYS)


def test_a_refusal_is_not_tried_again(monkeypatch, sleeps) -> None:
    calls: list[str] = []

    def refused(url: str) -> bytes:
        calls.append(url)
        raise youtube.FetchError(url, "HTTP 403", 403)

    monkeypatch.setattr(youtube, "_get", refused)
    with pytest.raises(youtube.SyncError):
        youtube.fetch_videos(CID)
    assert calls == [youtube.FEED_URL.format(CID), youtube.VIDEOS_PAGE_URL.format(CID)]
    assert sleeps == []


@pytest.mark.django_db
def test_sync_imports_once_with_our_own_cover(monkeypatch) -> None:
    monkeypatch.setattr(youtube, "_get", _youtube(cover=_jpeg()))
    added = youtube.sync_channel(CHANNEL)
    assert added == ["AAAAAAAAAAA", "BBBBBBBBBBB"]
    assert youtube.sync_channel(CHANNEL) == []
    video = Video.objects.get(external_url__contains="AAAAAAAAAAA")
    assert video.source == VideoSource.YOUTUBE and video.status == VideoStatus.READY
    assert video.topic == "breast" and video.kind == VideoKind.LONG
    assert video.poster is not None and (video.poster.width, video.poster.height) == (640, 360)
    assert video.poster.credit == "YouTube"


@pytest.mark.django_db
def test_feed_down_the_channel_page_is_read(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(youtube, "_get", _youtube(feed=None, cover=_jpeg(), calls=calls))
    assert youtube.sync_channel(CHANNEL) == ["CCCCCCCCCCC", "DDDDDDDDDDD", "EEEEEEEEEEE"]
    assert calls.count(youtube.FEED_URL.format(CID)) == 1 + len(youtube.FEED_RETRY_DELAYS)
    assert Video.objects.get(external_url__contains="CCCCCCCCCCC").topic == "cervical"
    assert Video.objects.get(external_url__contains="EEEEEEEEEEE").kind == VideoKind.SHORT_VERTICAL


@pytest.mark.django_db
def test_topic_from_the_title_before_the_description(monkeypatch) -> None:
    feed = FEED.replace(b"Forum lavhalari", b"Bachadon bo'yni").replace(b"Toshkent", b"ko'krak")
    monkeypatch.setattr(youtube, "_get", _youtube(feed=feed))
    youtube.sync_channel(CHANNEL)
    assert Video.objects.get(external_url__contains="BBBBBBBBBBB").topic == "cervical"


@pytest.mark.django_db
def test_a_cover_that_is_not_an_image_is_skipped(monkeypatch) -> None:
    monkeypatch.setattr(youtube, "_get", _youtube(cover=b"<html>" + b"x" * 5000))
    assert youtube.sync_channel(CHANNEL) == ["AAAAAAAAAAA", "BBBBBBBBBBB"]
    assert Video.objects.get(external_url__contains="AAAAAAAAAAA").poster is None
    assert not PortalImage.objects.exists()


@pytest.mark.django_db
def test_sync_restores_a_lost_cover(monkeypatch) -> None:
    monkeypatch.setattr(youtube, "_get", _youtube(cover=_jpeg()))
    youtube.sync_channel(CHANNEL)
    video = Video.objects.get(external_url__contains="AAAAAAAAAAA")
    video.poster.file.storage.delete(video.poster.file.name)  # the disk lost the file
    youtube.sync_channel(CHANNEL)
    video.refresh_from_db()
    assert video.poster.file.storage.exists(video.poster.file.name)


@pytest.mark.django_db
def test_an_unreachable_cover_does_not_flush_the_page_cache(monkeypatch) -> None:
    from apps.core.cache import page_cache_version

    monkeypatch.setattr(youtube, "_get", _youtube())  # every cover answers 404
    youtube.sync_channel(CHANNEL)
    version = page_cache_version()
    youtube.sync_channel(CHANNEL)
    assert page_cache_version() == version


@pytest.mark.django_db
def test_covers_wait_once_the_run_budget_is_spent(monkeypatch) -> None:
    """One time budget for the whole run: a slow YouTube cannot keep the start-up sync (before
    gunicorn) busy with cover downloads; the videos come in now, their covers on a later run."""
    calls: list[str] = []
    # 0 s until YouTube answered the list, then the budget is spent
    monkeypatch.setattr(youtube.time, "monotonic", lambda: 100.0 if calls else 0.0)
    monkeypatch.setattr(youtube, "_get", _youtube(cover=_jpeg(), calls=calls))
    assert youtube.sync_channel(CHANNEL) == ["AAAAAAAAAAA", "BBBBBBBBBBB"]
    assert not any("i.ytimg.com" in url for url in calls)
    assert Video.objects.get(external_url__contains="AAAAAAAAAAA").poster is None
    monkeypatch.setattr(youtube.time, "monotonic", time.perf_counter)
    youtube.sync_channel(CHANNEL)  # the next run has time: the cover is restored
    assert Video.objects.get(external_url__contains="AAAAAAAAAAA").poster is not None


def test_a_second_sync_waits_for_the_running_one(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(youtube, "_get", _youtube(calls=calls))
    cache.add(youtube.LOCK_KEY, 1, 60)
    assert youtube.sync_channel(CHANNEL) == []
    assert calls == []


def test_sync_never_raises(monkeypatch) -> None:
    def broken(url: str) -> bytes:
        raise OSError("offline")

    monkeypatch.setattr(youtube, "_get", broken)
    monkeypatch.setattr(youtube, "channel_url_from_settings", lambda: CHANNEL)
    assert youtube.sync_from_settings() == []


def test_a_failed_run_is_tried_again_in_5_minutes(monkeypatch) -> None:
    monkeypatch.setattr(youtube, "_get", _youtube(feed=None, page=FEED_404))
    monkeypatch.setattr(youtube, "channel_url_from_settings", lambda: CHANNEL)
    assert youtube.sync_from_settings() == []
    assert 0 < _expires_in(youtube.THROTTLE_KEY) <= youtube.FAILURE_THROTTLE_SECONDS


@pytest.mark.django_db
def test_a_run_that_reached_youtube_waits_30_minutes(monkeypatch) -> None:
    monkeypatch.setattr(youtube, "_get", _youtube())
    monkeypatch.setattr(youtube, "channel_url_from_settings", lambda: CHANNEL)
    assert youtube.sync_from_settings() == ["AAAAAAAAAAA", "BBBBBBBBBBB"]
    left = _expires_in(youtube.THROTTLE_KEY)
    assert youtube.FAILURE_THROTTLE_SECONDS < left <= youtube.THROTTLE_SECONDS


def test_sync_soon_starts_one_run_per_window(monkeypatch) -> None:
    runs: list[str] = []

    class NowThread:
        def __init__(self, target: Callable[[], None], name: str, daemon: bool) -> None:
            self.target = target

        def start(self) -> None:
            self.target()

    monkeypatch.setattr(youtube.threading, "Thread", NowThread)
    monkeypatch.setattr(youtube, "sync_from_settings", lambda: runs.append("run") or [])
    youtube.sync_soon()
    youtube.sync_soon()
    assert runs == ["run"]


@pytest.mark.django_db
def test_no_try_starts_after_the_budget(monkeypatch) -> None:
    """A slow YouTube: after the feed's tries ran into the budget, the channel page is not tried
    at all (the run would otherwise outlast the host's health check)."""
    calls: list[str] = []
    monkeypatch.setattr(youtube.time, "monotonic", lambda: 100.0 if calls else 0.0)
    monkeypatch.setattr(youtube, "_get", _youtube(feed=None, calls=calls))
    with pytest.raises(youtube.SyncError, match="time budget"):
        youtube.sync_channel(CHANNEL)
    assert calls == [youtube.FEED_URL.format(CID)]  # one try; no retry, no page


@pytest.mark.django_db
def test_a_cover_missing_outside_the_feed_is_restored(monkeypatch) -> None:
    """The feed lists only the latest videos: a video the sync made without its cover (no time
    left) still gets it once the feed no longer lists it; a video an editor made, or whose cover
    an editor removed, is left alone."""
    for video_id, title in (("ZZZZZZZZZZZ", "Sinxron"), ("YYYYYYYYYYY", "Muharrir")):
        Video.objects.create(
            title=title,
            source=VideoSource.YOUTUBE,
            external_url=f"https://www.youtube.com/watch?v={video_id}",
            status=VideoStatus.READY,
        )
    cache.set(youtube.COVER_PENDING_KEY.format("ZZZZZZZZZZZ"), 1, 60)  # what the sync left
    calls: list[str] = []
    monkeypatch.setattr(youtube, "_get", _youtube(cover=_jpeg(), calls=calls))
    youtube.sync_channel(CHANNEL)
    assert Video.objects.get(external_url__contains="ZZZZZZZZZZZ").poster is not None
    assert cache.get(youtube.COVER_PENDING_KEY.format("ZZZZZZZZZZZ")) is None
    assert Video.objects.get(external_url__contains="YYYYYYYYYYY").poster is None
    assert not any("YYYYYYYYYYY" in url for url in calls)


@pytest.mark.django_db
def test_a_cover_youtube_does_not_have_is_tried_once_a_day(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(youtube, "_get", _youtube(calls=calls))  # every cover answers 404
    youtube.sync_channel(CHANNEL)  # made without covers: pending
    youtube.sync_channel(CHANNEL)  # one more try each, then a day's rest
    tries = sum("i.ytimg.com" in url for url in calls)
    youtube.sync_channel(CHANNEL)
    assert sum("i.ytimg.com" in url for url in calls) == tries


def test_a_run_that_outlived_its_lock_keeps_the_next_runs_lock(monkeypatch) -> None:
    def slow_list(cid: str, deadline: float) -> tuple[list[Any], str]:
        cache.set(youtube.LOCK_KEY, "next-run", 60)  # our lock expired, another run took it
        return [], "feed"

    monkeypatch.setattr(youtube, "fetch_videos", slow_list)
    monkeypatch.setattr(youtube, "_restore_covers", lambda deadline, skip: 0)
    youtube.sync_channel(CHANNEL)
    assert cache.get(youtube.LOCK_KEY) == "next-run"
