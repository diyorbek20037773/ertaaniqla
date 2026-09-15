"""Every StreamField block of spec §4.3: `clean()` rules and rendered structure."""

from __future__ import annotations

import json
from typing import Any

import pytest
from django.core.exceptions import ValidationError
from django.utils import translation
from wagtail.blocks import StreamValue
from wagtail.models import Locale

from apps.articles import blocks
from apps.articles.blocks import ArticleBodyBlock, stream_plain_text

pytestmark = pytest.mark.django_db


def render(block_type: str, value: dict[str, Any] | str) -> str:
    stream = StreamValue(ArticleBodyBlock(), [{"type": block_type, "value": value}], is_lazy=True)
    with translation.override("uz"):
        return str(stream)


# ---------------------------------------------------------------------------
# clean()
# ---------------------------------------------------------------------------
def test_link_block_rejects_page_and_url_together(home) -> None:
    with pytest.raises(ValidationError):
        blocks.LinkBlock().clean({"page": home, "url": "https://example.com"})


def test_link_href_resolves_page_then_url(home) -> None:
    assert blocks.link_href({"page": home, "url": ""}) == home.url
    assert blocks.link_href({"page": None, "url": "https://x.uz"}) == "https://x.uz"
    assert blocks.link_href(None) == ""


def test_cta_requires_a_link() -> None:
    block = blocks.CTABlock()
    with pytest.raises(ValidationError):
        block.clean(block.to_python({"button_label": "Go", "link": {"page": None, "url": ""}}))


def test_video_block_requires_video_or_url() -> None:
    block = blocks.VideoBlock()
    with pytest.raises(ValidationError):
        block.clean(block.to_python({"video": None, "external_url": "", "caption": ""}))


def test_video_block_rejects_unknown_provider() -> None:
    block = blocks.VideoBlock()
    with pytest.raises(ValidationError):
        block.clean(block.to_python({"video": None, "external_url": "https://vimeo.com/1"}))


def test_embed_block_rejects_unknown_provider() -> None:
    block = blocks.EmbedBlock()
    with pytest.raises(ValidationError):
        block.clean(block.to_python({"url": "https://vimeo.com/1", "caption": ""}))


def test_three_columns_requires_exactly_three() -> None:
    block = blocks.ThreeColumnsBlock()
    two = block.to_python({"columns": [{"title": "a", "items": "<ul><li>x</li></ul>"}] * 2})
    with pytest.raises(ValidationError):
        block.clean(two)


def test_two_columns_requires_exactly_two() -> None:
    block = blocks.TwoColumnsBlock()
    three = block.to_python({"columns": [{"title": "a", "items": "<p>x</p>"}] * 3})
    with pytest.raises(ValidationError):
        block.clean(three)


def test_stat_year_bounds() -> None:
    block = blocks.StatBlock()
    with pytest.raises(ValidationError):
        block.clean(block.to_python({"value": "1", "label": "x", "source": "", "year": 1800}))


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------
def test_rich_text_renders_prose() -> None:
    html = render("rich_text", "<p>Salom</p>")
    assert 'class="block block--rich-text prose"' in html
    assert "<p>Salom</p>" in html


@pytest.mark.parametrize("kind", ["info", "warning", "danger", "success", "reassurance"])
def test_callout_kinds(kind: str) -> None:
    html = render("callout", {"kind": kind, "title": "T", "text": "<p>x</p>"})
    assert f"callout--{kind}" in html
    assert 'role="note"' in html
    assert 'class="sr-only"' in html  # kind announced in text, not colour only


def test_three_columns_render_all_items() -> None:
    cols = [{"title": f"Col {i}", "items": f"<ul><li>item {i}</li></ul>"} for i in range(3)]
    html = render("three_columns", {"columns": cols})
    assert html.count('class="columns__col"') == 3
    for i in range(3):
        assert f"item {i}" in html


def test_two_columns_render() -> None:
    cols = [{"title": f"Col {i}", "items": "<p>x</p>"} for i in range(2)]
    html = render("two_columns", {"columns": cols})
    assert "columns--2" in html
    assert html.count('class="columns__title"') == 2


def test_steps_auto_number_and_deadline(home) -> None:
    value = {
        "title": "Route",
        "steps": [
            {
                "number": "",
                "title": "One",
                "text": "<p>a</p>",
                "deadline": "",
                "link": {"page": None, "url": ""},
            },
            {
                "number": "",
                "title": "Two",
                "text": "<p>b</p>",
                "deadline": "10 days",
                "link": {"page": home.pk, "url": ""},
            },
        ],
    }
    html = render("steps", value)
    assert ">01<" in html
    assert ">02<" in html
    assert "10 days" in html
    assert f'href="{home.url}"' in html


def test_cards_grid_render() -> None:
    value = {
        "title": "Types",
        "cards": [
            {
                "image": None,
                "icon": "dna",
                "title": f"Card {i}",
                "text": "<p>t</p>",
                "link": {"page": None, "url": "https://x.uz"},
            }
            for i in range(6)
        ],
    }
    html = render("cards_grid", value)
    assert html.count('<article class="card">') == 6
    assert 'data-icon="dna"' in html
    assert 'href="https://x.uz"' in html


