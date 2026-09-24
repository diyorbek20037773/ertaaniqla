"""Section / topic / article page behaviour, theming, query discipline."""

from __future__ import annotations

import pytest
from django.test import Client
from django.utils import translation
from wagtail.models import Locale

from apps.articles.models import ArticlePage
from apps.core.navigation import get_navigation, invalidate_navigation, nav_cache_key
from apps.sections.models import SectionIndexPage, TopicIndexPage

pytestmark = pytest.mark.django_db


def test_get_section_from_nested_article(seeded) -> None:
    article = ArticlePage.objects.get(
        url_path__endswith="/ayollar/ogohlik/kokrak-bezi-saratoni/", locale__language_code="uz"
    )
    section = article.get_section()
    assert isinstance(section, SectionIndexPage)
    assert section.section_key == "women"
    assert article.section_key == "women"
    assert section.get_section() is section


def test_home_has_no_section(seeded) -> None:
    from apps.home.models import HomePage

    home = HomePage.objects.get(locale__language_code="uz")
    assert home.get_section() is None
    assert home.section_key == ""


def test_body_data_section_attribute_and_theme(seeded, client: Client) -> None:
    html = client.get("/uz/bolalar/").content.decode()
    assert 'data-section="children"' in html
    html = client.get("/uz/ayollar/ogohlik/kokrak-bezi-saratoni/").content.decode()
    assert 'data-section="women"' in html
    html = client.get("/uz/").content.decode()
    assert 'data-section=""' in html


def test_section_colour_override_is_emitted_with_nonce(seeded, client: Client) -> None:
    section = SectionIndexPage.objects.get(section_key="women", locale__language_code="uz")
    section.colour_primary = "#123456"
    section.save_revision().publish()
    html = client.get("/uz/ayollar/ogohlik/kokrak-bezi-saratoni/").content.decode()
    assert "--brand:#123456;" in html
    assert '<style nonce="' in html


def test_section_index_query_count(seeded, django_assert_max_num_queries) -> None:
    client = Client()
    client.get("/uz/bolalar/")  # warm nav cache + settings
    with django_assert_max_num_queries(40):
        response = client.get("/uz/bolalar/")
    assert response.status_code == 200


def test_women_section_opens_its_first_topic(seeded, client: Client) -> None:
    # D-066: the women's section has no landing of its own — the first tab opens
    response = client.get("/uz/ayollar/")
    assert response.status_code == 302
    assert response["Location"] == "/uz/ayollar/ogohlik/"
    response = client.get(response["Location"])
    assert response.status_code == 302
    assert response["Location"] == "/uz/ayollar/ogohlik/kokrak-bezi-saratoni/"


def test_topic_index_lists_child_articles(seeded, client: Client) -> None:
    topic = TopicIndexPage.objects.get(slug="diagnostika-va-davolash", locale__language_code="uz")
    articles = topic.get_articles()
    assert [a.slug for a in articles] == ["diagnostika", "davolash"]
    html = client.get(topic.url).content.decode()
    assert "Diagnostika" in html
    assert "daqiqa" in html  # reading time meta on cards (uz)


def test_variant_group_lists_breast_then_cervical(seeded) -> None:
    topic = TopicIndexPage.objects.get(slug="skrining", locale__language_code="uz")
    assert [a.slug for a in topic.get_articles()] == [
        "kokrak-bezi-saratoni",
        "bachadon-boyni-saratoni",
    ]
    assert topic.get_variants() == list(topic.get_articles())


def test_reading_time_and_word_count(seeded) -> None:
    article = ArticlePage.objects.filter(
        slug="uhod-i-podderzhka", locale__language_code="ru"
    ).first()
    assert article is not None
    assert article.word_count > 50
    assert article.reading_time >= 1


def test_verified_badge(seeded, user, client: Client) -> None:
    article = ArticlePage.objects.get(
        url_path__endswith="/ayollar/ogohlik/kokrak-bezi-saratoni/", locale__language_code="uz"
    )
    assert article.verified_badge is None
    user.first_name, user.last_name, user.organisation = "Dilfuza", "A.", "RONC"
    user.save()
    article.medically_verified = True
    article.last_reviewed_by = user
    article.save_revision().publish()
    badge = article.verified_badge
    assert badge is not None
    assert badge["name"] == "Dilfuza A."
    assert badge["organisation"] == "RONC"
    with translation.override("uz"):
        html = client.get(article.url).content.decode()
    assert "verified-badge" in html
    assert "RONC" in html


def test_navigation_structure_and_cache(seeded) -> None:
    invalidate_navigation()
    nav = get_navigation("ru")
    assert [s.key for s in nav] == ["women", "children"]
    women = nav[0]
    assert len(women.items) == 5
    assert women.items[0].title == "Осведомленность"
    assert [c.title for c in women.items[0].children] == [
        "Рак молочной железы",
        "Рак шейки матки",
    ]
    from django.core.cache import cache

    assert cache.get(nav_cache_key("ru")) is not None


def test_navigation_cache_invalidated_on_publish(seeded) -> None:
    from django.core.cache import cache

    get_navigation("uz")
    assert cache.get(nav_cache_key("uz")) is not None
    topic = TopicIndexPage.objects.get(slug="skrining", locale__language_code="uz")
    topic.title = "Skrining (yangi)"
    topic.save_revision().publish()
    assert cache.get(nav_cache_key("uz")) is None
    assert any(i.title == "Skrining (yangi)" for i in get_navigation("uz")[0].items)


def test_navigation_unknown_language_is_empty(db) -> None:
    assert get_navigation("de") == []


def test_mega_menu_rendered_on_every_page(seeded, client: Client) -> None:
    html = client.get("/ru/detskiy/uhod-i-podderzhka/").content.decode()
    assert html.count('class="mega-menu"') == 2
    assert "Организация лечения" in html
    assert "Информация для семьи" in html
    assert 'class="site-nav__section is-active"' in html


def test_locale_ru_exists_after_migrations(db) -> None:
    assert Locale.objects.filter(language_code="ru").exists()


def test_figma_header_menu_links(seeded, client: Client) -> None:
    # D-064: Asosiy · Haqimizda · Bo'limlar · Shifokorlar · Savol-Javob, per language
    from apps.core.navigation import get_header_links

    invalidate_navigation()
    assert get_header_links("uz") == {
        "home": "/uz/",
        "about": "/uz/haqimizda/",
        "doctors": "/uz/shifokorlar/",
        "faq": "/uz/savol-javob/",
    }
    assert get_header_links("ru")["about"] == "/ru/o-portale/"
    html = client.get("/uz/bolalar/").content.decode()
    for label, url in [
        ("Asosiy", "/uz/"),
        ("Haqimizda", "/uz/haqimizda/"),
        ("Shifokorlar", "/uz/shifokorlar/"),
        ("Savol-Javob", "/uz/savol-javob/"),
    ]:
        assert f'href="{url}">{label}</a>' in html or f'href="{url}" aria-current' in html
    assert 'class="site-search"' in html and 'name="q"' in html
    assert "lang-menu__toggle" in html
    assert client.get("/uz/haqimizda/").status_code == 200
    assert client.get("/ru/vrachi/").status_code == 200


def test_header_menu_follows_site_settings(seeded) -> None:
    from wagtail.models import Site

    from apps.core.models import SiteSettings
    from apps.core.navigation import get_header_links

    assert "doctors" in get_header_links("uz")
    settings_obj = SiteSettings.for_site(Site.objects.get(is_default_site=True))
    settings_obj.doctors_page = None
    settings_obj.save()  # the signal drops the cached header links
    assert "doctors" not in get_header_links("uz")
