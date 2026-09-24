"""Mobile screenshots (390 px) of the key pages — M1 gate (spec §14.9).

Run against a live server:  E2E_BASE_URL=http://localhost:8001 make e2e
Screenshots land in tests/e2e/screenshots/<name>.png (committed for the designer hand-off).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e

BASE_URL = os.environ.get("E2E_BASE_URL", "http://localhost:8001")
SCREENSHOTS = Path(__file__).parent / "screenshots"
MOBILE = {"width": 390, "height": 844}
DESKTOP = {"width": 1280, "height": 800}

PAGES = [
    ("home-uz", "/uz/"),
    ("home-ru", "/ru/"),
    ("section-women-uz", "/uz/ayollar/"),
    ("section-children-uz", "/uz/bolalar/"),
    ("section-children-ru", "/ru/detskiy/"),
    ("article-patient-route-uz", "/uz/ayollar/davolash/"),
    ("article-symptoms-ru", "/ru/zhenskiy/osvedomlennost/simptomy/"),
    ("article-care-children-uz", "/uz/bolalar/parvarish/"),
    ("directory-uz", "/uz/ayollar/qayerga-murojaat/"),
    ("stories-ru", "/ru/istorii/"),
    ("tools-screening-uz", "/uz/vositalar/skrining/"),
    ("tools-selfcheck-children-ru", "/ru/instrumenty/priznaki-u-detey/"),
    ("faq-uz", "/uz/savol-javob/"),
    ("glossary-ru", "/ru/slovar/"),
    ("materials-uz", "/uz/materiallar/"),
    ("feedback-uz", "/uz/qayta-aloqa/"),
    ("search-uz", "/uz/qidiruv/?q=saraton"),
    ("home-oz", "/oz/"),  # Uzbek Cyrillic (D-049)
    ("article-symptoms-oz", "/oz/ayollar/ogohlik/belgilar/"),
]


@pytest.fixture(scope="module")
def mobile_page(browser):
    context = browser.new_context(
        viewport=MOBILE,
        device_scale_factor=1,
        locale="uz",
        extra_http_headers={"X-E2E": "1"},  # hides the debug toolbar on the dev server
    )
    page = context.new_page()
    yield page
    context.close()


@pytest.mark.parametrize(("name", "path"), PAGES)
def test_screenshot(mobile_page, name: str, path: str) -> None:
    SCREENSHOTS.mkdir(exist_ok=True)
    response = mobile_page.goto(BASE_URL + path, wait_until="networkidle")
    assert response is not None and response.status == 200, path
    assert mobile_page.locator("main h1").count() == 1
    mobile_page.screenshot(path=str(SCREENSHOTS / f"{name}.png"), full_page=True)


# M5b: the design pages at desktop width too (Figma frames are 1728 px wide).
DESKTOP_PAGES = [
    ("home-uz", "/uz/"),
    ("article-patient-route-uz", "/uz/ayollar/davolash/"),
    ("directory-uz", "/uz/ayollar/qayerga-murojaat/"),
    ("tools-screening-uz", "/uz/vositalar/skrining/"),
    ("faq-uz", "/uz/savol-javob/"),
    ("glossary-ru", "/ru/slovar/"),
]


@pytest.fixture(scope="module")
def desktop_page(browser):
    context = browser.new_context(
        viewport=DESKTOP, device_scale_factor=1, locale="uz", extra_http_headers={"X-E2E": "1"}
    )
    page = context.new_page()
    yield page
    context.close()


@pytest.mark.parametrize(("name", "path"), DESKTOP_PAGES)
def test_desktop_screenshot(desktop_page, name: str, path: str) -> None:
    SCREENSHOTS.mkdir(exist_ok=True)
    response = desktop_page.goto(BASE_URL + path, wait_until="networkidle")
    assert response is not None and response.status == 200, path
    desktop_page.screenshot(path=str(SCREENSHOTS / f"desktop-{name}.png"), full_page=True)


def test_mobile_menu_opens_without_hover(mobile_page) -> None:
    mobile_page.goto(BASE_URL + "/uz/", wait_until="networkidle")
    mobile_page.locator("summary.site-nav__toggle-button").click()
    assert mobile_page.locator(".mega-menu").count() == 2
    mobile_page.locator(".mega-menu__title").first.click()
    assert mobile_page.locator(".mega-menu__item").first.is_visible()
    mobile_page.screenshot(path=str(SCREENSHOTS / "menu-open-uz.png"), full_page=True)


def test_language_switch_keeps_page(mobile_page) -> None:
    mobile_page.goto(BASE_URL + "/uz/ayollar/skrining/qayerda/", wait_until="networkidle")
    mobile_page.locator("summary.site-nav__toggle-button").click()
    mobile_page.locator('a.lang-switch__link[hreflang="ru"]').click()
    mobile_page.wait_for_load_state("networkidle")
    assert mobile_page.url.endswith("/ru/zhenskiy/skrining/gde-proyti/")


def test_language_switch_to_uzbek_cyrillic_and_back(mobile_page) -> None:
    mobile_page.goto(BASE_URL + "/uz/ayollar/skrining/qayerda/", wait_until="networkidle")
    mobile_page.locator("summary.site-nav__toggle-button").click()
    mobile_page.locator('a.lang-switch__link[hreflang="uz-Cyrl"]').click()
    mobile_page.wait_for_load_state("networkidle")
    assert mobile_page.url.endswith("/oz/ayollar/skrining/qayerda/")
    assert mobile_page.locator("html").get_attribute("lang") == "uz-Cyrl"
    assert "Скрининг" in mobile_page.locator("main").inner_text()
    mobile_page.locator("summary.site-nav__toggle-button").click()
    mobile_page.locator('a.lang-switch__link[hreflang="uz"]').click()
    mobile_page.wait_for_load_state("networkidle")
    assert mobile_page.url.endswith("/uz/ayollar/skrining/qayerda/")
