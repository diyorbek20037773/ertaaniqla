"""Blogger kit page (spec §10, A6, TZ «материалы для распространения»)."""

from __future__ import annotations

import json

import pytest
from django.test import Client

from apps.media_library.materials import MaterialsPage

pytestmark = pytest.mark.django_db


def _page(lang: str) -> MaterialsPage:
    return MaterialsPage.objects.get(locale__language_code=lang)


def test_seeded_in_both_languages_at_spec_urls(seeded, client: Client) -> None:
    assert _page("uz").url == "/uz/materiallar/"
    assert _page("ru").url == "/ru/materialy/"
    for lang in ("uz", "ru"):
        response = client.get(_page(lang).url)
        assert response.status_code == 200


def test_materials_render_caption_hashtags_and_audience_filter(seeded, client: Client) -> None:
    page = _page("uz")
    page.materials = json.dumps(
        [
            {
                "type": "material",
                "value": {
                    "title": "Skrining posteri",
                    "audience": "bloggers",
                    "section": "women",
                    "caption": "Erta aniqla — hayotni saqla. [[TODO: content — copywriter]]",
                    "hashtags": "#ertaaniqla #skrining",
                },
            },
            {
                "type": "material",
                "value": {
                    "title": "Klinika uchun varaqa",
                    "audience": "clinics",
                    "section": "both",
                    "caption": "",
                    "hashtags": "",
                },
            },
        ]
    )
    page.save_revision().publish()

    html = client.get(page.url).content.decode()
    assert "Skrining posteri" in html and "Klinika uchun varaqa" in html
    assert "#ertaaniqla #skrining" in html
    assert 'data-copy="Erta aniqla' in html  # copy-caption button
    assert 'data-section="women"' in html

    filtered = client.get(page.url + "?audience=clinics").content.decode()
    assert "Klinika uchun varaqa" in filtered and "Skrining posteri" not in filtered
    assert 'href="/uz/materiallar/?audience=clinics" aria-current="true"' in filtered

    assert "Skrining posteri" in page.get_body_text()
    assert page.reading_time >= 1


def test_empty_state(seeded, client: Client) -> None:
    page = _page("ru")
    page.materials = json.dumps([])
    page.save_revision().publish()
    assert "Здесь появятся материалы." in client.get(page.url).content.decode()
