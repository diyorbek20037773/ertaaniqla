"""YouTube channel → «Videoroliklar» (D-085). New videos of the portal's channel (Settings → Site
settings → YouTube) appear on the site by themselves.

* where the list comes from (no API key, www.youtube.com only):
  1. the public channel feed (`/feeds/videos.xml?channel_id=…`), tried 3 times with a short pause.
     On 2026-10-16 it answered 404 to about 3 requests in 4 and to every cache-busted one (the
     200s were CDN copies), so it cannot be the only source;
  2. the channel's own «Videos» page (`/channel/UC…/videos`, 200 to every request that day): the
     `ytInitialData` JSON in it lists the videos. It has no description, so the topic is guessed
     from the title only;
* a video that is not on the site yet becomes a `Video` (source YouTube, ready; a Short becomes a
  short vertical video), its cover is downloaded once and kept as our own image — visitors'
  browsers never ask YouTube for it, the player still loads only after consent (spec §8);
* the topic is guessed from the title, then the description (ko'krak / bachadon / bola…), an
  editor can change it, and nothing an editor edited is overwritten (existing videos are left
  alone);
* every request: https to www.youtube.com / i.ytimg.com only (redirects included), a timeout and
  a size cap; the XML goes through defusedxml, the page JSON through a bounded walk;
* schedule: Celery beat every 30 minutes; hosts without a worker (Railway demo) sync at start-up
  and from the video list, in a background thread: again 30 minutes after a run that reached
  YouTube, 5 minutes after one that did not.
"""

from __future__ import annotations

import http.client
import json
import logging
import re
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from typing import IO, Any

from defusedxml import ElementTree as SafeET
from django.core.cache import cache

logger = logging.getLogger("ertaaniqla.youtube")

FEED_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={}"
VIDEOS_PAGE_URL = "https://www.youtube.com/channel/{}/videos"
THUMBNAIL_URL = "https://i.ytimg.com/vi/{}/{}"
THUMBNAILS = ("maxresdefault.jpg", "hqdefault.jpg")
ALLOWED_HOSTS = frozenset({"www.youtube.com", "i.ytimg.com"})
USER_AGENT = "Mozilla/5.0 (ertaaniqla.uz)"
# YouTube's own «reject all» answer to its cookie banner, so a server in the EU gets the page and
# not consent.youtube.com. A fixed value: no visitor's data ever goes to YouTube.
CONSENT_COOKIE = "SOCS=CAI"
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}
TIMEOUT = 10
MAX_PAGE_BYTES = 4 * 1024 * 1024  # the «Videos» page is ≈ 0.9 MB, ytInitialData near its end
MAX_IMAGE_BYTES = 2 * 1024 * 1024
FEED_RETRY_DELAYS = (1.0, 3.0)  # 3 tries
PAGE_RETRY_DELAYS = (2.0,)  # 2 tries
RETRY_STATUSES = frozenset({404, 408, 429, 500, 502, 503, 504})
SYNC_BUDGET_SECONDS = 45  # the start-up sync runs before gunicorn (Railway health check: 120 s)
MAX_JSON_NODES = 500_000
MAX_PAGE_VIDEOS = 60
THROTTLE_KEY = "youtube:sync:recent"
THROTTLE_SECONDS = 30 * 60
FAILURE_THROTTLE_SECONDS = 5 * 60
LOCK_KEY = "youtube:sync:running"
LOCK_SECONDS = 10 * 60
MAX_COVER_REPAIRS = 10  # covers fetched again per run for videos whose cover file is missing
COVER_PENDING_KEY = "youtube:cover-pending:{}"  # the sync made the video without its cover
COVER_PENDING_SECONDS = 30 * 24 * 3600
NO_COVER_KEY = "youtube:no-cover:{}"  # YouTube had no cover for it: next try tomorrow
NO_COVER_SECONDS = 24 * 3600
CHANNEL_ID_SECONDS = 7 * 24 * 3600
CHANNEL_ID_RE = re.compile(r"UC[0-9A-Za-z_-]{22}")
VIDEO_ID_RE = re.compile(r"[0-9A-Za-z_-]{11}")
HANDLE_URL_RE = re.compile(r"^https://(?:www\.|m\.)?youtube\.com/(@[^/?#\s]{3,100})")
# the channel's own id on its page; a bare "channelId" can be another (featured) channel's
PAGE_CHANNEL_ID_RES = tuple(
    re.compile(before + r"(UC[0-9A-Za-z_-]{22})")
    for before in (
        r'"externalId":"',
        r'<link rel="canonical" href="https://www\.youtube\.com/channel/',
        r"feeds/videos\.xml\?channel_id=",
    )
)
INITIAL_DATA_RE = re.compile(r"(?:var ytInitialData|window\[\"ytInitialData\"\])\s*=\s*")
SHORT_RENDERERS = frozenset({"shortsLockupViewModel", "reelItemRenderer"})
PAGE_RENDERERS = SHORT_RENDERERS | {"lockupViewModel", "videoRenderer", "gridVideoRenderer"}
CONTROL_RE = re.compile(r"[\x00-\x1f\x7f-\x9f]")
TOPIC_WORDS = (
    ("breast", re.compile(r"ko.?krak|кўкрак|кукрак|грудн|молочн|mammograf|маммограф|pushti", re.I)),
    ("cervical", re.compile(r"bachadon|бачадон|шейк|hpv|opv|впч|кольпоскоп", re.I)),
    ("children", re.compile(r"bolalar|болалар|детск|дети|bola\b|бола\b", re.I)),
)

