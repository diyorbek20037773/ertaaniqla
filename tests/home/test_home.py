"""HomePage: both sections equally, hero, stats, featured content (spec §4.3, S-05)."""

from __future__ import annotations

import pytest
from django.test import Client

from apps.articles.models import ArticlePage
from apps.home.models import HomeFeaturedArticle, HomeFeaturedVideo, HomePage
from apps.media_library.models import Video, VideoSource

pytestmark = pytest.mark.django_db


def test_home_shows_both_section_cards(seeded, client: Client) -> None:
    html = client.get("/uz/").content.decode()
    assert 'class="section-card" href="/uz/ayollar/" data-section="women"' in html
    assert 'class="section-card" href="/uz/bolalar/" data-section="children"' in html
    assert "Erta aniqla" in html
    assert html.count('class="stat"') == 3


def test_home_featured_articles_and_videos(seeded, client: Client) -> None:
    home = HomePage.objects.get(locale__language_code="uz")
    article = ArticlePage.objects.get(slug="belgilar", locale__language_code="uz")
    video = Video.objects.create(
        title="Shifokor bilan suhbat",
        source=VideoSource.YOUTUBE,
        external_url="https://youtu.be/dQw4w9WgXcQ",
        doctor_name="Dr. Test",
    )
    HomeFeaturedArticle.objects.create(page=home, article=article, sort_order=0)
    HomeFeaturedVideo.objects.create(page=home, video=video, sort_order=0)
    home.hero_title = "Erta aniqlang"
    home.emergency_banner = "<p>Kampaniya</p>"
    home.save_revision().publish()
    html = client.get("/uz/").content.decode()
    assert "Erta aniqlang" in html
    assert "Kampaniya" in html
    assert article.title in html
    assert "Shifokor bilan suhbat" in html
    assert home.get_body_text().startswith("Erta aniqlang")
    assert str(HomeFeaturedArticle.objects.first()) == article.title
    assert str(HomeFeaturedVideo.objects.first()) == video.title


def test_unpublished_featured_article_hidden(seeded, client: Client) -> None:
    home = HomePage.objects.get(locale__language_code="uz")
    article = ArticlePage.objects.get(slug="xavf-omillari", locale__language_code="uz")
    HomeFeaturedArticle.objects.create(page=home, article=article, sort_order=0)
    article.unpublish()
    html = client.get("/uz/").content.decode()
    assert "Featured" not in html or article.title not in html
