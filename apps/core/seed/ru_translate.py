"""Russian versions of the women's pages, the section questions and the first news item
(developer request 2026-10-15, D-088).

The Uzbek bodies are the client's text (Figma / Word). Their Russian pages are built from the
same builder, so blocks, accordion anchors, illustrations and links are identical; only the text
changes. Every visible text is cut into segments — a heading / title / label, or the inside of
one `<p>`, `<li>` or `<h2>`–`<h4>` of a rich text — and looked up in `ru_women.json`
(`{uz segment: ru segment}`). The file is plain data a translator can review; a test fails when
an Uzbek segment has no Russian entry, so a later Uzbek edit cannot leave the Russian page stale.

The Russian text is a translation of medical content: like the Uzbek pages, they stay
unverified (no «checked by a doctor» badge) until the medical review workflow approves them.
"""

from __future__ import annotations

import json
import re
from functools import cache
from pathlib import Path
from typing import Any

DICTIONARY = Path(__file__).resolve().parent / "ru_women.json"

# block-level pieces of a rich text; seeded HTML never nests them
SEGMENT_RE = re.compile(r"<(p|li|h2|h3|h4)((?:\s[^>]*)?)>(.*?)</\1>", re.S)
# StreamField keys that never hold visible text
TECHNICAL_KEYS = {
    "anchor",
    "framed",
    "icon",
    "id",
    "illustration",
    "image",
    "kind",
    "layout",
    "places",  # ScreeningRouteBlock step: a code, not text (D-105)
    "note_icon",
    "number",
    "page",
    "pictogram",
    "style",
    "topic",
    "type",
    "url",
    "variant",
    "width",
}
HAS_LETTERS = re.compile(r"[A-Za-zʻʼ]")


class Missing(KeyError):
    """An Uzbek segment without a Russian entry."""


@cache
def dictionary() -> dict[str, str]:
    if not DICTIONARY.exists():
        return {}
    data: dict[str, str] = json.loads(DICTIONARY.read_text(encoding="utf-8"))
    return data


def segments(value: Any, key: str = "") -> list[str]:
    """Every translatable Uzbek segment of a StreamField JSON value, in order."""
    found: list[str] = []
    if isinstance(value, dict):
        for name, item in value.items():
            if name not in TECHNICAL_KEYS:
                found += segments(item, name)
    elif isinstance(value, list):
        for item in value:
            found += segments(item, key)
    elif isinstance(value, str) and HAS_LETTERS.search(value):
        parts = SEGMENT_RE.findall(value)
        if parts:
            found += [inner.strip() for _tag, _attrs, inner in parts if HAS_LETTERS.search(inner)]
        else:
            found.append(value.strip())
    return found


def _ru(text: str, lookup: dict[str, str], missing: list[str]) -> str:
    stripped = text.strip()
    if not HAS_LETTERS.search(stripped):
        return text
    if stripped not in lookup:
        missing.append(stripped)
        return text
    return text.replace(stripped, lookup[stripped])


def translate(value: Any, lookup: dict[str, str], missing: list[str], key: str = "") -> Any:
    """`value` with every Uzbek segment replaced by its Russian entry (misses are collected)."""
    if isinstance(value, dict):
        return {
            name: item if name in TECHNICAL_KEYS else translate(item, lookup, missing, name)
            for name, item in value.items()
        }
    if isinstance(value, list):
        return [translate(item, lookup, missing, key) for item in value]
    if isinstance(value, str) and HAS_LETTERS.search(value):
        if SEGMENT_RE.search(value):
            return SEGMENT_RE.sub(
                lambda m: (
                    f"<{m.group(1)}{m.group(2)}>{_ru(m.group(3), lookup, missing)}</{m.group(1)}>"
                ),
                value,
            )
        return _ru(value, lookup, missing)
    return value


class RuPages:
    """`page_id(key, "uz")` answers with the Russian page, so links built for the Uzbek body
    point at the Russian pages."""

    def __init__(self, ctx: Any) -> None:
        self.ctx = ctx
        self.terms = {"uz": ctx.terms.get("ru", []), "ru": ctx.terms.get("ru", [])}

    def page_id(self, key: str, lang: str) -> int | None:
        found: int | None = self.ctx.page_id(key, "ru" if lang == "uz" else lang)
        return found


def russian_body(builder: Any, ctx: Any) -> list[dict[str, Any]]:
    """The Uzbek body of `builder`, translated, with links to the Russian pages."""
    missing: list[str] = []
    body: list[dict[str, Any]] = translate(builder("uz", RuPages(ctx)), dictionary(), missing)
    if missing:
        raise Missing(missing[:5])
    return body