_sleep = time.sleep  # tests replace it


@dataclass
class FeedVideo:
    video_id: str
    title: str
    description: str
    published: datetime | None
    short: bool = False


class FetchError(OSError):
    """A YouTube request without a usable answer: an HTTP error, a refused redirect, too big."""

    def __init__(self, url: str, reason: str, status: int | None = None) -> None:
        super().__init__(f"{reason} ({url})")
        self.url = url
        self.status = status


class SyncError(Exception):
    """YouTube could not be read: the channel id, or both the feed and the channel page."""


def _check_url(url: str) -> None:
    """https to YouTube's own hosts only — never file:, http:, another host, a port or user@."""
    parts = urllib.parse.urlsplit(url)
    if (
        parts.scheme != "https"
        or parts.hostname not in ALLOWED_HOSTS
        or "@" in parts.netloc
        or parts.port is not None
    ):
        raise ValueError(url)


class _YouTubeRedirects(urllib.request.HTTPRedirectHandler):
    """Follows a redirect only to where `_get` itself may go (no SSRF through a 30x)."""

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: IO[bytes],
        code: int,
        msg: str,
        headers: http.client.HTTPMessage,
        newurl: str,
    ) -> urllib.request.Request | None:
        try:
            _check_url(newurl)
        except ValueError:
            fp.close()
            raise FetchError(newurl, f"redirect {code} refused") from None
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_OPENER = urllib.request.build_opener(_YouTubeRedirects)


def _get(url: str) -> bytes:
    """One GET: https to www.youtube.com / i.ytimg.com only (redirects too), `TIMEOUT` seconds, at
    most `MAX_PAGE_BYTES` (`MAX_IMAGE_BYTES` for a cover). Raises FetchError or another OSError."""
    _check_url(url)
    image = url.startswith("https://i.ytimg.com/")
    limit = MAX_IMAGE_BYTES if image else MAX_PAGE_BYTES
    headers = {"User-Agent": USER_AGENT}
    if not image:
        headers["Cookie"] = CONSENT_COOKIE
    request = urllib.request.Request(url, headers=headers)  # noqa: S310 - scheme and host checked
    try:
        with _OPENER.open(request, timeout=TIMEOUT) as response:
            data = bytes(response.read(limit + 1))
    except urllib.error.HTTPError as error:
        error.close()
        raise FetchError(url, f"HTTP {error.code}", error.code) from None
    if len(data) > limit:
        raise FetchError(url, f"more than {limit} bytes")
    return data


def _transient(error: BaseException) -> bool:
    """Worth another try: a dropped connection, a timeout, a 404/429/5xx — not a refused redirect,
    a 403 or an oversized answer."""
    if isinstance(error, FetchError):
        return error.status in RETRY_STATUSES
    return True


