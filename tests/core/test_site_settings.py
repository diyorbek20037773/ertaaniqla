"""Site settings rendered in header/footer/banner (spec §4.3 'Site settings')."""

from __future__ import annotations

import pytest
from django.test import Client
from wagtail.models import Site

from apps.core.models import SiteSettings

pytestmark = pytest.mark.django_db


@pytest.fixture
def site_settings(seeded) -> SiteSettings:
    site = Site.objects.get(is_default_site=True)
    settings_obj, _ = SiteSettings.objects.get_or_create(site=site)
    settings_obj.hotline_phone = "+998712001122"
    settings_obj.telegram_url = "https://t.me/ertaaniqla"
    settings_obj.footer_text_uz = "Oʻzbek footer"
    settings_obj.footer_text_ru = "Русский футер"
    settings_obj.emergency_banner_enabled = True
    settings_obj.emergency_banner_uz = "Skrining oyi!"
    settings_obj.emergency_banner_ru = "Месяц скрининга!"
    settings_obj.emergency_banner_link = "https://ertaaniqla.uz/uz/ayollar/skrining/"
    settings_obj.save()
    return settings_obj


def test_header_footer_use_settings(site_settings, client: Client) -> None:
    html = client.get("/uz/").content.decode()
    assert "+998 71 200-11-22" in html
    assert 'href="tel:+998712001122"' in html
    assert "https://t.me/ertaaniqla" in html
    assert "Oʻzbek footer" in html
    assert "Sayt tashxis qoʻymaydi" in html  # disclaimer default
    ru = client.get("/ru/").content.decode()
    assert "Русский футер" in ru
    assert "Сайт не ставит диагноз" in ru


def test_emergency_banner(site_settings, client: Client) -> None:
    html = client.get("/uz/ayollar/").content.decode()
    assert "banner--emergency" in html
    assert "Skrining oyi!" in html
    ru = client.get("/ru/").content.decode()
    assert "Месяц скрининга!" in ru
    site_settings.emergency_banner_enabled = False
    site_settings.save()
    assert "banner--emergency" not in client.get("/uz/").content.decode()


def test_localized_helper(site_settings) -> None:
    assert site_settings.localized("footer_text", "ru") == "Русский футер"
    site_settings.footer_text_ru = ""
    assert site_settings.localized("footer_text", "ru") == "Oʻzbek footer"
