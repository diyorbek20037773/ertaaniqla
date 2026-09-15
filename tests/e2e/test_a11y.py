"""axe-core accessibility audit (spec §9, M2 gate): 0 serious/critical violations on key pages.

Runs against a live server (E2E_BASE_URL). axe is injected as an init script (CDP), so the
page's nonce-based CSP does not block it.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e

BASE_URL = os.environ.get("E2E_BASE_URL", "http://localhost:8001")
AXE_PATH = Path(__file__).resolve().parents[2] / "node_modules" / "axe-core" / "axe.min.js"
REPORT_DIR = Path(__file__).parent / "a11y"

PAGES = [
    "/uz/",
    "/ru/zhenskiy/",
    "/uz/bolalar/",
    "/uz/ayollar/ogohlik/belgilar/",
    "/ru/zhenskiy/kuda-obratitsya/",
    "/uz/qidiruv/?q=skrining",
]


@pytest.fixture(scope="module")
def axe_page(browser):
    assert AXE_PATH.exists(), "run `npm ci` first (axe-core)"
    context = browser.new_context(
        viewport={"width": 390, "height": 844}, extra_http_headers={"X-E2E": "1"}
    )
    context.add_init_script(path=str(AXE_PATH))
    page = context.new_page()
    yield page
    context.close()


@pytest.mark.parametrize("path", PAGES)
def test_no_serious_violations(axe_page, path: str) -> None:
    response = axe_page.goto(BASE_URL + path, wait_until="networkidle")
    assert response is not None and response.status == 200
    result = axe_page.evaluate(
        "() => axe.run(document, {runOnly: {type: 'tag', "
        "values: ['wcag2a', 'wcag2aa', 'wcag21aa', 'best-practice']}})"
    )
    REPORT_DIR.mkdir(exist_ok=True)
    name = path.strip("/").replace("/", "_").replace("?", "_").replace("=", "_") or "home"
    (REPORT_DIR / f"{name}.json").write_text(
        json.dumps(result["violations"], indent=2, ensure_ascii=False), encoding="utf-8"
    )
    serious = [v for v in result["violations"] if v["impact"] in {"serious", "critical"}]
    summary = [(v["id"], v["impact"], len(v["nodes"])) for v in serious]
    assert not serious, summary