def _get_retrying(url: str, delays: tuple[float, ...], deadline: float) -> bytes:
    """`_get`, tried again after each pause in `delays` while the failure is transient. No try
    starts once the run's time budget (`deadline`, a `time.monotonic()` value) is spent, and a
    retry only when a whole try (`TIMEOUT`) still fits after its pause."""
    for attempt in range(len(delays) + 1):
        if time.monotonic() >= deadline:
            raise FetchError(url, "the run's time budget is spent")
        try:
            return _get(url)
        except (OSError, http.client.HTTPException) as error:
            if (
                attempt == len(delays)
                or not _transient(error)
                or time.monotonic() + delays[attempt] + TIMEOUT > deadline
            ):
                raise
            logger.info(
                "youtube: %s, try %d of %d in %.0f s",
                error,
                attempt + 2,
                len(delays) + 1,
                delays[attempt],
            )
            _sleep(delays[attempt])
    raise AssertionError("unreachable")


def channel_id_from_page(html: str) -> str:
    for pattern in PAGE_CHANNEL_ID_RES:
        match = pattern.search(html)
        if match:
            return match.group(1)
    return ""


def _deadline(deadline: float | None) -> float:
    """The run's time budget as a `time.monotonic()` value: the caller's, or a new one."""
    return time.monotonic() + SYNC_BUDGET_SECONDS if deadline is None else deadline


def channel_id(channel_url: str, deadline: float | None = None) -> str:
    """`…/channel/UC…` directly; `…/@handle` (www., m. or bare youtube.com, any tab, `?si=…`)
    through the channel page, cached for a week. "" for anything else."""
    url = (channel_url or "").strip()
    found = CHANNEL_ID_RE.search(url)
    if found:
        return found.group(0)
    handle = HANDLE_URL_RE.match(url)
    if handle is None:
        if url:
            logger.warning("youtube: not a channel URL in Site settings: %.200s", url)
        return ""
    page_url = "https://www.youtube.com/" + urllib.parse.quote(handle.group(1), safe="@._-%")
    key = f"youtube:channel-id:{page_url}"
    cached = cache.get(key)
    if cached:
        return str(cached)
    page = _get_retrying(page_url, PAGE_RETRY_DELAYS, _deadline(deadline))
    value = channel_id_from_page(page.decode("utf-8", "replace"))
    if value:
        cache.set(key, value, CHANNEL_ID_SECONDS)
    else:
        logger.warning("youtube: no channel id on %s", page_url)
    return value


def _clean(text: str | None) -> str:
    """One line without control characters (PostgreSQL refuses NUL)."""
    return " ".join(CONTROL_RE.sub(" ", text or "").split())


