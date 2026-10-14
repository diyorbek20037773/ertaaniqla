"""YouTube channel → «Videoroliklar» (D-085): feed parsing, topic guess, import once, covers kept
as our own images, the channel id from either URL form."""

from __future__ import annotations

from io import BytesIO

import pytest
from PIL import Image

from apps.media_library import youtube
from apps.media_library.models import Video, VideoSource, VideoStatus

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


def _jpeg() -> bytes:
    buffer = BytesIO()
    Image.effect_noise((640, 360), 60).convert("RGB").save(buffer, "JPEG")
    return buffer.getvalue()


def test_parse_feed_and_topic() -> None:
    videos = youtube.parse_feed(FEED)
    assert [v.video_id for v in videos] == ["AAAAAAAAAAA", "BBBBBBBBBBB"]
    assert videos[0].title.startswith("Ko")
    assert youtube.guess_topic(f"{videos[0].title} {videos[0].description}") == "breast"
    assert youtube.guess_topic("Bachadon boʻyni saratoni va HPV") == "cervical"
    assert youtube.guess_topic("Bolalar onkologiyasi") == "children"
    assert youtube.guess_topic("Forum lavhalari") == ""


def test_channel_id_from_url(monkeypatch) -> None:
    assert youtube.channel_id("https://www.youtube.com/channel/UChtzDub2Q1cTIC3Nl_Uk9Cg") == (
        "UChtzDub2Q1cTIC3Nl_Uk9Cg"
    )
    page = b'<script>{"externalId":"UChtzDub2Q1cTIC3Nl_Uk9Cg"}</script>'
    monkeypatch.setattr(youtube, "_get", lambda url: page)
    assert youtube.channel_id("https://www.youtube.com/@ertaaniqla") == "UChtzDub2Q1cTIC3Nl_Uk9Cg"
    assert youtube.channel_id("https://example.com/video") == ""


def test_get_refuses_other_schemes() -> None:
    with pytest.raises(ValueError):
        youtube._get("file:///etc/passwd")


@pytest.mark.django_db
def test_sync_imports_once_with_our_own_cover(monkeypatch) -> None:
    cover = _jpeg()

    def fake_get(url: str) -> bytes:
        return FEED if "feeds/videos.xml" in url else cover

    monkeypatch.setattr(youtube, "_get", fake_get)
    added = youtube.sync_channel("https://www.youtube.com/channel/UChtzDub2Q1cTIC3Nl_Uk9Cg")
    assert added == ["AAAAAAAAAAA", "BBBBBBBBBBB"]
    assert youtube.sync_channel("https://www.youtube.com/channel/UChtzDub2Q1cTIC3Nl_Uk9Cg") == []
    video = Video.objects.get(external_url__contains="AAAAAAAAAAA")
    assert video.source == VideoSource.YOUTUBE and video.status == VideoStatus.READY
    assert video.topic == "breast"
    assert video.poster is not None and (video.poster.width, video.poster.height) == (640, 360)
    assert video.poster.credit == "YouTube"


@pytest.mark.django_db
def test_sync_never_raises(monkeypatch) -> None:
    def broken(url: str) -> bytes:
        raise OSError("offline")

    monkeypatch.setattr(youtube, "_get", broken)
    monkeypatch.setattr(
        youtube,
        "channel_url_from_settings",
        lambda: "https://www.youtube.com/channel/UChtzDub2Q1cTIC3Nl_Uk9Cg",
    )
    assert youtube.sync_from_settings() == []


@pytest.mark.django_db
def test_sync_restores_a_lost_cover(monkeypatch) -> None:
    cover = _jpeg()
    monkeypatch.setattr(youtube, "_get", lambda url: FEED if "feeds/videos.xml" in url else cover)
    youtube.sync_channel("https://www.youtube.com/channel/UChtzDub2Q1cTIC3Nl_Uk9Cg")
    video = Video.objects.get(external_url__contains="AAAAAAAAAAA")
    video.poster.file.storage.delete(video.poster.file.name)  # the disk lost the file
    youtube.sync_channel("https://www.youtube.com/channel/UChtzDub2Q1cTIC3Nl_Uk9Cg")
    video.refresh_from_db()
    assert video.poster.file.storage.exists(video.poster.file.name)
