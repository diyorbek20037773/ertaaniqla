"""The CMS «Translate this page» action (wagtail-localize) is safe on our pages (D-094): it never
publishes a Russian copy that still holds the Uzbek text, and it does not crash on a block whose
optional image is empty (text cards without a picture)."""

from __future__ import annotations

import pytest
from django.conf import settings
from wagtail.models import Locale, Page

pytestmark = pytest.mark.django_db


def test_translation_never_goes_live_by_itself() -> None:
    assert settings.WAGTAILLOCALIZE_SYNC_LIVE_STATUS_ON_TRANSLATE is False


def test_segments_of_a_page_with_empty_images(seeded) -> None:
    """A women's page full of text cards without a picture: extracting its segments (the first
    step of «Translate this page») used to raise AttributeError ('NoneType'.get) → HTTP 500."""
    from wagtail_localize.models import TranslationSource

    page = Page.objects.get(
        url_path__endswith="/ayollar/ogohlik/kokrak-bezi-saratoni/", locale__language_code="uz"
    ).specific
    source, _created = TranslationSource.get_or_create_from_instance(page)
    assert source.stringsegment_set.exists()  # the Uzbek text was found


@pytest.mark.parametrize("sync_live", [False, True])
def test_translate_this_page_makes_a_draft(
    seeded, admin_user, settings, django_capture_on_commit_callbacks, sync_live: bool
) -> None:
    """A live Uzbek page translated to Russian through the CMS: the Russian copy is a draft for
    the translator, not a live page with Uzbek text on /ru/. wagtail-localize publishes the copy
    in an on-commit callback, so the callbacks run here; the package default (True) is the
    control that shows the check can fail."""
    from wagtail_localize.operations import TranslationCreator

    from apps.articles.models import ArticlePage

    settings.WAGTAILLOCALIZE_SYNC_LIVE_STATUS_ON_TRANSLATE = sync_live
    parent = Page.objects.get(url_path__endswith="/haqimizda/", locale__language_code="uz")
    page = ArticlePage(title="Yangi sahifa", slug="yangi-sahifa", summary="Qisqa mazmun")
    parent.add_child(instance=page)
    page.save_revision().publish()
    ru = Locale.objects.get(language_code="ru")
    with django_capture_on_commit_callbacks(execute=True):
        TranslationCreator(admin_user, [ru]).create_translations(page)
    translated = Page.objects.get(pk=page.get_translation(ru).pk)
    assert translated.live is sync_live