def _date(value: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat(value) if value else None
    except ValueError:
        return None


def parse_feed(xml: bytes) -> list[FeedVideo]:
    """Entries of the channel's Atom feed. An entry without a valid video id is skipped and a bad
    date left empty; a body that is not the feed (an HTML error page) raises ValueError."""
    try:
        root = SafeET.fromstring(xml, forbid_dtd=True)  # defusedxml's refusals are ValueErrors
    except SafeET.ParseError as error:
        raise ValueError(f"not a feed: {error}") from None
    if root.tag != "{http://www.w3.org/2005/Atom}feed":
        raise ValueError(f"not a feed: <{root.tag}>")
    videos = []
    for entry in root.findall("atom:entry", NS):
        video_id = (entry.findtext("yt:videoId", default="", namespaces=NS) or "").strip()
        if not VIDEO_ID_RE.fullmatch(video_id):
            continue
        link = entry.find("atom:link[@rel='alternate']", NS)
        videos.append(
            FeedVideo(
                video_id=video_id,
                title=_clean(entry.findtext("atom:title", default="", namespaces=NS)) or video_id,
                description=entry.findtext(
                    "media:group/media:description", default="", namespaces=NS
                )
                or "",
                published=_date(entry.findtext("atom:published", default="", namespaces=NS)),
                short=link is not None and "/shorts/" in (link.get("href") or ""),
            )
        )
    return videos


def _dig(node: Any, *keys: str) -> Any:
    for key in keys:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


def _text(value: Any) -> str:
    """YouTube's text objects: {"simpleText": …} or {"runs": [{"text": …}, …]}."""
    if not isinstance(value, dict):
        return ""
    if isinstance(value.get("simpleText"), str):
        return str(value["simpleText"])
    runs = value.get("runs")
    if not isinstance(runs, list):
        return ""
    return "".join(str(run.get("text", "")) for run in runs if isinstance(run, dict))


def _selected_tab(data: Any) -> Any:
    """The content of the page's selected tab when it is the «Videos» tab, else None (YouTube
    answers a missing tab with another one)."""
    tabs = _dig(data, "contents", "twoColumnBrowseResultsRenderer", "tabs")
    for tab in tabs if isinstance(tabs, list) else []:
        renderer = _dig(tab, "tabRenderer")
        if isinstance(renderer, dict) and renderer.get("selected"):
            url = _dig(renderer, "endpoint", "commandMetadata", "webCommandMetadata", "url")
            if isinstance(url, str) and url.endswith("/videos"):
                return renderer.get("content")
            return None
    return None


def _renderers(data: Any) -> Iterator[tuple[str, dict[str, Any]]]:
    """Every video renderer in `data`, in page order; at most `MAX_JSON_NODES` nodes are visited
    (no recursion, whatever the JSON looks like)."""
    stack: list[Any] = [data]
    for _visit in range(MAX_JSON_NODES):
        if not stack:
            return
        node = stack.pop()
        if isinstance(node, dict):
            children = []
            for key, value in node.items():
                if key in PAGE_RENDERERS and isinstance(value, dict):
                    yield key, value
                else:
                    children.append(value)
            stack.extend(reversed(children))
        elif isinstance(node, list):
            stack.extend(reversed(node))


def _page_video(name: str, node: dict[str, Any]) -> FeedVideo | None:
    if name == "lockupViewModel":
        if node.get("contentType") != "LOCKUP_CONTENT_TYPE_VIDEO":
            return None  # a playlist or a channel
        video_id = node.get("contentId")
        title = _dig(node, "metadata", "lockupMetadataViewModel", "title", "content")
    elif name == "shortsLockupViewModel":
        video_id = _dig(node, "onTap", "innertubeCommand", "reelWatchEndpoint", "videoId")
        title = _dig(node, "overlayMetadata", "primaryText", "content")
    else:  # videoRenderer, gridVideoRenderer, reelItemRenderer: the page before 2025
        video_id = node.get("videoId")
        title = _text(node.get("title") or node.get("headline"))
    if not isinstance(video_id, str) or not VIDEO_ID_RE.fullmatch(video_id):
        return None
    return FeedVideo(
        video_id=video_id,
        title=_clean(title if isinstance(title, str) else "") or video_id,
        description="",
        published=None,
        short=name in SHORT_RENDERERS,
    )


def parse_videos_page(html: str) -> list[FeedVideo]:
    """The videos of the channel's «Videos» tab, from the page's `ytInitialData` JSON (no
    description, no exact date). Raises ValueError when there are none: a consent or error page,
    another tab, a cut-off page, or YouTube changed the page."""
    marker = INITIAL_DATA_RE.search(html)
    if marker is None:
        raise ValueError("no ytInitialData on the page")
    try:
        data, _end = json.JSONDecoder().raw_decode(html, marker.end())
    except (ValueError, RecursionError) as error:
        raise ValueError(f"bad ytInitialData: {error}") from None
    tab = _selected_tab(data)
    if tab is None:
        raise ValueError("the page is not the «Videos» tab")
    videos: list[FeedVideo] = []
    seen: set[str] = set()
    for name, node in _renderers(tab):
        video = _page_video(name, node)
        if video is not None and video.video_id not in seen:
            seen.add(video.video_id)
            videos.append(video)
            if len(videos) >= MAX_PAGE_VIDEOS:
                break
    if not videos:
        raise ValueError("no videos in ytInitialData (has YouTube changed the page?)")
    return videos


def fetch_videos(cid: str, deadline: float | None = None) -> tuple[list[FeedVideo], str]:
    """The channel's latest videos and where they came from: the feed, else the channel page.
    Raises SyncError when neither answered within the run's time budget."""
    deadline = _deadline(deadline)
    try:
        return parse_feed(_get_retrying(FEED_URL.format(cid), FEED_RETRY_DELAYS, deadline)), "feed"
    except (OSError, http.client.HTTPException, ValueError) as error:
        feed_error = error
    logger.info("youtube: the feed failed (%s), reading the channel page", feed_error)
    try:
        page = _get_retrying(VIDEOS_PAGE_URL.format(cid), PAGE_RETRY_DELAYS, deadline)
        return parse_videos_page(page.decode("utf-8", "replace")), "channel page"
    except (OSError, http.client.HTTPException, ValueError) as error:
        raise SyncError(f"feed: {feed_error}; channel page: {error}") from error


def guess_topic(text: str) -> str:
    for topic, pattern in TOPIC_WORDS:
        if pattern.search(text or ""):
            return topic
    return ""


def _cover(video_id: str, deadline: float | None = None) -> tuple[bytes, tuple[int, int]] | None:
    """The biggest cover YouTube has for the video and its size, checked to be a real JPEG. None
    once the run's time budget is spent (a later run fetches it, see `sync_channel`)."""
    from PIL import Image as PILImage

    deadline = _deadline(deadline)
    for name in THUMBNAILS:
        if time.monotonic() > deadline:
            return None
        try:
            data = _get(THUMBNAIL_URL.format(video_id, name))
        except (OSError, http.client.HTTPException):
            continue
        if len(data) < 2000:  # YouTube's grey placeholder for a missing size
            continue
        try:
            with PILImage.open(BytesIO(data)) as probe:
                if probe.format == "JPEG":
                    return data, probe.size
        except (OSError, ValueError, PILImage.DecompressionBombError):
            continue
    return None


def _poster(video_id: str, title: str, deadline: float | None = None) -> Any:
    """Download the video cover once and keep it as a portal image (None when unreachable)."""
    from django.core.files.images import ImageFile

    from apps.media_library.models import PortalImage

    cover = _cover(video_id, deadline)
    if cover is None:
        logger.info("youtube: no cover for %s yet", video_id)
        return None
    data, (width, height) = cover
    image = PortalImage(title=title[:255], description=title[:255], credit="YouTube")
    image.file.save(f"youtube-{video_id}.jpg", ImageFile(BytesIO(data)), save=False)
    # file.save() recomputes the size from the stored file; set it from the bytes we have
    image.width, image.height = width, height
    image.file_size = len(data)
    image.save()
    return image


def _has_file(image: Any) -> bool:
    return image is not None and bool(image.file) and image.file.storage.exists(image.file.name)


def _watch_id(url: str) -> str:
    """The id in `https://www.youtube.com/watch?v=…` (what the sync stores), else ""."""
    value = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query).get("v", [""])[0]
    return value if VIDEO_ID_RE.fullmatch(value) else ""


