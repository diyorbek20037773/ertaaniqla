"""YouTube channel → «Videoroliklar» (D-085). New videos of the portal's channel (Settings → Site
settings → YouTube) appear on the site by themselves.

* the public channel feed (`/feeds/videos.xml?channel_id=…`, no API key) lists the latest videos;
* a video that is not on the site yet becomes a `Video` (source YouTube, ready), its cover is
  downloaded once and kept as our own image — visitors' browsers never ask YouTube for it, the
  player still loads only after consent (spec §8);
* the topic is guessed from the title and description (ko'krak / bachadon / bola…), an editor can
  change it, and nothing an editor edited is overwritten (existing videos are left alone);
* schedule: Celery beat every 30 minutes; hosts without a worker (Railway demo) sync at start-up
  and at most every 30 minutes when the video list is rendered, in a background thread.
"""

from __future__ import annotations

import logging
import re
import threading
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from django.core.cache import cache

logger = logging.getLogger("ertaaniqla.youtube")

FEED_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={}"
THUMBNAILS = ("maxresdefault.jpg", "hqdefault.jpg")
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}
TIMEOUT = 10
THROTTLE_KEY = "youtube:sync:recent"
THROTTLE_SECONDS = 30 * 60
CHANNEL_ID_RE = re.compile(r"UC[0-9A-Za-z_-]{22}")
TOPIC_WORDS = (
    ("breast", re.compile(r"ko.?krak|кўкрак|кукрак|грудн|молочн|mammograf|маммограф|pushti", re.I)),
    ("cervical", re.compile(r"bachadon|бачадон|шейк|hpv|opv|впч|кольпоскоп", re.I)),
    ("children", re.compile(r"bolalar|болалар|детск|дети|bola\b|бола\b", re.I)),
)


@dataclass
class FeedVideo:
    video_id: str
    title: str
    description: str
    published: datetime | None


def _get(url: str) -> bytes:
    if not url.startswith("https://"):  # YouTube only, never file: or other schemes
        raise ValueError(url)
    headers = {"User-Agent": "Mozilla/5.0 (ertaaniqla.uz)"}
    request = urllib.request.Request(url, headers=headers)  # noqa: S310 - https checked above
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:  # noqa: S310
        return bytes(response.read())


def channel_id(channel_url: str) -> str:
    """`…/channel/UC…` directly; `…/@handle` through the channel page (cached for a day)."""
    found = CHANNEL_ID_RE.search(channel_url or "")
    if found:
        return found.group(0)
    if not channel_url.startswith("https://www.youtube.com/@"):
        return ""
    key = f"youtube:channel-id:{channel_url}"
    cached = cache.get(key)
    if cached:
        return str(cached)
    html = _get(channel_url).decode("utf-8", "replace")
    match = re.search(r'"(?:externalId|channelId)":"(UC[0-9A-Za-z_-]{22})"', html)
    value = match.group(1) if match else ""
    if value:
        cache.set(key, value, 24 * 3600)
    return value


def parse_feed(xml: bytes) -> list[FeedVideo]:
    root = ET.fromstring(xml)  # noqa: S314 - YouTube over HTTPS; expat guards entity expansion
    videos = []
    for entry in root.findall("atom:entry", NS):
        video_id = entry.findtext("yt:videoId", default="", namespaces=NS)
        if not video_id:
            continue
        published = entry.findtext("atom:published", default="", namespaces=NS)
        videos.append(
            FeedVideo(
                video_id=video_id,
                title=(entry.findtext("atom:title", default="", namespaces=NS) or video_id).strip(),
                description=entry.findtext(
                    "media:group/media:description", default="", namespaces=NS
                ),
                published=datetime.fromisoformat(published) if published else None,
            )
        )
    return videos


def guess_topic(text: str) -> str:
    for topic, pattern in TOPIC_WORDS:
        if pattern.search(text or ""):
            return topic
    return ""


def _poster(video_id: str, title: str) -> Any:
    """Download the video cover once and keep it as a portal image (None when unreachable)."""
    from io import BytesIO

    from django.core.files.images import ImageFile

    from apps.media_library.models import PortalImage

    for name in THUMBNAILS:
        try:
            data = _get(f"https://i.ytimg.com/vi/{video_id}/{name}")
        except OSError:
            continue
        if len(data) < 2000:  # YouTube's grey placeholder for a missing size
            continue
        from PIL import Image as PILImage

        image = PortalImage(title=title[:255], description=title[:255], credit="YouTube")
        image.file.save(f"youtube-{video_id}.jpg", ImageFile(BytesIO(data)), save=False)
        # file.save() recomputes the size from the stored file; set it from the bytes we have
        image.width, image.height = PILImage.open(BytesIO(data)).size
        image.file_size = len(data)
        image.save()
        return image
    return None


def sync_channel(channel_url: str) -> list[str]:
    """Add the channel's videos that are not on the site yet. Returns their ids."""
    from apps.media_library.models import Video, VideoKind, VideoSource, VideoStatus

    cid = channel_id(channel_url)
    if not cid:
        return []
    added = []
    for item in parse_feed(_get(FEED_URL.format(cid))):
        if Video.objects.filter(external_url__contains=item.video_id).exists():
            continue
        Video.objects.create(
            title=item.title[:200],
            topic=guess_topic(f"{item.title} {item.description}"),
            kind=VideoKind.LONG,
            source=VideoSource.YOUTUBE,
            external_url=f"https://www.youtube.com/watch?v={item.video_id}",
            poster=_poster(item.video_id, item.title),
            status=VideoStatus.READY,
        )
        added.append(item.video_id)
    if added:
        from apps.core.cache import bump_page_cache

        bump_page_cache()
        logger.info("youtube: %d new video(s) %s", len(added), ",".join(added))
    return added


def channel_url_from_settings() -> str:
    from wagtail.models import Site

    from apps.core.models import SiteSettings

    site = Site.objects.filter(is_default_site=True).first()
    return SiteSettings.for_site(site).youtube_url if site else ""


def sync_from_settings() -> list[str]:
    try:
        return sync_channel(channel_url_from_settings())
    except Exception:  # network or YouTube format: never break a page or a start-up
        logger.exception("youtube: sync failed")
        return []


def sync_soon() -> None:
    """Hosts without a Celery worker: at most every 30 minutes, in a background thread."""
    if not cache.add(THROTTLE_KEY, 1, THROTTLE_SECONDS):
        return

    def run() -> None:
        from django.db import connection

        try:
            sync_from_settings()
        finally:
            connection.close()

    threading.Thread(target=run, name="youtube-sync", daemon=True).start()
