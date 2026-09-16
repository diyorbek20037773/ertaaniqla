"""OpenGraph image generation (spec §10): 1200×630 PNG per page with the section colour,
title, subtitle and site name. Pillow + bundled DejaVu (Latin, Cyrillic, U+02BB)."""

from __future__ import annotations

import io
import textwrap
from pathlib import Path

from django.conf import settings
from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1200, 630
STORY_WIDTH, STORY_HEIGHT = 1080, 1920
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


def _render(
    width: int,
    height: int,
    title: str,
    subtitle: str,
    section_key: str,
    language: str,
    scale: float,
    max_title_lines: int,
) -> bytes:
    primary, soft = SECTION_COLOURS.get(section_key, SECTION_COLOURS[""])
    padding = int(PADDING * scale)
    band = int(BAND * scale)
    image = Image.new("RGB", (width, height), soft)
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, width, band], fill=primary)
    draw.rectangle([0, height - band, width, height], fill=primary)

    label_font = _font(True, int(30 * scale))
    label = SECTION_LABELS.get(section_key, SECTION_LABELS[""]).get(language, "")
    top = padding + (height // 5 if height > width else 0)
    draw.text((padding, top), label, font=label_font, fill=primary)

    title_size = int(64 * scale)
    min_size = int(36 * scale)
    while title_size > min_size:
        title_font = _font(True, title_size)
        lines = _wrap(title.strip(), title_font, width - 2 * padding)
        if len(lines) <= max_title_lines:
            break
        title_size -= 6
    else:
        title_font = _font(True, min_size)
        lines = _wrap(title.strip(), title_font, width - 2 * padding)[: max_title_lines + 1]
    y = top + int(70 * scale)
    for line in lines[: max_title_lines + 1]:
        draw.text((padding, y), line, font=title_font, fill="#111111")
        y += int(title_size * 1.25)

    if subtitle:
        sub_font = _font(False, int(30 * scale))
        for line in _wrap(
            textwrap.shorten(subtitle, 160, placeholder="…"), sub_font, width - 2 * padding
        )[:3]:
            draw.text((padding, y + int(12 * scale)), line, font=sub_font, fill="#5c5c5c")
            y += int(40 * scale)

    site_font = _font(False, int(26 * scale))
    draw.text(
        (padding, height - band - padding + int(20 * scale)),
        SITE_NAME.get(language, SITE_NAME["uz"]),
        font=site_font,
        fill=primary,
    )
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def render_og_image(
    title: str, subtitle: str = "", section_key: str = "", language: str = "uz"
) -> bytes:
    """1200×630 PNG for OpenGraph. Deterministic, no I/O besides font loading."""
    return _render(WIDTH, HEIGHT, title, subtitle, section_key, language, 1.0, 3)


def render_story_image(
    title: str, subtitle: str = "", section_key: str = "", language: str = "uz"
) -> bytes:
    """1080×1920 PNG for Instagram/TikTok stories (spec §10 share bar)."""
    return _render(STORY_WIDTH, STORY_HEIGHT, title, subtitle, section_key, language, 1.5, 6)
