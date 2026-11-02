"""One-off (QA 2026-11-02): the footer site map's section links land on their section. Run once
after the deploy:

    python manage.py client_update_20261102

The QA crawl found six footer links (on every page) pointing at anchors no page had:
* screening — `#usullari`, `#kimlarga`; support — `#xonalar`, `#huquqlar`: the section headings
  get these anchors (uz and ru, both cancers' pages where the heading exists);
* «Davlat dasturi doirasida bepul skrining» pointed at the screening page, but that section is
  the support page's first heading: the link moves there and the heading gets `#bepul-skrining`;
* `#hamkorlar` (about page): the footer's partner logos carry that id now (template).

Telegram news items:
* the channel posted the same words (no video) more than once: the later copies are unpublished
  and redirect to the first (3 pairs on 2026-11-02); the bot skips such reposts from now on;
* links imported from the channel's public page kept t.me's double escape (`&amp;amp;`): fixed;
* a Russian post signed «Telegram: https://t.me/…» had made an Uzbek item titled with the link
  (language detection counted the link's letters): that item is unpublished, its address
  redirects to «Yangiliklar».

A page with an unpublished draft is skipped (an editor's work is never published by this
command); a second run changes nothing.
"""

from __future__ import annotations

import json
from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.seed.women_figma import SECTION_ANCHORS

SECTIONS = ("/skrining/", "/qollab-quvvatlash/", "/zhenskiy/skrining/", "/podderzhka/")


def anchor_headings(raw: list[dict[str, Any]]) -> bool:
    """Give the known section headings their anchor (in place); True when anything changed."""
    changed = False
    for block in raw:
        if block.get("type") != "heading":
            continue
        value = block["value"]
        text = value if isinstance(value, str) else value.get("text", "")
        anchor = SECTION_ANCHORS.get(" ".join(str(text).split()))
        current = "" if isinstance(value, str) else value.get("anchor", "")
        if anchor and not current:
            block["value"] = {"text": text, "anchor": anchor}
            changed = True
    return changed


def update_pages() -> tuple[list[str], list[str]]:
    from apps.articles.models import ArticlePage

    done, skipped = [], []
    for page in ArticlePage.objects.live().order_by("path"):
        if not any(part in page.url_path for part in SECTIONS):
            continue
        raw = json.loads(json.dumps(list(page.body.raw_data)))
        if not anchor_headings(raw):
            continue
        if page.has_unpublished_changes:
            skipped.append(page.url_path)
            continue
        page.body = raw
        page.save_revision().publish()
        done.append(page.url_path)
    return done, skipped


def move_free_screening_link() -> int:
    """«Davlat dasturi doirasida bepul skrining» → the support page of the same cancer."""
    from wagtail.models import Page, Site

    from apps.core.models import SiteSettings

    site = Site.objects.filter(is_default_site=True).first()
    if site is None:
        return 0
    settings = SiteSettings.for_site(site)
    moved = 0
    for field in ("footer_columns_uz", "footer_columns_ru"):
        raw = json.loads(json.dumps(list(getattr(settings, field).raw_data)))
        changed = False
        for column in raw:
            for link in column.get("value", {}).get("links", []):
                value = link.get("value", link)
                if value.get("anchor") != "bepul-skrining" or not value.get("page"):
                    continue
                page = Page.objects.filter(pk=value["page"]).first()
                if page is None or "skrining" not in page.url_path:
                    continue  # already moved
                support_path = page.url_path.replace("/zhenskiy/skrining/", "/zhenskiy/podderzhka/")
                support_path = support_path.replace("/skrining/", "/qollab-quvvatlash/")
                support = Page.objects.filter(url_path=support_path).first()
                if support is not None:
                    value["page"] = support.pk
                    changed = True
                    moved += 1
        if changed:
            setattr(settings, field, raw)
    if moved:
        settings.save()
    return moved


def _retire(page: Any, target: Any) -> None:
    """Unpublish a news item; its address redirects to `target` (kept item or the list)."""
    from wagtail.contrib.redirects.models import Redirect
    from wagtail.models import Site

    from apps.posts.models import TelegramPost

    site = Site.objects.filter(is_default_site=True).first()
    url = page.get_url()
    page.unpublish()
    if url:
        Redirect.objects.update_or_create(
            old_path=Redirect.normalise_path(url),
            site=site,
            defaults={"redirect_page": target, "is_permanent": True},
        )
    if target.specific_class is type(page.specific):
        TelegramPost.objects.filter(page=page).update(page=target)
        TelegramPost.objects.filter(ru_page=page).update(ru_page=target)


def retire_repeats() -> list[str]:
    """Later copies of a repeated text-only post, and items titled with a link."""
    import re

    from apps.posts.models import PostPage, TelegramPost
    from apps.posts.telegram import _text_html

    ids = {i for pair in TelegramPost.objects.values_list("page_id", "ru_page_id") for i in pair}
    retired: list[str] = []
    first: dict[tuple[Any, ...], Any] = {}
    for page in PostPage.objects.live().filter(id__in=ids - {None}).order_by("date", "id"):
        if re.search(r"https?://", page.title):
            retired.append(f"{page.url_path} (title is a link)")
            _retire(page, page.get_parent())
            continue
        if any(block.block_type == "embed" for block in page.body):
            continue  # a video each: not a repeat
        key = (page.locale_id, page.get_parent().pk, page.title, page.summary, _text_html(page))
        if key in first:
            retired.append(f"{page.url_path} (repeats {first[key].url_path})")
            _retire(page, first[key])
        else:
            first[key] = page
    return retired


def fix_double_escaped_links() -> list[str]:
    """`&amp;amp;` in the news items' text (t.me escapes links twice) → `&amp;`."""
    from apps.posts.models import PostPage, TelegramPost

    ids = {i for pair in TelegramPost.objects.values_list("page_id", "ru_page_id") for i in pair}
    fixed: list[str] = []
    for page in PostPage.objects.live().filter(id__in=ids - {None}).order_by("id"):
        raw = json.dumps(list(page.body.raw_data), ensure_ascii=False)
        if "&amp;amp;" not in raw or page.has_unpublished_changes:
            continue
        page.body = json.loads(raw.replace("&amp;amp;", "&amp;"))
        page.save_revision().publish()
        fixed.append(page.url_path)
    return fixed


class Command(BaseCommand):
    help = "QA 2026-11-02: anchors for the footer site map's section links."

    def handle(self, *args: Any, **options: Any) -> None:
        with transaction.atomic():
            done, skipped = update_pages()
            moved = move_free_screening_link()
            retired = retire_repeats()
            links = fix_double_escaped_links()
        for path in done:
            self.stdout.write(f"anchored {path}")
        for path in skipped:
            self.stdout.write(f"skipped {path} (unpublished draft)")
        for path in links:
            self.stdout.write(f"links fixed {path}")
        for line in retired:
            self.stdout.write(f"unpublished {line}")
        self.stdout.write(
            f"client_update_20261102: pages {len(done)}, footer links moved {moved}, "
            f"news items unpublished {len(retired)}, link fixes {len(links)}"
        )
