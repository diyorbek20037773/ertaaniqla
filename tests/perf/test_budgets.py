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


@pytest.mark.parametrize(
    "url", ["/uz/", "/uz/ayollar/", "/ru/zhenskiy/osvedomlennost/rak-molochnoy-zhelezy/"]
)
def test_html_budget(seeded, client: Client, url: str) -> None:
    body = client.get(url).content
    assert len(gzip.compress(body, compresslevel=6)) <= 60 * 1024


def test_every_component_modifier_survives_the_purge() -> None:
    """Modifiers are often built from data in templates; Tailwind must not purge them."""
    import re

    css = DIST / "main.css"
    if not css.exists():
        pytest.skip("run `npm run build` first")
    source = (DIST.parent / "src" / "components.css").read_text(encoding="utf-8")
    built = css.read_text(encoding="utf-8")
    modifiers = set(re.findall(r"^\s*\.([a-z0-9_-]+--[a-z0-9_-]+)", source, flags=re.M))
    assert modifiers
    missing = sorted(m for m in modifiers if f".{m}" not in built)
    assert not missing, f"purged from static/dist/main.css: {missing}"
