"""Bundle-size budgets (spec §4.6): CSS ≤ 40 KB gz, JS ≤ 50 KB gz; HTML ≤ 60 KB gz on key
pages. Lighthouse itself runs in CI (`lighthouserc.json`); this is the always-on guard."""

from __future__ import annotations

import gzip
from pathlib import Path

import pytest
from django.test import Client

DIST = Path(__file__).resolve().parents[2] / "static" / "dist"
pytestmark = pytest.mark.django_db


def gz_size(path: Path) -> int:
    return len(gzip.compress(path.read_bytes(), compresslevel=6))


@pytest.mark.skipif(not (DIST / "main.css").exists(), reason="run `npm run build` first")
def test_css_budget() -> None:
    assert gz_size(DIST / "main.css") <= 40 * 1024


@pytest.mark.skipif(not (DIST / "main.js").exists(), reason="run `npm run build` first")
def test_js_budget() -> None:
    assert gz_size(DIST / "main.js") <= 50 * 1024


@pytest.mark.parametrize("url", ["/uz/", "/uz/ayollar/", "/ru/zhenskiy/osvedomlennost/simptomy/"])
def test_html_budget(seeded, client: Client, url: str) -> None:
    body = client.get(url).content
    assert len(gzip.compress(body, compresslevel=6)) <= 60 * 1024
