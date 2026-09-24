"""OpenGraph image generation (spec §10)."""

from __future__ import annotations

import io

import pytest
from django.test import Client
from PIL import Image

from apps.articles.models import ArticlePage
from apps.core.og import render_og_image
from apps.core.tasks import generate_og_image

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("section", ["women", "children", ""])
@pytest.mark.parametrize("language", ["uz", "ru"])
def test_render_og_image_png_1200x630(section: str, language: str) -> None:
    png = render_og_image(
        "Koʻkrak bezi saratoni — Рак молочной железы: очень длинный заголовок для переноса строк",
        "Qisqacha mazmun / Краткое описание",
        section,
        language,
    )
    image = Image.open(io.BytesIO(png))
    assert image.format == "PNG"
    assert image.size == (1200, 630)


def test_task_generates_and_stores_image(seeded, client: Client) -> None:
    article = ArticlePage.objects.get(
        url_path__endswith="/ayollar/ogohlik/kokrak-bezi-saratoni/", locale__language_code="uz"
    )
    name = generate_og_image(article.pk)
    assert name.startswith("og/uz-")
    article.refresh_from_db()
    assert article.og_image_generated_url.endswith(".png")
    html = client.get(article.url).content.decode()
    assert f'property="og:image" content="http://localhost{article.og_image_generated_url}"' in html
    assert 'property="og:image:width" content="1200"' in html


def test_task_skips_missing_or_unpublished(seeded) -> None:
    assert generate_og_image(10**9) == ""
    article = ArticlePage.objects.get(
        url_path__endswith="/zhenskiy/osvedomlennost/rak-molochnoy-zhelezy/",
        locale__language_code="ru",
    )
    article.unpublish()
    assert generate_og_image(article.pk) == ""


def test_publish_triggers_task(seeded, django_capture_on_commit_callbacks) -> None:
    article = ArticlePage.objects.get(
        url_path__endswith="/ayollar/ogohlik/bachadon-boyni-saratoni/", locale__language_code="uz"
    )
    article.og_image_generated = ""
    article.save(update_fields=["og_image_generated"], clean=False)
    with django_capture_on_commit_callbacks(execute=True):
        article.save_revision().publish()
    article.refresh_from_db()
    assert article.og_image_generated
