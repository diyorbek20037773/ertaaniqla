"""Client requests of 2026-10-15 (docs/new_task_15.10.26, D-087): «Bolalar saratoni» hidden,
the «coming soon» note, no editor placeholders for visitors, «Foydali maʼlumotlar» in the
header, the lex.uz resolutions on «Biz haqimizda», the first news item."""

from __future__ import annotations

import json
import re

import pytest
from django.core.management import call_command
from django.test import Client
from wagtail.models import Page, Site

from apps.core.models import SiteSettings
from apps.core.placeholders import strip_placeholders
from apps.posts.models import PostPage

pytestmark = pytest.mark.django_db


def _main(html: str) -> str:
    return html.split("<main", 1)[1].split("</main>", 1)[0]


def test_children_section_is_hidden_by_default(seeded, client: Client) -> None:
    for url in ("/uz/bolalar/", "/ru/detskiy/", "/uz/vositalar/bolalar-belgilari/"):
        assert client.get(url).status_code == 404, url
    html = client.get("/uz/").content.decode()
    assert 'data-section="children"' not in html  # header sections menu
    assert 'href="/uz/bolalar/' not in html  # menu, footer site map, landing cards
    assert 'data-topic="children"' not in html and "topic=children" not in html
    news = client.get("/uz/yangiliklar/?topic=children").content.decode()
    assert "topic=children" not in news  # neither a pill nor an accepted filter
    assert 'value="children"' not in client.get("/uz/ayollar/qayerga-murojaat/").content.decode()
    tools = client.get("/uz/vositalar/").content.decode()
    assert "bolalar-belgilari" not in tools
    sitemap = client.get("/uz/sitemap.xml").content.decode()
    assert "/uz/ayollar/" in sitemap and "/uz/bolalar/" not in sitemap
    results = client.get("/uz/qidiruv/?q=Diagnostika").content.decode()
    assert "/uz/bolalar/" not in results
    # editors still preview the hidden pages in the CMS
    page = Page.objects.get(url_path__endswith="/bolalar/", locale__language_code="uz")
    assert page.live


def test_children_section_comes_back_with_the_setting(seeded, client: Client) -> None:
    settings_obj = SiteSettings.for_site(Site.objects.get(is_default_site=True))
    settings_obj.show_children_section = True
    settings_obj.save()
    assert client.get("/uz/bolalar/").status_code == 200
    assert 'data-section="children"' in client.get("/uz/").content.decode()


def test_landing_note_under_the_two_cards(seeded, client: Client) -> None:
    call_command("seed_home_design")
    html = client.get("/uz/").content.decode()
    assert html.count('class="dir-card"') == 2
    assert '<p class="dir-note">Ushbu platformada yaqin vaqt ichida bolalar saratoni' in html
    assert "prostata bezi saratoniga bagʻishlangan" in html
    assert 'class="dir-note">В ближайшее время' in client.get("/ru/").content.decode()


def test_useful_information_in_the_header(seeded, client: Client) -> None:
    html = client.get("/uz/").content.decode()
    assert re.search(r'href="/uz/yangiliklar/"[^>]*>Foydali maʼlumotlar</a>', html)
    ru = client.get("/ru/").content.decode()
    assert re.search(r'href="/ru/novosti/"[^>]*>Полезная информация</a>', ru)


def test_placeholders_never_reach_visitors(seeded, client: Client) -> None:
    url = "/uz/ayollar/skrining/bachadon-boyni-saratoni/"
    page = Page.objects.get(url_path__endswith=url[3:], locale__language_code="uz").specific
    assert "[[VERIFY" in json.dumps(list(page.body.raw_data))  # still in the CMS for editors
    for path in (url, "/ru/zhenskiy/skrining/", "/uz/", "/oz/ayollar/skrining/"):
        html = client.get(path, follow=True).content.decode()
        assert "[[" not in html and "Matn shifokor tekshiruvini kutmoqda" not in html, path
        assert "ТОДО" not in html and "ВЕРИФЙ" not in html  # nor their Cyrillic form


def test_strip_keeps_template_elements() -> None:
    html = (
        '<p data-block-key="a1">[[TODO: content — copywriter]] [[VERIFY: doctor]]</p>'
        "<p><i>Matn shifokor tekshiruvini kutmoqda. [[VERIFY: doctor]]</i></p>"
        '<p aria-live="polite"></p><i class="icon"></i>'
        "<p>Sayt tashxis qoʻymaydi. [[TODO: content — copywriter]]</p>"
    )
    assert strip_placeholders(html) == (
        '<p aria-live="polite"></p><i class="icon"></i><p>Sayt tashxis qoʻymaydi.</p>'
    )


