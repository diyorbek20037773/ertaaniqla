"""Provider embeds without third-party scripts (spec §4.3 `embed`, §8 CSP).

Only the four providers named in the TZ are accepted. Each is rendered as a plain `<iframe>`
to the provider's own embed endpoint (already allowed in `frame-src`), so no oEmbed network
call happens at validation or render time and no provider JavaScript runs on our origin.
Instagram and TikTok are wrapped in a click-to-load facade (privacy + page weight).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

CLICK_TO_LOAD_PROVIDERS = frozenset({"instagram", "tiktok"})

_YOUTUBE_ID = re.compile(r"^[A-Za-z0-9_-]{6,20}$")


@dataclass(frozen=True)
class EmbedInfo:
    provider: str
    src: str
    vertical: bool = False

    @property
    def click_to_load(self) -> bool:
        return self.provider in CLICK_TO_LOAD_PROVIDERS


def parse_embed_url(url: str) -> EmbedInfo | None:
    """Return the iframe source for a supported provider URL, or None."""
    parsed = urlparse(url.strip())
    if parsed.scheme != "https":
        return None
    host = parsed.netloc.lower().removeprefix("www.").removeprefix("m.")
    path = parsed.path.rstrip("/")
    parts = [p for p in path.split("/") if p]

    if host in {"youtube.com", "youtube-nocookie.com"}:
        video_id = ""
        if path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [""])[0]
        elif parts and parts[0] in {"embed", "shorts", "live"} and len(parts) >= 2:
            video_id = parts[1]
        if _YOUTUBE_ID.match(video_id):
            return EmbedInfo(
                "youtube",
                f"https://www.youtube-nocookie.com/embed/{video_id}",
                vertical=parts[:1] == ["shorts"],
            )
        return None
    if host == "youtu.be" and len(parts) == 1 and _YOUTUBE_ID.match(parts[0]):
        return EmbedInfo("youtube", f"https://www.youtube-nocookie.com/embed/{parts[0]}")

    if host == "t.me":
        # https://t.me/channel/123  →  https://t.me/channel/123?embed=1
        if len(parts) == 2 and parts[1].isdigit() and re.match(r"^[A-Za-z0-9_]{3,}$", parts[0]):
            return EmbedInfo("telegram", f"https://t.me/{parts[0]}/{parts[1]}?embed=1")
        return None

    if host == "instagram.com":
        # https://www.instagram.com/p/<code>/ or /reel/<code>/
        if len(parts) >= 2 and parts[0] in {"p", "reel", "reels"}:
            code = parts[1]
            if re.match(r"^[A-Za-z0-9_-]{5,}$", code):
                return EmbedInfo(
                    "instagram",
                    f"https://www.instagram.com/{'reel' if parts[0] != 'p' else 'p'}/{code}/embed/",
                    vertical=parts[0] != "p",
                )
        return None

    if host == "tiktok.com":
        # https://www.tiktok.com/@user/video/1234567890
        if len(parts) == 3 and parts[1] == "video" and parts[2].isdigit():
            return EmbedInfo("tiktok", f"https://www.tiktok.com/embed/v2/{parts[2]}", vertical=True)
        return None

    return None
