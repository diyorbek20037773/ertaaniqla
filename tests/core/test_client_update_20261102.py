"""QA of 2026-11-02: section headings with anchors (old plain-string headings still render), the
footer site map's section links landing on them, the meta description falling back to the
summary, unique <title>s for news items sharing a headline, and `client_update_20261102`
(anchors, the free-screening link, repeated Telegram posts, a link-titled item, t.me's double
escape)."""

from __future__ import annotations

import io
import json
from datetime import date
from typing import Any

import pytest
from django.core.management import call_command
from django.test import Client
from wagtail.contrib.redirects.models import Redirect
from wagtail.models import Page

from apps.articles.blocks import SectionHeadingBlock
from apps.posts.models import PostIndexPage, PostKind, PostPage, TelegramPost

pytestmark = pytest.mark.django_db


def test_heading_reads_old_strings_and_renders_its_anchor() -> None:
    block = SectionHeadingBlock()
    old = block.to_python("Skrining usullari")
    assert old["text"] == "Skrining usullari" and old["anchor"] == ""
    assert block.render(old).strip() == (
        '<h2 class="block block--heading section-heading__title">Skrining usullari</h2>'
    )
    new = block.to_python({"text": "Skrining usullari", "anchor": "usullari"})
    assert 'id="usullari"' in block.render(new)
    assert [v["text"] for v in block.bulk_to_python(["A", {"text": "B", "anchor": ""}])] == [
        "A",
        "B",
    ]


def test_footer_section_links_land_on_their_section(seeded: Any, client: Client) -> None:
    html = client.get("/uz/").content.decode()
    footer = html.split('class="site-footer"', 1)[1]
    links = {
        "/uz/ayollar/skrining/kokrak-bezi-saratoni/#usullari": "usullari",
        "/uz/ayollar/skrining/kokrak-bezi-saratoni/#kimlarga": "kimlarga",
        "/uz/ayollar/qollab-quvvatlash/kokrak-bezi-saratoni/#bepul-skrining": "bepul-skrining",
        "/uz/ayollar/qollab-quvvatlash/kokrak-bezi-saratoni/#xonalar": "xonalar",
        "/uz/ayollar/qollab-quvvatlash/kokrak-bezi-saratoni/#huquqlar": "huquqlar",
    }
    for href, anchor in links.items():
        assert f'href="{href}"' in footer, href
        assert f'id="{anchor}"' in client.get(href.split("#")[0]).content.decode(), href
    assert 'href="/uz/haqimizda/#hamkorlar"' in footer and 'id="hamkorlar"' in html
    ru = client.get("/ru/zhenskiy/skrining/rak-molochnoy-zhelezy/").content.decode()
    assert 'id="usullari"' in ru and 'id="kimlarga"' in ru


def _news_list() -> PostIndexPage:
    return PostIndexPage.objects.get(
        locale__language_code="uz", kind=PostKind.NEWS, telegram_feed=True
    )


def _item(parent: Page, title: str, day: int, summary: str = "", **fields: Any) -> PostPage:
    page = PostPage(title=title, summary=summary, date=date(2025, 10, day), **fields)
    parent.add_child(instance=page)
    page.save_revision().publish()
    return page


def test_meta_description_falls_back_to_the_summary(seeded: Any, client: Client) -> None:
    long = "Skrining haqida muhim maʼlumot. " * 10
    page = _item(_news_list(), "Meta sinov", 1, summary=long)
    html = client.get(page.url).content.decode()
    meta = html.split('<meta name="description" content="', 1)[1].split('"', 1)[0]
    assert meta.startswith("Skrining haqida muhim") and meta.endswith("…") and len(meta) <= 160
    video = _item(_news_list(), "Sizlarga hali hech kim aytmagan faktni aytaman", 2)  # no summary
    assert (
        '<meta name="description" content="Sizlarga hali hech kim aytmagan faktni aytaman">'
        in client.get(video.url).content.decode()
    )
    page.search_description = "Muharrir tavsifi"
    page.save_revision().publish()
    assert (
        '<meta name="description" content="Muharrir tavsifi">'
        in client.get(page.url).content.decode()
    )