def _restore_covers(deadline: float, skip: set[str]) -> int:
    """Covers the sync owns are fetched again, listed in today's feed or not (the feed shows only
    the latest 15): one the sync could not fetch when it made the video (no time left, YouTube
    unreachable), and one whose file is gone (lost disk, restored database). A video without a
    cover for any other reason — an editor's video, a cover an editor removed — is left alone."""
    from apps.media_library.models import Video, VideoSource

    restored = tried = 0
    videos = Video.objects.filter(source=VideoSource.YOUTUBE).select_related("poster")
    for video in videos.order_by("-created_at"):
        if tried >= MAX_COVER_REPAIRS or time.monotonic() >= deadline:
            break
        video_id = _watch_id(video.external_url)
        if not video_id or video_id in skip or cache.get(NO_COVER_KEY.format(video_id)):
            continue
        pending = cache.get(COVER_PENDING_KEY.format(video_id))
        lost = video.poster_id is not None and not _has_file(video.poster)
        if not (pending or lost):
            continue
        tried += 1
        poster = _poster(video_id, video.title, deadline)
        if poster is None:  # no page-cache flush for it; YouTube had none → try again tomorrow
            if time.monotonic() < deadline:
                cache.set(NO_COVER_KEY.format(video_id), 1, NO_COVER_SECONDS)
            continue
        video.poster = poster
        video.save(update_fields=["poster"])
        cache.delete(COVER_PENDING_KEY.format(video_id))
        restored += 1
    return restored


