"""D-097, D-101: the video description (uz / ru) and the client's videos of 2026-10-19/20."""

from __future__ import annotations

from typing import Any

import pytest
from django.core.management import call_command

from apps.media_library import youtube
from apps.media_library.client_videos import VIDEOS, VIDEOS_20261020
from apps.media_library.models import Video, VideoSource, VideoStatus


@pytest.fixture
def covers(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """No network: YouTube «has no cover»; returns the ids a cover was asked for."""
    asked: list[str] = []

    def no_cover(video_id: str, title: str, deadline: float | None = None) -> Any:
        asked.append(video_id)
        return None

    monkeypatch.setattr(youtube, "_poster", no_cover)
    return asked


def _video_id(video: Video) -> str:
    return video.external_url.rsplit("=", 1)[1]


@pytest.mark.django_db
def test_client_videos_are_added_once_and_editors_keep_their_changes(covers) -> None:
    call_command("client_update_20261019")
    videos = list(Video.objects.order_by("-created_at", "-pk"))
    # the client's first video is the newest: it heads the «Videoroliklar» list
    assert [_video_id(v) for v in videos] == [item.video_id for item in VIDEOS]
    first = videos[0]
    assert first.title == "KOʻKRAK BEZI SARATONINING DAVOSI BORMI?"
    assert first.title_ru == "Возможно ли вылечиться от рака молочной железы?"
    assert first.description.startswith("Taniqli radio boshlovchi")
    assert first.description_ru.startswith("Известная радиоведущая")
    assert first.topic == "breast"
    assert all(v.source == VideoSource.YOUTUBE and v.status == VideoStatus.READY for v in videos)
    assert all(v.description and v.description_ru and v.title_ru for v in videos)
    assert len(covers) == len(VIDEOS)

    first.title_ru = "Свой заголовок"
    first.description = ""
    first.save()
    call_command("client_update_20261019")
    first.refresh_from_db()
    assert first.title_ru == "Свой заголовок"  # an editor's change stays
    assert first.description.startswith("Taniqli")  # an emptied field is filled again
    assert Video.objects.count() == len(VIDEOS)
    assert len(covers) == len(VIDEOS)  # no second download


@pytest.mark.django_db
def test_the_second_batch_lands_above_the_first(covers) -> None:
    call_command("client_update_20261019")
    call_command("client_update_20261020")
    videos = list(Video.objects.order_by("-created_at", "-pk"))
    order = [item.video_id for item in (*VIDEOS_20261020, *VIDEOS)]
    assert [_video_id(v) for v in videos] == order
    cervical = Video.objects.get(external_url__contains="XAeJ1-1K6hQ")
    assert cervical.topic == "cervical" and cervical.description == ""
    assert cervical.title_ru == "Передается ли рак шейки матки половым путём?"
    call_command("client_update_20261020")
    assert Video.objects.count() == len(order)


def test_client_texts_use_the_uzbek_apostrophes() -> None:
    """ʻ (U+02BB) and ʼ (U+02BC) only, never ‘ ’ or ' (project rule)."""
    for item in (*VIDEOS, *VIDEOS_20261020):
        for text in (item.title, item.description):
            assert not set(text) & {"‘", "’", "'"}, (item.video_id, text)


@pytest.mark.django_db
def test_watch_page_shows_the_description_of_its_language(seeded, client) -> None:
    video = Video.objects.create(
        title="Mammografiya haqida",
        description="Birinchi qism.\n\nIkkinchi qism.",
        description_ru="Первая часть.",
        transcript="<p>Matn</p>",
        source=VideoSource.YOUTUBE,
        external_url="https://www.youtube.com/watch?v=AAAAAAAAAAA",
        status=VideoStatus.READY,
    )
    uz = client.get(f"/uz/videoroliklar/{video.pk}/").content.decode()
    assert "<p>Birinchi qism.</p>" in uz and "<p>Ikkinchi qism.</p>" in uz
    assert '<meta name="description" content="Birinchi qism. Ikkinchi qism.">' in uz
    ru = client.get(f"/ru/video/{video.pk}/").content.decode()
    assert "<p>Первая часть.</p>" in ru and "Birinchi" not in ru
    assert '<meta property="og:description" content="Первая часть.">' in ru

    video.description_ru = ""
    video.save()
    ru = client.get(f"/ru/video/{video.pk}/").content.decode()
    assert "video__description" not in ru and "Birinchi" not in ru  # no Uzbek fallback
    assert '<meta name="description" content="Matn">' in ru  # the transcript, as before
