"""OpenGraph image generation (spec §10): 1200×630 PNG per page with the section colour,
title, subtitle and site name. Pillow + bundled DejaVu (Latin, Cyrillic, U+02BB)."""

from __future__ import annotations

import io
import textwrap
from pathlib import Path

from django.conf import settings
from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1200, 630
PADDING = 72
BAND = 24

# working defaults = tokens.css; the designer's colours replace these in M5b
SECTION_COLOURS: dict[str, tuple[str, str]] = {
    "women": ("#b8336a", "#f6e4ec"),
    "children": ("#8a5a00", "#f7ecd6"),
    "": ("#2b2b2b", "#f7f7f7"),
}
SECTION_LABELS: dict[str, dict[str, str]] = {
    "women": {"uz": "Ayollar saratoni", "ru": "Женский рак"},
    "children": {"uz": "Bolalar saratoni", "ru": "Детский рак"},
    "": {"uz": "Erta aniqla", "ru": "Эрта аниқла"},
}
SITE_NAME = {"uz": "ertaaniqla.uz — Erta aniqla", "ru": "ertaaniqla.uz — Эрта аниқла"}


def _font(bold: bool, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_dir = Path(getattr(settings, "OG_IMAGE_FONT_DIR", "static/fonts"))
    path = font_dir / ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")
    try:
        return ImageFont.truetype(str(path), size)
    except OSError:  # pragma: no cover - fonts are bundled; fallback keeps the task alive
        return ImageFont.load_default(size=size)


def _wrap(
    text: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont, max_width: int
) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if font.getlength(candidate) <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def render_og_image(
    title: str, subtitle: str = "", section_key: str = "", language: str = "uz"
) -> bytes:
    """PNG bytes for the given page data. Deterministic, no I/O besides font loading."""
    primary, soft = SECTION_COLOURS.get(section_key, SECTION_COLOURS[""])
    image = Image.new("RGB", (WIDTH, HEIGHT), soft)
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, WIDTH, BAND], fill=primary)
    draw.rectangle([0, HEIGHT - BAND, WIDTH, HEIGHT], fill=primary)

    label_font = _font(True, 30)
    label = SECTION_LABELS.get(section_key, SECTION_LABELS[""]).get(language, "")
    draw.text((PADDING, PADDING), label, font=label_font, fill=primary)

    title_size = 64
    while title_size > 36:
        title_font = _font(True, title_size)
        lines = _wrap(title.strip(), title_font, WIDTH - 2 * PADDING)
        if len(lines) <= 3:
            break
        title_size -= 6
    else:
        title_font = _font(True, 36)
        lines = _wrap(title.strip(), title_font, WIDTH - 2 * PADDING)[:4]
    y = PADDING + 70
    for line in lines[:4]:
        draw.text((PADDING, y), line, font=title_font, fill="#111111")
        y += int(title_size * 1.25)

    if subtitle:
        sub_font = _font(False, 30)
        for line in _wrap(
            textwrap.shorten(subtitle, 160, placeholder="…"), sub_font, WIDTH - 2 * PADDING
        )[:2]:
            draw.text((PADDING, y + 12), line, font=sub_font, fill="#5c5c5c")
            y += 40

    site_font = _font(False, 26)
    draw.text(
        (PADDING, HEIGHT - BAND - PADDING + 20),
        SITE_NAME.get(language, SITE_NAME["uz"]),
        font=site_font,
        fill=primary,
    )
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()
