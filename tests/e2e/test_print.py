"""Print stylesheets (spec §5, A5) and the accessibility toolbar (spec §9, A8).

Regional clinics print the self-exam guide, the patient route and the question checklists:
under `@media print` the site chrome disappears, accordions are expanded and the page carries
the site name. The toolbar state (font scale, contrast, motion) must survive a reload.
"""

from __future__ import annotations

import os

import pytest
from playwright.sync_api import Browser

BASE = os.environ.get("E2E_BASE_URL", "http://localhost:8001")
pytestmark = pytest.mark.e2e

PRINT_PAGES = [
    "/uz/ayollar/ogohlik/kokrak-bezi-saratoni/",  # self-exam steps
    "/uz/ayollar/davolash/",  # 4-step patient route
    "/ru/detskiy/diagnostika-i-lechenie/diagnostika/",  # questions checklist
]


@pytest.fixture(scope="module")
def print_page(browser: Browser):
    context = browser.new_context(
        viewport={"width": 390, "height": 844}, extra_http_headers={"X-E2E": "1"}
    )
    page = context.new_page()
    yield page
    context.close()


def _display(page, selector: str) -> str:
    return page.evaluate(
        "(sel) => { const el = document.querySelector(sel);"
        " return el ? getComputedStyle(el).display : 'missing'; }",
        selector,
    )


@pytest.mark.parametrize("path", PRINT_PAGES)
def test_print_media_hides_chrome_and_expands_accordions(print_page, path: str) -> None:
    response = print_page.goto(BASE + path)
    assert response is not None and response.status == 200
    print_page.emulate_media(media="print")
    for selector in (".site-header", ".site-footer", ".share", ".a11y-toolbar", ".skip-link"):
        assert _display(print_page, selector) in ("none", "missing"), selector
    assert _display(print_page, "main") != "none"
    # accordion bodies are visible even when <details> is closed
    closed = print_page.evaluate(
        "() => [...document.querySelectorAll('details:not([open]) > :not(summary)')]"
        ".map((el) => getComputedStyle(el).display)"
    )
    assert all(d != "none" for d in closed)
    footer_note = print_page.evaluate(
        "() => getComputedStyle(document.querySelector('main'), '::after').content"
    )
    assert "ertaaniqla.uz" in footer_note
    print_page.emulate_media(media="screen")


def test_a11y_toolbar_persists_across_reload(browser: Browser) -> None:
    context = browser.new_context(
        viewport={"width": 390, "height": 844}, extra_http_headers={"X-E2E": "1"}
    )
    page = context.new_page()
    page.goto(BASE + "/uz/")
    page.click('[data-a11y="font"][data-value="150"]')
    page.click('[data-a11y="contrast"]')
    assert page.get_attribute("html", "data-font-scale") == "150"
    assert page.get_attribute("html", "data-contrast") == "high"
    page.reload()
    assert page.get_attribute("html", "data-font-scale") == "150"
    assert page.get_attribute("html", "data-contrast") == "high"
    assert page.get_attribute('[data-a11y="contrast"]', "aria-pressed") == "true"
    page.click('[data-a11y="contrast"]')
    assert page.get_attribute("html", "data-contrast") in (None, "")
    context.close()