@pytest.mark.parametrize("urgency", ["routine", "soon", "urgent"])
def test_symptom_list_urgency_has_text_label(urgency: str) -> None:
    value = {
        "title": "",
        "symptoms": [{"symptom": "S", "urgency": urgency, "explanation": "<p>e</p>"}],
    }
    html = render("symptom_list", value)
    assert f"symptom--{urgency}" in html
    assert 'class="symptom__urgency"' in html


def test_stat_render() -> None:
    html = render("stat", {"value": "1 / 8", "label": "L", "source": "MoH", "year": 2025})
    assert "1 / 8" in html
    assert "MoH, 2025" in html


def test_video_block_external_youtube_renders_iframe() -> None:
    value = {
        "video": None,
        "external_url": "https://youtu.be/dQw4w9WgXcQ",
        "caption": "c",
        "transcript": "<p>tr</p>",
    }
    html = render("video", value)
    assert "youtube-nocookie.com/embed/dQw4w9WgXcQ" in html
    assert "<figcaption" in html
    assert "video__transcript" in html


def test_video_block_tiktok_is_click_to_load() -> None:
    value = {
        "video": None,
        "external_url": "https://www.tiktok.com/@a/video/123456",
        "caption": "",
        "transcript": "",
    }
    html = render("video", value)
    assert "embed__facade" in html
    assert "x-data" in html
    assert "<noscript>" in html


def test_embed_block_instagram_facade_and_noscript_link() -> None:
    html = render("embed", {"url": "https://www.instagram.com/p/ABCDE12/", "caption": "cap"})
    assert "embed__facade" in html
    assert 'href="https://www.instagram.com/p/ABCDE12/"' in html
    assert "cap" in html


def test_embed_block_telegram_direct_iframe() -> None:
    html = render("embed", {"url": "https://t.me/ertaaniqla/7", "caption": ""})
    assert 'src="https://t.me/ertaaniqla/7?embed=1"' in html
    assert "embed__facade" not in html


def test_image_gallery_render(wagtail_image) -> None:
    value = {
        "title": "Infographics",
        "images": [
            {
                "image": {"image": wagtail_image.pk, "decorative": False, "alt_text": "Alt!"},
                "caption": "c1",
            }
        ],
        "downloadable": True,
    }
    html = render("image_gallery", value)
    assert 'alt="Alt!"' in html
    assert "gallery__download" in html
    assert "c1" in html


def test_document_download_render(wagtail_document) -> None:
    html = render(
        "document_download", {"document": wagtail_document.pk, "description": "PDF guide"}
    )
    assert wagtail_document.url in html
    assert "PDF guide" in html
    assert "download" in html


def test_faq_accordion_uses_details() -> None:
    value = {
        "title": "Ask",
        "items": [
            {"question": "Q1?", "answer": "<p>A1</p>"},
            {"question": "Q2?", "answer": "<p>A2</p>"},
        ],
    }
    html = render("faq_accordion", value)
    assert html.count("<details") == 2
    assert "<summary" in html
    assert "Q2?" in html


def test_glossary_terms_render(glossary_term) -> None:
    html = render("glossary_terms", {"title": "", "terms": [glossary_term.pk]})
    assert "<dl" in html
    assert glossary_term.term in html


def test_institution_list_filters(institution) -> None:
    html = render(
        "institution_list",
        {"title": "Where", "region": "", "kind": "", "free_only": True, "limit": 5},
    )
    assert institution.name_uz in html
    html = render(
        "institution_list",
        {"title": "", "region": "", "kind": "ngo", "free_only": False, "limit": 5},
    )
    assert institution.name_uz not in html
    assert "institution-list__empty" in html


def test_cta_render(home) -> None:
    html = render(
        "cta",
        {
            "text": "<p>Go</p>",
            "button_label": "Open",
            "link": {"page": home.pk, "url": ""},
            "style": "secondary",
        },
    )
    assert "button--secondary" in html
    assert f'href="{home.url}"' in html


def test_quote_render() -> None:
    html = render("quote", {"text": "Line 1\nLine 2", "author": "A", "role": "R"})
    assert "<blockquote" in html
    assert "Line 1<br>Line 2" in html
    assert "A, R" in html


def test_table_render() -> None:
    value = {
        "caption": "Screening",
        "columns": [{"type": "text", "heading": "Test"}, {"type": "text", "heading": "Who"}],
        "rows": [{"values": ["Mammography", "45–65"]}],
    }
    html = render("table", value)
    assert "<caption>Screening</caption>" in html
    assert '<th scope="col">Who</th>' in html
    assert "45–65" in html


def test_stream_plain_text_skips_ids_and_html() -> None:
    body = ArticleBodyBlock().to_python(
        json.loads(
            json.dumps(
                [
                    {"type": "rich_text", "value": "<p>Salom <b>dunyo</b></p>"},
                    {
                        "type": "cta",
                        "value": {
                            "text": "",
                            "button_label": "Open",
                            "link": {"page": None, "url": "https://x.uz"},
                            "style": "primary",
                        },
                    },
                ]
            )
        )
    )
    text = stream_plain_text(body)
    assert "Salom dunyo" in text
    assert "https://x.uz" not in text
    assert "<b>" not in text
    assert stream_plain_text(None) == ""


def test_region_choices_include_all_regions() -> None:
    choices = blocks.region_choices()
    assert choices[0][0] == ""
    assert len(choices) == 15  # "all" + 14 regions


def test_locale_fixture_exists() -> None:
    assert Locale.objects.filter(language_code="ru").exists()
