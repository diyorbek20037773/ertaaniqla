"""One-off: the client's requests of 2026-10-15 (docs/new_task_15.10.26, D-087) applied to a site
seeded before them. Run once after the deploy (a fresh seed already has all of it):

    python manage.py client_update_20261015

* the news list becomes «Foydali maʼlumotlar» / «Полезная информация» (title and footer link,
  only where the seeded wording is still in place);
* «Biz haqimizda» lists the three resolutions with their lex.uz links, its copywriter
  placeholder goes;
* the two screening blocks the client verified lose their `[[VERIFY]]` paragraphs;
* Telegram / Facebook / Instagram links are filled where empty;
* the first «Foydali maʼlumotlar» item is published (`apps.posts.client_news`).

Each step touches only seeded content and reports what it did; a second run changes nothing.
"""

from __future__ import annotations

import json
import re
from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

NEWS_OLD = {"uz": "Yangiliklar", "ru": "Новости"}
NEWS_NEW = {"uz": "Foydali maʼlumotlar", "ru": "Полезная информация"}
SOCIAL = {
    "telegram_url": "https://t.me/erta_aniqla",
    "facebook_url": "https://www.facebook.com/erta.aniqla",
    "instagram_url": "https://www.instagram.com/erta.aniqla/",
}
# the verified blocks: the TZ table «Davlat dasturi: kimga va qanchalik tez-tez» (also on the
# cervical page) and the card under «Kimlarga skrining tavsiya etiladi»
VERIFIED_TITLES = {"Davlat dasturi: kimga va qanchalik tez-tez", "Госпрограмма: кому и как часто"}
VERIFIED_MARK = "[[VERIFY: TZ — mammografiya 45–65"
SCREENING_KEYS = ("women.screening.breast", "women.screening.cervical")
# a paragraph holding nothing but placeholders
MARKER_PARAGRAPH = re.compile(r"<p[^>]*>(?:\s|\[\[(?:TODO|VERIFY)\b[^\]]*\]\])*</p>")


def _publish(page: Any) -> None:
    page.save_revision(log_action=True).publish()


def _without_markers(html: str) -> str:
    return MARKER_PARAGRAPH.sub("", html)


class Command(BaseCommand):
    help = "Apply the client's requests of 2026-10-15 to a live site (safe to re-run)."

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        from apps.core import visibility
        from apps.core.cache import bump_page_cache
        from apps.core.navigation import invalidate_navigation
        from apps.core.seed.builder import Seeder

        seeder = Seeder()
        if not seeder.resolve_existing():
            self.stdout.write("client_update_20261015: no site yet, nothing to do")
            return
        report = {
            "renamed": seeder.rename("news", NEWS_OLD, NEWS_NEW),
            "footer": self.footer_labels(),
            "social": self.social_links(),
            "about": self.about_laws(seeder),
            "screening": self.verified_blocks(seeder),
            "news": self.first_news(seeder),
        }
        invalidate_navigation()
        visibility.invalidate()
        bump_page_cache()
        self.stdout.write(
            "client_update_20261015: " + " ".join(f"{k}={v}" for k, v in report.items())
        )

    def footer_labels(self) -> int:
        from wagtail.models import Site

        from apps.core.models import SiteSettings

        site = Site.objects.filter(is_default_site=True).first()
        if site is None:
            return 0
        settings_obj = SiteSettings.for_site(site)
        changed = 0
        for lang in ("uz", "ru"):
            field = f"footer_columns_{lang}"
            columns = list(getattr(settings_obj, field).raw_data)
            for column in columns:
                for link in column["value"].get("links", []):
                    if link.get("label") == NEWS_OLD[lang]:
                        link["label"] = NEWS_NEW[lang]
                        changed += 1
            if changed:
                setattr(settings_obj, field, json.dumps(columns))
        if changed:
            settings_obj.save()
        return changed

    def social_links(self) -> int:
        from wagtail.models import Site

        from apps.core.models import SiteSettings

        site = Site.objects.filter(is_default_site=True).first()
        if site is None:
            return 0
        settings_obj = SiteSettings.for_site(site)
        filled = [field for field in SOCIAL if not getattr(settings_obj, field)]
        for field in filled:
            setattr(settings_obj, field, SOCIAL[field])
        if filled:
            settings_obj.save()
        return len(filled)

    def about_laws(self, seeder: Any) -> int:
        from wagtail.models import Page

        from apps.core.seed import tree

        changed = 0
        for lang in ("uz", "ru"):
            page_id = seeder.ctx.page_id("about", lang)
            if page_id is None:
                continue
            page = Page.objects.get(pk=page_id).specific
            blocks = list(page.body.raw_data)
            before = json.dumps(blocks, ensure_ascii=False)
            for block in blocks:
                if block["type"] == "rich_text":
                    block["value"] = _without_markers(block["value"])
            if "lex.uz" not in before:
                blocks.extend(tree.about_laws(lang))
            if json.dumps(blocks, ensure_ascii=False) != before:
                page.body = blocks
                _publish(page)
                changed += 1
        return changed

    def verified_blocks(self, seeder: Any) -> int:
        from wagtail.models import Page

        changed = 0
        for key in SCREENING_KEYS:
            for lang in ("uz", "ru"):
                page_id = seeder.ctx.page_id(key, lang)
                if page_id is None:
                    continue
                page = Page.objects.get(pk=page_id).specific
                blocks = list(page.body.raw_data)
                touched = False
                for block in blocks:
                    if block["type"] != "text_card":
                        continue
                    value = block["value"]
                    text = value.get("text", "")
                    if value.get("title") in VERIFIED_TITLES or VERIFIED_MARK in text:
                        cleaned = _without_markers(text)
                        if cleaned != text:
                            value["text"] = cleaned
                            touched = True
                if touched:
                    page.body = blocks
                    _publish(page)
                    changed += 1
        return changed

    def first_news(self, seeder: Any) -> int:
        from apps.posts.client_news import create_first_news
        from apps.posts.models import PostIndexPage

        page_id = seeder.ctx.page_id("news", "uz")
        index = PostIndexPage.objects.filter(pk=page_id).first() if page_id else None
        if index is None:
            return 0
        return 1 if create_first_news(index) is not None else 0
