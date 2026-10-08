"""HomePage: both sections equally, hero, stats, featured content (spec §4.3, S-05)."""

from __future__ import annotations

import pytest
from django.core.management import call_command
from django.test import Client

from apps.articles.models import ArticlePage
from apps.home.models import HomeFeaturedArticle, HomeFeaturedVideo, HomePage
from apps.media_library.models import Video, VideoSource

pytestmark = pytest.mark.django_db


def test_home_final_design_blocks(seeded, client: Client) -> None:
    """Final design (D-081): direction cards, «Bepul skrining» panel and «Savolingiz bormi?»,
    every text from the CMS; seed_home_design fills only empty fields."""
    html = client.get("/uz/").content.decode()
    assert html.count('class="dir-card"') == 3  # one card per topic before the CMS is filled
    call_command("seed_home_design")
    html = client.get("/uz/").content.decode()
    for topic in ("breast", "cervical", "children"):
        assert f'class="dir-card" data-topic="{topic}"' in html
    assert 'href="/uz/ayollar/ogohlik/kokrak-bezi-saratoni/#belgilari"' in html
    assert 'href="/uz/ayollar/ogohlik/bachadon-boyni-saratoni/#aniqlash-usullari"' in html
    assert "Skriningdan qayerda oʻtish mumkin?" in html
    assert 'action="/uz/ayollar/qayerga-murojaat/"' in html and 'name="region"' in html
    assert "Savolingiz bormi?" in html
    assert 'class="stat"' not in html  # no stats strip in the design
    ru = client.get("/ru/").content.decode()
    assert "Где пройти скрининг?" in ru and 'href="/ru/zhenskiy/osvedomlennost/' in ru
    home = HomePage.objects.get(locale__language_code="uz")
    home.cta_title = "Tahrirlangan sarlavha"
    home.save_revision().publish()
    call_command("seed_home_design")  # an editor's text is never overwritten
    home.refresh_from_db()
    assert home.cta_title == "Tahrirlangan sarlavha"


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
    # design 2026-10: the landing shows the news / videos / articles feeds instead
    assert 'class="container home-block"' in html
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
    """Final design: «ERTA ANIQLA» in bold capitals, «hayotni saqla» in italics below with the
    first word in raspberry."""
    home = HomePage.objects.get(locale__language_code="uz")
    assert home.hero_title_parts == ("Erta aniqla –", "hayotni saqla")
    assert home.hero_title_lines == ("Erta aniqla", "hayotni", "saqla")
    html = client.get("/uz/").content.decode()
    assert '<span class="home-hero__main">Erta aniqla</span>' in html
    assert '<em class="home-hero__accent">hayotni</em> <em>saqla</em>' in html
    assert 'href="/uz/ayollar/qayerga-murojaat/">Skrining joyini toping' in html
    assert 'href="#yonalishlar">Yoʻnalishlar bilan tanishing</a>' in html
    home.hero_title = "Faqat sarlavha"
    assert home.hero_title_parts == ("Faqat sarlavha", "")
    assert home.hero_title_lines == ("Faqat sarlavha", "", "")
