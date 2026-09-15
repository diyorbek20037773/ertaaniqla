"""Patient stories: consent enforcement (F10), private consent document, index + filter."""

from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.test import Client
from wagtail.models import Locale

from apps.media_library.models import PortalDocument
from apps.stories.models import PatientStoryPage, StoryIndexPage

pytestmark = pytest.mark.django_db


@pytest.fixture
def index(seeded) -> StoryIndexPage:
    return StoryIndexPage.objects.get(locale__language_code="uz")


def make_story(index: StoryIndexPage, **kwargs) -> PatientStoryPage:
    defaults = {
        "title": "Hikoya",
        "slug": kwargs.pop("slug", "hikoya"),
        "person_display_name": "Nilufar (ism oʻzgartirilgan)",
        "section": "women",
        "summary": "[[TODO: content — copywriter]]",
        "locale": Locale.objects.get(language_code="uz"),
        "live": False,
    }
    defaults.update(kwargs)
    story = PatientStoryPage(**defaults)
    index.add_child(instance=story)
    return story


def test_draft_without_consent_is_allowed_but_publish_fails(index) -> None:
    story = make_story(index)
    assert not story.live
    with pytest.raises(ValidationError) as exc:
        story.save_revision().publish()
    assert "consent_obtained" in exc.value.message_dict
    story.refresh_from_db()
    assert not story.live


def test_children_story_needs_guardian_consent(index) -> None:
    story = make_story(index, slug="bola", section="children", consent_obtained=True)
    with pytest.raises(ValidationError) as exc:
        story.save_revision().publish()
    assert "consent_guardian" in exc.value.message_dict
    story.consent_guardian = True
    story.save_revision().publish()
    story.refresh_from_db()
    assert story.live
    assert story.section_key == "children"


def test_consent_document_is_forced_private(index) -> None:
    doc = PortalDocument.objects.create(
        title="Consent", file=ContentFile(b"%PDF-1.4 c", name="c.pdf")
    )
    assert not doc.is_private
    story = make_story(index, slug="doc", consent_obtained=True, consent_document=doc)
    story.save_revision().publish()
    doc.refresh_from_db()
    assert doc.is_private


def test_index_lists_and_filters(index, client: Client) -> None:
    women = make_story(index, slug="w", title="Ayol hikoyasi", consent_obtained=True)
    women.save_revision().publish()
    child = make_story(
        index,
        slug="c",
        title="Bola hikoyasi",
        section="children",
        consent_obtained=True,
        consent_guardian=True,
    )
    child.save_revision().publish()
    html = client.get("/uz/hikoyalar/").content.decode()
    assert "Ayol hikoyasi" in html and "Bola hikoyasi" in html
    html = client.get("/uz/hikoyalar/?section=children").content.decode()
    assert "Bola hikoyasi" in html and "Ayol hikoyasi" not in html
    page = client.get(child.url)
    assert page.status_code == 200
    body = page.content.decode()
    assert 'data-section="children"' in body
    assert "Nilufar" in body


def test_seeded_index_in_both_languages(seeded, client: Client) -> None:
    assert client.get("/uz/hikoyalar/").status_code == 200
    assert client.get("/ru/istorii/").status_code == 200
