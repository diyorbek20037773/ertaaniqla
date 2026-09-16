"""Interactive bits must work under the strict CSP (spec §8): Alpine is the CSP build, so
share-copy, the click-to-load embed facade and the self-check counter run without
`unsafe-eval`; nothing in the console may report a CSP violation."""

from __future__ import annotations

import os

import pytest
from playwright.sync_api import Browser, ConsoleMessage

BASE = os.environ.get("E2E_BASE_URL", "http://localhost:8001")
pytestmark = pytest.mark.e2e


def _page(browser: Browser):
    context = browser.new_context(
        viewport={"width": 390, "height": 844},
        extra_http_headers={"X-E2E": "1"},
        permissions=["clipboard-read", "clipboard-write"],
    )
    page = context.new_page()
    errors: list[str] = []

    def on_console(message: ConsoleMessage) -> None:
        if message.type == "error":
            errors.append(message.text)

    page.on("console", on_console)
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    return context, page, errors


def test_share_copy_and_no_csp_errors(browser: Browser) -> None:
    context, page, errors = _page(browser)
    page.goto(f"{BASE}/uz/ayollar/ogohlik/belgilar/")
    page.click(".share__link--copy")
    page.wait_for_selector(".share__copied", state="visible")
    assert page.get_attribute(".share__link--copy", "aria-pressed") == "true"
    assert page.evaluate("navigator.clipboard.readText()").startswith("http")
    assert not [e for e in errors if "Content Security Policy" in e or "EvalError" in e], errors
    context.close()


def test_self_check_counter(browser: Browser) -> None:
    context, page, errors = _page(browser)
    page.goto(f"{BASE}/uz/vositalar/oz-tekshiruv/")
    boxes = page.locator("input[type=checkbox]")
    boxes.nth(0).check()
    boxes.nth(1).check()
    page.wait_for_function(
        "document.querySelector('.tool-form__count').textContent.trim() === '2 ✓'"
    )
    assert not [e for e in errors if "Content Security Policy" in e or "EvalError" in e], errors
    context.close()


def test_favicon_and_robots(browser: Browser) -> None:
    context, page, _errors = _page(browser)
    assert page.request.get(f"{BASE}/favicon.ico").status == 200
    assert "Sitemap:" in page.request.get(f"{BASE}/robots.txt").text()
    context.close()
