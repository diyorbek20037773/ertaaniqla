"""HomePage: both sections equally, hero, stats, featured content (spec §4.3, S-05)."""

from __future__ import annotations

import pytest
from django.test import Client

from apps.articles.models import ArticlePage
from apps.home.models import HomeFeaturedArticle, HomeFeaturedVideo, HomePage
from apps.media_library.models import Video, VideoSource

pytestmark = pytest.mark.django_db


def test_home_shows_both_section_cards(seeded, client: Client) -> None:
    """Both sections get the same capsule card, only colour and artwork differ (M5b)."""
    html = client.get("/uz/").content.decode()
    assert 'class="capsule-card" data-section="women"' in html
    assert 'class="capsule-card" data-section="children"' in html
    assert 'class="capsule-card__link" href="/uz/ayollar/"' in html
    assert 'class="capsule-card__link" href="/uz/bolalar/"' in html
    assert html.count('class="capsule-card"') == 2
    assert "Erta aniqla" in html
    assert html.count('class="stat"') == 3


def test_home_featured_articles_and_videos(seeded, client: Client) -> None:
    home = HomePage.objects.get(locale__language_code="uz")
    article = ArticlePage.objects.get(
        url_path__endswith="/ayollar/ogohlik/kokrak-bezi-saratoni/", locale__language_code="uz"
    )
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
    article = ArticlePage.objects.get(
        url_path__endswith="/ayollar/ogohlik/bachadon-boyni-saratoni/", locale__language_code="uz"
    )
    HomeFeaturedArticle.objects.create(page=home, article=article, sort_order=0)
    article.unpublish()
    html = client.get("/uz/").content.decode()
    assert "Featured" not in html or article.title not in html


def test_hero_title_splits_after_the_dash(seeded, client: Client) -> None:
    """Figma: «ERTA ANIQLA –» in the gradient, «HAYOTNI SAQLA» in grey below."""
    home = HomePage.objects.get(locale__language_code="uz")
    assert home.hero_title_parts == ("Erta aniqla –", "hayotni saqla")
    home.hero_title = "Faqat sarlavha"
    assert home.hero_title_parts == ("Faqat sarlavha", "")
    html = client.get("/uz/").content.decode()
    assert '<span class="hero__title-rest">hayotni saqla</span>' in html
    assert 'href="/uz/haqimizda/">Batafsil</a>' in html
    assert 'href="/uz/ayollar/qayerga-murojaat/">Murojaat qilish</a>' in html
