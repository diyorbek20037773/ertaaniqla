"""Shared pytest fixtures."""

from __future__ import annotations

from typing import Any

import pytest
from django.test import Client


@pytest.fixture
def client() -> Client:
    return Client()


@pytest.fixture(autouse=True)
def _clear_cache() -> Any:
    """Rate-limit counters, nav/glossary/waffle caches must not leak between tests."""
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def user(db, django_user_model):
    return django_user_model.objects.create_user(
        username="editor", email="editor@example.uz", password="correct-horse-battery-staple"
    )


@pytest.fixture
def admin_user(db, django_user_model):
    return django_user_model.objects.create_superuser(
        username="admin", email="admin@example.uz", password="correct-horse-battery-staple"
    )


@pytest.fixture(scope="session")
def seeded_tree(django_db_setup, django_db_blocker) -> dict[str, int]:
    """The full TZ tree seeded once per test session (idempotent, so `--reuse-db` is fine)."""
    from apps.core.seed.builder import Seeder

    with django_db_blocker.unblock():
        return Seeder().run()


@pytest.fixture
def seeded(seeded_tree, db) -> dict[str, int]:
    """Per-test access to the seeded tree inside the test transaction."""
    return seeded_tree


@pytest.fixture
def home(db) -> Any:
    """A minimal site: root → HomePage (uz) as the default site's root page."""
    from wagtail.models import Locale, Page, Site

    from apps.home.models import HomePage

    uz = Locale.objects.get(language_code="uz")
    existing = HomePage.objects.filter(locale=uz).first()
    if existing is not None:
        return existing
    root = Page.get_first_root_node()
    page = HomePage(title="Erta aniqla", slug="test-home", locale=uz)
    root.add_child(instance=page)
    site = Site.objects.filter(is_default_site=True).first()
    if site is None:
        Site.objects.create(hostname="localhost", port=80, root_page=page, is_default_site=True)
    else:
        site.root_page = page
        site.save(update_fields=["root_page"])
    return page


@pytest.fixture
def women_section(home) -> Any:
    from wagtail.models import Locale

    from apps.sections.models import SectionIndexPage

    uz = Locale.objects.get(language_code="uz")
    existing = SectionIndexPage.objects.filter(locale=uz, section_key="women").first()
    if existing is not None:
        return existing
    section = SectionIndexPage(
        title="Ayollar saratoni", slug="test-ayollar", section_key="women", locale=uz
    )
    home.add_child(instance=section)
    section.save_revision().publish()
    return section