def test_about_page_lists_the_resolutions(seeded, client: Client) -> None:
    html = _main(client.get("/uz/haqimizda/").content.decode())
    for url in (
        "https://www.lex.uz/uz/docs/8287513",
        "https://lex.uz/docs/7232845",
        "https://lex.uz/docs/7533952",
    ):
        assert f'href="{url}"' in html
    assert "24.06.2026 yildagi PQ-238-son" in html
    assert "Normativ-huquqiy hujjatlar" in html


def _old_site_state() -> None:
    """What a site seeded before 2026-10-15 looks like."""
    news = Page.objects.get(url_path__endswith="/yangiliklar/", locale__language_code="uz").specific
    news.title = "Yangiliklar"
    news.save_revision().publish()
    about = Page.objects.get(url_path__endswith="/haqimizda/", locale__language_code="uz").specific
    about.body = [
        {"type": "rich_text", "value": "<p>Matn.</p><p>[[TODO: content — copywriter]]</p>"}
    ]
    about.save_revision().publish()
    screening = Page.objects.get(
        url_path__endswith="/ayollar/skrining/kokrak-bezi-saratoni/", locale__language_code="uz"
    ).specific
    blocks = list(screening.body.raw_data)
    for block in blocks:
        if block["type"] == "text_card" and block["value"]["title"].startswith("Davlat dasturi"):
            block["value"]["text"] += "<p>[[VERIFY: doctor]]</p>"
    screening.body = blocks
    screening.save_revision().publish()
    settings_obj = SiteSettings.for_site(Site.objects.get(is_default_site=True))
    columns = list(settings_obj.footer_columns_uz.raw_data)
    for link in columns[0]["value"]["links"]:
        if link["label"] == "Foydali maʼlumotlar":
            link["label"] = "Yangiliklar"
    settings_obj.footer_columns_uz = json.dumps(columns)
    settings_obj.telegram_url = ""
    settings_obj.instagram_url = "https://instagram.com/editor-choice"
    settings_obj.save()


def test_one_off_command_updates_an_older_site(seeded, client: Client) -> None:
    _old_site_state()
    call_command("client_update_20261015")
    news = Page.objects.get(url_path__endswith="/yangiliklar/", locale__language_code="uz").specific
    assert news.title == "Foydali maʼlumotlar"
    about = Page.objects.get(url_path__endswith="/haqimizda/", locale__language_code="uz").specific
    body = json.dumps(list(about.body.raw_data), ensure_ascii=False)
    assert "[[TODO" not in body and body.count("lex.uz") == 3
    screening = Page.objects.get(
        url_path__endswith="/ayollar/skrining/kokrak-bezi-saratoni/", locale__language_code="uz"
    ).specific
    for block in screening.body.raw_data:
        if block["type"] == "text_card" and block["value"]["title"].startswith("Davlat dasturi"):
            assert "[[VERIFY" not in block["value"]["text"]
    settings_obj = SiteSettings.for_site(Site.objects.get(is_default_site=True))
    labels = [
        link["label"] for link in settings_obj.footer_columns_uz.raw_data[0]["value"]["links"]
    ]
    assert "Foydali maʼlumotlar" in labels and "Yangiliklar" not in labels
    assert settings_obj.telegram_url == "https://t.me/erta_aniqla"
    assert settings_obj.facebook_url == "https://www.facebook.com/erta.aniqla"
    assert settings_obj.instagram_url == "https://instagram.com/editor-choice"  # editor's kept
    post = PostPage.objects.get(slug="kokrak-bezi-saratonida-genetik-tekshiruvlar")
    assert post.live and post.topic == "breast" and str(post.date) == "2026-10-15"
    assert post.image is not None and post.image.width == 1600
    html = client.get(post.url).content.decode()
    assert "Koʻkrak bezi saratonida genetik tekshiruvlar" in html
    assert "<h2>Kimlarga genetik test tavsiya etiladi</h2>" in html
    lead, body = html.split('class="post__body"', 1)
    assert "saraton — bu hukm emas" in lead.split("<main", 1)[1]
    assert "saraton — bu hukm emas" not in body  # the lead is not repeated in the body
    # a second run changes nothing and never duplicates the news item
    call_command("client_update_20261015")
    assert PostPage.objects.filter(slug=post.slug).count() == 1
    about.refresh_from_db()
    assert json.dumps(list(about.body.raw_data), ensure_ascii=False).count("lex.uz") == 3