def test_items_sharing_a_headline_get_unique_titles(seeded: Any) -> None:
    parent = _news_list()
    first = _item(parent, "Bir xil sarlavha", 16)
    second = _item(parent, "Bir xil sarlavha", 16)
    third = _item(parent, "Bir xil sarlavha", 25)
    alone = _item(parent, "Yagona sarlavha", 25)
    titles = {p.html_title for p in (first, second, third)}
    assert titles == {
        "Bir xil sarlavha — 16.10.2025 (1)",
        "Bir xil sarlavha — 16.10.2025 (2)",
        "Bir xil sarlavha — 25.10.2025",
    }
    assert alone.html_title == "Yagona sarlavha"


def test_one_off_update_fixes_anchors_footer_and_repeats(seeded: Any, client: Client) -> None:
    from wagtail.models import Site

    from apps.core.models import SiteSettings

    # the live site before the update: plain headings, the free-screening link on the screening page
    screening = Page.objects.get(
        url_path__endswith="/ayollar/skrining/kokrak-bezi-saratoni/"
    ).specific
    support = Page.objects.get(
        url_path__endswith="/ayollar/qollab-quvvatlash/kokrak-bezi-saratoni/"
    )
    raw = json.loads(json.dumps(list(screening.body.raw_data)))
    for block in raw:
        if block["type"] == "heading" and isinstance(block["value"], dict):
            block["value"] = block["value"]["text"]
    screening.body = raw
    screening.save_revision().publish()
    site_settings = SiteSettings.for_site(Site.objects.get(is_default_site=True))
    columns = json.loads(json.dumps(list(site_settings.footer_columns_uz.raw_data)))
    for column in columns:
        for link in column["value"]["links"]:
            value = link.get("value", link)  # ListBlock items: {"type", "value", "id"} or bare
            if value.get("anchor") == "bepul-skrining":
                value["page"] = screening.pk
    site_settings.footer_columns_uz = columns
    site_settings.save()
    # Telegram items: a text-only post posted twice, a link-titled one, a double-escaped link
    parent = _news_list()
    body = [{"type": "rich_text", "value": '<p><a href="https://x.uz/?a=1&amp;amp;b=2">x</a></p>'}]
    original = _item(parent, "Salom, qizlar!", 6, summary="Profilaktika", body=body)
    repeat = _item(parent, "Salom, qizlar!", 9, summary="Profilaktika", body=body)
    link_titled = _item(parent, "Telegram: https://t.me/erta_aniqla", 10)
    for number, page in enumerate((original, repeat, link_titled), start=1):
        TelegramPost.objects.create(chat_id=-100, message_id=number, page=page)
    old_repeat_url = repeat.url

    out = io.StringIO()
    call_command("client_update_20261102", stdout=out)
    assert "footer links moved 1" in out.getvalue() and "news items unpublished 2" in out.getvalue()
    assert 'id="usullari"' in client.get(screening.url).content.decode()
    footer = client.get("/uz/").content.decode().split('class="site-footer"', 1)[1]
    assert f'href="{support.url}#bepul-skrining"' in footer
    repeat.refresh_from_db()
    link_titled.refresh_from_db()
    assert not repeat.live and not link_titled.live
    assert (
        Redirect.objects.get(old_path=Redirect.normalise_path(old_repeat_url)).redirect_page_id
        == original.pk
    )
    assert TelegramPost.objects.get(message_id=2).page_id == original.pk
    original.refresh_from_db()
    assert "&amp;amp;" not in json.dumps(list(original.body.raw_data))

    call_command("client_update_20261102", stdout=out)
    assert out.getvalue().rstrip().endswith("news items unpublished 0, link fixes 0")
