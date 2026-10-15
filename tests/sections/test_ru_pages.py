"""Russian versions of the women's pages, questions and the first news item (D-088): the Uzbek
design bodies translated segment by segment — same blocks, anchors and links, no Uzbek left."""

from __future__ import annotations

import json
import re

import pytest
from django.core.management import call_command
from django.test import Client
from wagtail.models import Page

from apps.core.seed import ru_translate, tree, women_faq, women_figma
from apps.faq.models import Question
from apps.posts.models import PostPage

BUILDERS = [
    women_figma.body_breast_awareness,
    women_figma.body_cervical_awareness,
    women_figma.body_breast_screening,
    women_figma.body_cervical_screening,
    women_figma.body_breast_treatment,
    women_figma.body_cervical_treatment,
    women_figma.body_support,
    women_figma.body_after,
    women_faq.body_breast_faq,
    women_faq.body_cervical_faq,
]
UZBEK_ONLY = re.compile(r"[ʻʼ]|\b(?:va|bilan|uchun|boʻlgan|haqida)\b")


class _Pages(tree.SeedContext):
    """Every key resolves (so link buttons and their labels are built)."""

    def page_id(self, key: str, lang: str) -> int:
        return 1 if lang == "uz" else 2


def _anchors(body: object) -> list[str]:
    return re.findall(r'"anchor": "([^"]*)"', json.dumps(body, ensure_ascii=False))


@pytest.mark.parametrize("builder", BUILDERS, ids=lambda b: b.__name__)
def test_every_uzbek_segment_has_russian(builder) -> None:
    ctx = _Pages()
    russian = ru_translate.russian_body(builder, ctx)  # raises Missing on an untranslated segment
    uzbek = builder("uz", ctx)
    assert [b["type"] for b in russian] == [b["type"] for b in uzbek]
    assert _anchors(russian) == _anchors(uzbek)  # footer and FAQ links keep working
    texts = ru_translate.segments(russian)
    leftovers = [t for t in texts if UZBEK_ONLY.search(t)]
    assert not leftovers, leftovers[:3]
    assert "2" in json.dumps(russian) and '"page": 1' not in json.dumps(russian)  # Russian pages


def test_dictionary_has_no_stale_entries() -> None:
    """Every entry is still used, so a reviewer only ever reads live text."""
    ctx = _Pages()
    used = {s for b in BUILDERS for s in ru_translate.segments(b("uz", ctx))}
    from apps.posts import client_news

    used |= {client_news.TITLE, client_news.SUMMARY}
    used |= set(ru_translate.segments(client_news.BODY_HTML))
    stale = set(ru_translate.dictionary()) - used
    assert not stale, sorted(stale)[:3]


@pytest.mark.django_db
def test_russian_women_page_is_translated(seeded, client: Client) -> None:
    html = client.get("/ru/zhenskiy/osvedomlennost/rak-molochnoy-zhelezy/").content.decode()
    main = html.split("<main", 1)[1].split("</main>", 1)[0]
    assert "Рак молочной железы" in main
    assert 'id="belgilari"' in main  # same anchors as the Uzbek page
    assert "перевод с узбекского" not in main and "ʻ" not in main


@pytest.mark.django_db
def test_live_site_command_fills_russian_pages_once(seeded, client: Client) -> None:
    page = Page.objects.get(
        url_path__endswith="/zhenskiy/osvedomlennost/rak-molochnoy-zhelezy/",
        locale__language_code="ru",
    ).specific
    page.body = [{"type": "rich_text", "value": f"<p>{women_figma.RU_TODO}</p>"}]  # old seed
    page.save_revision().publish()
    edited = Page.objects.get(
        url_path__endswith="/zhenskiy/skrining/rak-molochnoy-zhelezy/", locale__language_code="ru"
    ).specific
    edited.body = [{"type": "rich_text", "value": "<p>Текст редактора.</p>"}]  # translated by hand
    edited.save_revision().publish()
    call_command("client_update_20261015")  # the uz news item the Russian one translates

    call_command("apply_ru_translations")
    page.refresh_from_db()
    assert "перевод с узбекского" not in json.dumps(list(page.body.raw_data), ensure_ascii=False)
    edited.refresh_from_db()
    assert "Текст редактора." in json.dumps(list(edited.body.raw_data), ensure_ascii=False)
    ru_post = PostPage.objects.get(locale__language_code="ru")
    assert ru_post.title == "Генетические исследования при раке молочной железы"
    assert ru_post.live and ru_post.image_id is not None
    html = client.get(ru_post.url).content.decode()
    assert "<h2>" in html and "BRCA1" in html
    assert Question.objects.filter(language="ru").count() == 13
    faq = client.get("/ru/voprosy-otvety/").content.decode()
    assert "Что такое рак молочной железы?" in faq

    call_command("apply_ru_translations")  # nothing changes the second time
    assert PostPage.objects.filter(locale__language_code="ru").count() == 1
    assert Question.objects.filter(language="ru").count() == 13
