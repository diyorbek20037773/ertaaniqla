"""Client changes of 2026-10-13 (docs/FAQ.docx, D-084): «Savol-javob» tab per disease inside the
women's section, «Umumiy maʼlumot» / «Biz haqimizda» titles, scrolling section banner."""

from __future__ import annotations

import re

import pytest
from django.core.management import call_command
from django.test import Client
from wagtail.models import Page

pytestmark = pytest.mark.django_db


def test_women_faq_tab_with_the_client_answers(seeded, client: Client) -> None:
    html = client.get("/uz/ayollar/savol-javob/kokrak-bezi-saratoni/").content.decode()
    assert "Koʻkrak bezi saratoni nima?" in html  # accordion item title
    assert "sut bezi toʻqimasi hujayralarining nazoratsiz koʻpayishi" in html
    main = html.split("<main", 1)[1].split("</main>", 1)[0]
    assert 'id="savol-6"' in main and "[[TODO" not in main
    assert 'href="/uz/savol-javob/"' in html  # «Savol berish» → the question page
    cervical = client.get("/uz/ayollar/savol-javob/bachadon-boyni-saratoni/").content.decode()
    assert "Emlash orqali bachadon boʻyni saratonidan himoyalanish mumkinmi?" in cervical
    assert re.search(
        r'section-tabs__link is-active"\s+href="/uz/ayollar/savol-javob/bachadon', cervical
    )
    assert client.get("/ru/zhenskiy/voprosy-otvety/rak-molochnoy-zhelezy/").status_code == 200


def test_live_site_command_creates_missing_pages_and_keeps_editor_titles(seeded) -> None:
    faq = Page.objects.get(url_path__endswith="/ayollar/savol-javob/", locale__language_code="uz")
    for page in list(faq.get_translations(inclusive=True)):
        page.delete()  # a live site from before the change has no such tab
    # an editor renamed «Umumiy maʼlumot» to something else: the command keeps it
    awareness = Page.objects.get(
        url_path__endswith="/ayollar/ogohlik/", locale__language_code="uz"
    ).specific
    awareness.title = "Tahrirlangan nom"
    awareness.save_revision().publish()
    call_command("seed_client_changes")
    awareness.refresh_from_db()
    assert awareness.title == "Tahrirlangan nom"
    # the about page carries the new name
    about = Page.objects.get(url_path__endswith="/haqimizda/", locale__language_code="uz")
    assert about.title == "Biz haqimizda"
    recreated = Page.objects.get(
        url_path__endswith="/ayollar/savol-javob/", locale__language_code="uz"
    )
    assert recreated.get_children().count() == 2  # breast + cervical
    assert recreated.get_translation_or_none(
        Page.objects.get(url_path__endswith="/zhenskiy/").locale
    )


def test_scrolling_banner_has_a_pause_button(seeded, client: Client) -> None:
    html = client.get("/uz/ayollar/ogohlik/kokrak-bezi-saratoni/").content.decode()
    assert "data-marquee" in html and 'aria-pressed="false"' in html
    assert html.count('class="section-banner__tile"') == 4
    assert "Animatsiyani toʻxtatish" in html
