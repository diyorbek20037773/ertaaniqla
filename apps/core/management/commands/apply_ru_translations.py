"""Russian versions of the women's pages, the section questions and the first news item on a
site seeded before them (D-088). Run once after the deploy (a fresh seed already has them):

    python manage.py apply_ru_translations

* a Russian women's page whose body still holds the seeded translator placeholder gets the
  translated body (blocks, anchors and links identical to the Uzbek page); a page an editor has
  already translated has no placeholder and is left alone;
* the question page gets the client's entries in Russian (`apps.faq.design.seed_questions`);
* the first «Foydali maʼlumotlar» item gets its Russian version.
Re-running changes nothing.
"""

from __future__ import annotations

import json
from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

PLACEHOLDER = "[[TODO: перевод с узбекского"


class Command(BaseCommand):
    help = "Fill the Russian women's pages, questions and news item from the translation (D-088)."

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        from wagtail.models import Page

        from apps.core.cache import bump_page_cache
        from apps.core.navigation import invalidate_navigation
        from apps.core.seed import tree
        from apps.core.seed.builder import Seeder
        from apps.faq.design import seed_questions
        from apps.home.models import HomePage
        from apps.posts.client_news import SLUG, create_russian_news
        from apps.posts.models import PostPage

        seeder = Seeder()
        if not seeder.resolve_existing():
            self.stdout.write("apply_ru_translations: no site yet, nothing to do")
            return
        pages = 0
        for node in tree.iter_nodes():
            page_id = seeder.ctx.page_id(node.key, "ru")
            if page_id is None or node.body is None:
                continue
            page = Page.objects.get(pk=page_id).specific
            field = "body" if node.kind == "article" else "intro"
            current = getattr(page, field)
            if PLACEHOLDER not in json.dumps(list(current.raw_data), ensure_ascii=False):
                continue
            if seeder.apply_body(page, node, "ru", publish=True):
                pages += 1
        uz_home = HomePage.objects.filter(locale__language_code="uz").first()
        questions = seed_questions(uz_home) if uz_home is not None else 0
        news = 0
        uz_post = PostPage.objects.filter(slug=SLUG, locale__language_code="uz").first()
        if uz_post is not None and create_russian_news(uz_post) is not None:
            news = 1
        invalidate_navigation()
        bump_page_cache()
        self.stdout.write(f"apply_ru_translations: pages={pages} questions={questions} news={news}")
