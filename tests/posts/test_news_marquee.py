"""«Yangiliklar»: two rows of news moving in opposite directions (D-112, after uzcombinator.uz)."""

from __future__ import annotations

import io
from datetime import date
from typing import Any

import pytest
from django.core.files.images import ImageFile
from django.test import Client
from PIL import Image

from apps.media_library.models import PortalImage
from apps.posts.models import MARQUEE_MIN_ITEMS, PostIndexPage, PostKind, PostPage

pytestmark = pytest.mark.django_db
CHANNEL = "/uz/yangiliklar/"


def _picture() -> PortalImage:
    buffer = io.BytesIO()
    Image.new("RGB", (800, 500), "pink").save(buffer, "PNG")
    image = PortalImage(title="Rasm", description="Rasm")
    image.file.save("marquee.png", ImageFile(buffer), save=False)
    image.width, image.height = 800, 500
    image.file_size = len(buffer.getvalue())
    image.save()
    return image


def _list(channel: bool = True) -> PostIndexPage:
    return PostIndexPage.objects.get(
        locale__language_code="uz", kind=PostKind.NEWS, telegram_feed=channel
    )


def _post(parent: PostIndexPage, title: str, day: int, image: Any, video: bool = False) -> PostPage:
    embed = {"type": "embed", "value": {"url": "https://t.me/erta_aniqla/1", "caption": ""}}
    page = PostPage(
        title=title, date=date(2026, 10, day), image=image, body=[embed] if video else []
    )
    parent.add_child(instance=page)
    page.save_revision().publish()
    return page


@pytest.fixture
def channel_posts(seeded: Any) -> PostIndexPage:
    parent = _list()
    image = _picture()
    for day in range(1, 11):
        _post(parent, f"Foto yangilik {day}", day, image)
    _post(parent, "Video seriya", 20, image, video=True)
    _post(parent, "Video seriya", 21, image, video=True)  # the same headline: one card
    _post(parent, "Rasmsiz yangilik", 22, None)
    return parent


def test_two_rows_move_apart_and_the_copy_stays_out_of_reach(
    channel_posts: PostIndexPage, client: Client
) -> None:
    html = client.get(CHANNEL).content.decode()
    marquee = html.split('class="news-marquee"', 1)[1].split("</section>", 1)[0]
    assert marquee.count('class="news-marquee__row') == 2
    assert marquee.count("news-marquee__row--reverse") == 1
    assert marquee.count('aria-hidden="true">') >= 2  # each row's copy
    assert marquee.count('class="news-marquee__card"') == 2 * 11  # 10 photos + 1 video headline
    assert marquee.count('tabindex="-1"') == 11
    assert "data-marquee-toggle" in marquee  # WCAG 2.2.2
    assert "Rasmsiz yangilik" not in marquee
    assert html.index('class="news-marquee"') < html.index('class="topic-filter')
    # every item stays in the plain list, the large first card gives way to the rows
    assert "news-feature" not in html
    assert html.split('id="post-grid"', 1)[1].count('class="news-card"') == 12


def test_photos_come_first_and_videos_fill_up(channel_posts: PostIndexPage) -> None:
    rows = channel_posts.get_marquee()
    items = [post for pair in zip(rows[0], rows[1], strict=False) for post in pair]
    assert items[0].title == "Foto yangilik 10"
    assert [post.title for post in rows[0] + rows[1]].count("Video seriya") == 1
    assert not any(post.leads_with_video for post in items[:9])


@pytest.mark.parametrize("query", ["?page=2", "?topic=breast"])
def test_only_on_the_first_unfiltered_page(
    channel_posts: PostIndexPage, client: Client, query: str
) -> None:
    assert 'class="news-marquee"' not in client.get(CHANNEL + query).content.decode()


def test_too_few_items_and_other_lists_keep_the_plain_page(seeded: Any, client: Client) -> None:
    image = _picture()
    for day in range(1, MARQUEE_MIN_ITEMS):
        _post(_list(), f"Yangilik {day}", day, image)
        _post(_list(channel=False), f"Maqola {day + 10}", day, image)
    _post(_list(channel=False), "Maqola 9", 9, image)
    html = client.get(CHANNEL).content.decode()
    assert 'class="news-marquee"' not in html and "news-feature" in html
    useful = client.get("/uz/foydali-malumotlar/").content.decode()
    assert 'class="news-marquee"' not in useful
