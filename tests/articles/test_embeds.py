"""Provider embed parsing (no network, spec §4.3 `embed`)."""

from __future__ import annotations

import pytest

from apps.articles.embeds import parse_embed_url


@pytest.mark.parametrize(
    ("url", "provider", "src", "vertical", "click"),
    [
        (
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "youtube",
            "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ",
            False,
            False,
        ),
        (
            "https://youtu.be/dQw4w9WgXcQ",
            "youtube",
            "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ",
            False,
            False,
        ),
        (
            "https://www.youtube.com/shorts/dQw4w9WgXcQ",
            "youtube",
            "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ",
            True,
            False,
        ),
        (
            "https://t.me/ertaaniqla/42",
            "telegram",
            "https://t.me/ertaaniqla/42?embed=1",
            False,
            False,
        ),
        (
            "https://www.instagram.com/p/CxYz_123ab/",
            "instagram",
            "https://www.instagram.com/p/CxYz_123ab/embed/",
            False,
            True,
        ),
        (
            "https://www.instagram.com/reel/CxYz_123ab/",
            "instagram",
            "https://www.instagram.com/reel/CxYz_123ab/embed/",
            True,
            True,
        ),
        (
            "https://www.tiktok.com/@ronc/video/7234567890123456789",
            "tiktok",
            "https://www.tiktok.com/embed/v2/7234567890123456789",
            True,
            True,
        ),
    ],
)
def test_supported_providers(
    url: str, provider: str, src: str, vertical: bool, click: bool
) -> None:
    info = parse_embed_url(url)
    assert info is not None
    assert info.provider == provider
    assert info.src == src
    assert info.vertical is vertical
    assert info.click_to_load is click


@pytest.mark.parametrize(
    "url",
    [
        "http://www.youtube.com/watch?v=dQw4w9WgXcQ",  # not https
        "https://www.youtube.com/watch?v=<script>",
        "https://vimeo.com/123456",
        "https://t.me/ertaaniqla",  # channel, not a post
        "https://www.instagram.com/ertaaniqla/",  # profile
        "https://www.tiktok.com/@ronc",
        "https://example.com/",
        "",
    ],
)
def test_unsupported_urls(url: str) -> None:
    assert parse_embed_url(url) is None