def sync_channel(channel_url: str) -> list[str]:
    """Add the channel's videos that are not on the site yet. Returns their ids; raises SyncError
    when YouTube could not be read. One run at a time (two would add the same video twice)."""
    from apps.media_library.models import Video, VideoKind, VideoSource, VideoStatus

    # one budget for the whole run (channel id, feed or page, covers): the start-up sync runs
    # before gunicorn and must end well inside the host's health-check window
    deadline = time.monotonic() + SYNC_BUDGET_SECONDS
    try:
        cid = channel_id(channel_url, deadline)
    except (OSError, http.client.HTTPException) as error:
        raise SyncError(f"channel id: {error}") from error
    if not cid:
        return []
    token = secrets.token_hex(8)
    if cache.add(LOCK_KEY, token, LOCK_SECONDS) is False:  # None = no cache (Redis down): go on
        logger.info("youtube: another sync is running")
        return []
    try:
        items, source = fetch_videos(cid, deadline)
        added = []
        for item in items:
            if Video.objects.filter(external_url__contains=item.video_id).exists():
                continue
            poster = _poster(item.video_id, item.title, deadline)
            Video.objects.create(
                title=item.title[:200],
                topic=guess_topic(item.title) or guess_topic(item.description),
                kind=VideoKind.SHORT_VERTICAL if item.short else VideoKind.LONG,
                source=VideoSource.YOUTUBE,
                external_url=f"https://www.youtube.com/watch?v={item.video_id}",
                poster=poster,
                status=VideoStatus.READY,
            )
            if poster is None:  # a later run fetches it (`_restore_covers`)
                cache.set(COVER_PENDING_KEY.format(item.video_id), 1, COVER_PENDING_SECONDS)
            added.append(item.video_id)
        repaired = _restore_covers(deadline, skip=set(added))  # just tried
    finally:
        if cache.get(LOCK_KEY) == token:  # a run that outlived its lock leaves the next one's
            cache.delete(LOCK_KEY)
    if added or repaired:
        from apps.core.cache import bump_page_cache

        bump_page_cache()
    logger.info(
        "youtube: %s from the %s: %d listed, %d new %s, %d cover(s) restored",
        cid,
        source,
        len(items),
        len(added),
        ",".join(added),
        repaired,
    )
    return added


def channel_url_from_settings() -> str:
    from wagtail.models import Site

    from apps.core.models import SiteSettings

    site = Site.objects.filter(is_default_site=True).first()
    return SiteSettings.for_site(site).youtube_url if site else ""


def sync_from_settings() -> list[str]:
    """`sync_channel` for the channel in Site settings; never raises (a page or a start-up must not
    break). Sets the `sync_soon` throttle from the outcome: the next try in 30 minutes after a run
    that reached YouTube, in 5 minutes after one that did not."""
    added: list[str] = []
    reached = False
    try:
        added = sync_channel(channel_url_from_settings())
        reached = True
    except SyncError as error:  # YouTube unreachable for now: expected, no traceback
        logger.warning("youtube: sync failed: %s", error)
    except Exception:  # YouTube's format changed or a bug: logged with the traceback
        logger.exception("youtube: sync failed")
    cache.set(THROTTLE_KEY, 1, THROTTLE_SECONDS if reached else FAILURE_THROTTLE_SECONDS)
    return added


def sync_soon() -> None:
    """Hosts without a Celery worker: one run in a background thread, at most every 30 minutes (5
    after a failed run, see `sync_from_settings`). The throttle is taken before the run, so page
    views across the gunicorn workers start only one."""
    if not cache.add(THROTTLE_KEY, 1, THROTTLE_SECONDS):
        return

    def run() -> None:
        from django.db import connection

        try:
            sync_from_settings()
        finally:
            connection.close()

    threading.Thread(target=run, name="youtube-sync", daemon=True).start()
