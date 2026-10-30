"""Telegram channel → «Yangiliklar» (D-109). Every post of the portal's channel becomes a published
news item by itself; an edited post updates it.

* the bot (`TELEGRAM_NEWS_BOT_TOKEN`) is an admin of the channel (`TELEGRAM_NEWS_CHANNEL`), so
  Telegram sends it `channel_post` / `edited_channel_post` updates. They arrive at
  `/telegram/webhook/` (registered by `manage.py telegram_news setup`) one at a time
  (max_connections=1), carrying a secret header derived from SECRET_KEY and the token;
* a post becomes: title = its first line (emoji trimmed), summary = the next paragraph, body =
  the rest (bold, italic and links kept), date = the post's date, topic guessed from the words
  (koʻkrak / bachadon / bola…, empty = «Barchasi» only), picture = the photo or the video's
  preview. A video, GIF or file post also embeds the Telegram post itself, so it plays on the
  page;
* language: the channel writes in Uzbek, in Russian, or both in one post split by a line of
  ➖ / — / _ . The Uzbek part goes to /uz/yangiliklar/ and the Russian part becomes its Russian
  version (/ru/novosti/); a Russian-only post is published in Russian only;
* an album arrives as one message per photo; the captioned one makes the item, the other photos
  join it (the first as the picture when it has none, the rest as a gallery);
* an edit rewrites the item only while nobody has edited it in the CMS (a person's revision
  wins). Telegram never tells a bot about deleted posts: unpublish those in the CMS;
* requests go to https://api.telegram.org only (no redirects), with a timeout and a size cap;
  the token never appears in an exception or a log line.
"""

from __future__ import annotations

import bisect
import contextlib
import datetime as dt
import hashlib
import hmac
import http.client
import json
import logging
import re
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from html import escape
from io import BytesIO
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.db import transaction
from django.utils.text import slugify

from apps.media_library.youtube import guess_topic

if TYPE_CHECKING:
    from apps.posts.models import PostIndexPage, PostPage, TelegramPost

logger = logging.getLogger("ertaaniqla.telegram")

API_URL = "https://api.telegram.org/bot{token}/{method}"
FILE_URL = "https://api.telegram.org/file/bot{token}/{path}"
ALLOWED_UPDATES = ("channel_post", "edited_channel_post")
TIMEOUT = 15
MAX_API_BYTES = 1024 * 1024
MAX_IMAGE_BYTES = 10 * 1024 * 1024
TITLE_MAX = 150
SUMMARY_MAX = 300
SLUG_MAX = 80
MIN_PART_LETTERS = 20  # a shorter part (a signature, an emoji line) joins its neighbour
MIN_HALF_LETTERS = 60  # each language of a bilingual post without a separator line
# a line made only of these (at least 2 of them) splits a bilingual post: ➖➖➖, ——, ____, -----
SEPARATOR_RE = re.compile(r"^[➖—–\-_=*•~·.\s]+$")
UZ_CYRILLIC = frozenset("ўқғҳЎҚҒҲ")
HASHTAG_OR_MENTION_RE = re.compile(r"[#@][\w.]+")
_APOS = re.compile(r"['’`‘]")
TITLE_LEAD = frozenset('«"„“(')
TITLE_TAIL_TRIM = ":;,.-–—"
EMBED_KINDS = ("video", "animation", "document", "audio", "voice", "video_note")


class TelegramError(Exception):
    """A Bot API call without a usable answer. The message never contains the token."""


# --- Bot API --------------------------------------------------------------------------------
class _NoRedirects(urllib.request.HTTPRedirectHandler):
    """api.telegram.org never redirects; a 30x is an error, not a hop to another host."""

    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None


_OPENER = urllib.request.build_opener(_NoRedirects)


def bot_token() -> str:
    return str(settings.TELEGRAM_NEWS_BOT_TOKEN).strip()


def _open(url: str, data: bytes | None, limit: int, what: str) -> bytes:
    headers = {"Content-Type": "application/json"} if data is not None else {}
    request = urllib.request.Request(url, data=data, headers=headers)  # noqa: S310 - fixed host
    try:
        with _OPENER.open(request, timeout=TIMEOUT) as response:
            body = bytes(response.read(limit + 1))
    except urllib.error.HTTPError as error:
        detail = ""
        with contextlib.suppress(ValueError, OSError, AttributeError):
            detail = str(json.loads(error.read(MAX_API_BYTES)).get("description", ""))
        error.close()
        raise TelegramError(f"{what}: HTTP {error.code} {detail}".rstrip()) from None
    except (OSError, http.client.HTTPException) as error:  # URLError, timeouts, resets
        raise TelegramError(f"{what}: {type(error).__name__}") from None
    if len(body) > limit:
        raise TelegramError(f"{what}: more than {limit} bytes")
    return body


def api(method: str, **params: Any) -> Any:
    """One Bot API call (JSON POST); its `result`, or TelegramError."""
    token = bot_token()
    if not token:
        raise TelegramError("TELEGRAM_NEWS_BOT_TOKEN is not set")
    body = _open(
        API_URL.format(token=token, method=method),
        json.dumps(params).encode(),
        MAX_API_BYTES,
        method,
    )
    try:
        answer = json.loads(body)
    except ValueError:
        raise TelegramError(f"{method}: not JSON") from None
    if not isinstance(answer, dict) or not answer.get("ok"):
        description = answer.get("description", "error") if isinstance(answer, dict) else "error"
        raise TelegramError(f"{method}: {description}")
    return answer.get("result")


def download(file_id: str) -> bytes:
    """The bytes of a file the bot can see (photos, video previews), at most MAX_IMAGE_BYTES."""
    info = api("getFile", file_id=file_id) or {}
    path = str(info.get("file_path") or "")
    if not path or path.startswith("/") or ".." in path:
        raise TelegramError("getFile: no file path")
    if int(info.get("file_size") or 0) > MAX_IMAGE_BYTES:
        raise TelegramError("getFile: file too big")
    url = FILE_URL.format(token=bot_token(), path=urllib.parse.quote(path))
    return _open(url, None, MAX_IMAGE_BYTES, "file")


def webhook_secret() -> str:
    """The `secret_token` Telegram sends back in X-Telegram-Bot-Api-Secret-Token: changes with
    the token or SECRET_KEY, so rotating either one locks out the old webhook."""
    message = f"telegram-news:{bot_token()}".encode()
    return hmac.new(settings.SECRET_KEY.encode(), message, hashlib.sha256).hexdigest()


def channel_name() -> str:
    """`TELEGRAM_NEWS_CHANNEL` without @ or https://t.me/ (a numeric id stays as it is)."""
    value = str(settings.TELEGRAM_NEWS_CHANNEL).strip()
    value = re.sub(r"^(?:https?://)?(?:t\.me|telegram\.me)/", "", value, flags=re.I)
    return value.strip("/").lstrip("@")


def is_our_channel(chat: dict[str, Any]) -> bool:
    name = channel_name()
    if not name or chat.get("type") != "channel":
        return False
    username = str(chat.get("username") or "")
    return name.lower() == username.lower() or name == str(chat.get("id"))


# --- text → title / summary / body ----------------------------------------------------------
@dataclass
class Styled:
    """A message text with its Telegram formatting, indexed by Python character position."""

    text: str
    bold: list[bool]
    italic: list[bool]
    href: list[str]


def _safe_url(kind: str, entity: dict[str, Any], text: str) -> str:
    if kind == "text_link":
        url = str(entity.get("url") or "")
    elif kind == "url":
        url = text if re.match(r"(?i)https?://", text) else f"https://{text}"
    else:  # mention
        url = f"https://t.me/{text.lstrip('@')}"
    parts = urllib.parse.urlsplit(url)
    return url if parts.scheme in ("http", "https") and parts.hostname else ""


def styled(text: str, entities: list[dict[str, Any]] | None) -> Styled:
    """Map the entities (UTF-16 offsets) onto the characters: bold, italic and links survive,
    everything else (code, spoilers, custom emoji…) becomes plain text."""
    starts: list[int] = []
    position = 0
    for char in text:
        starts.append(position)
        position += 2 if ord(char) > 0xFFFF else 1
    size = len(text)
    result = Styled(text, [False] * size, [False] * size, [""] * size)
    for entity in entities or []:
        try:
            begin = int(entity.get("offset", 0))
            end = begin + int(entity.get("length", 0))
        except (TypeError, ValueError):
            continue
        first, last = bisect.bisect_left(starts, begin), bisect.bisect_left(starts, end)
        if first >= last:
            continue
        kind = entity.get("type")
        if kind == "bold":
            result.bold[first:last] = [True] * (last - first)
        elif kind == "italic":
            result.italic[first:last] = [True] * (last - first)
        elif kind in ("text_link", "url", "mention"):
            url = _safe_url(str(kind), entity, text[first:last])
            if url:
                result.href[first:last] = [url] * (last - first)
    return result


def uz_apostrophes(text: str) -> str:
    """oʻ / gʻ take U+02BB, every other apostrophe U+02BC (the site's Uzbek spelling)."""
    return _APOS.sub(lambda m: "ʻ" if m.start() and text[m.start() - 1] in "oOgG" else "ʼ", text)


def _render(st: Styled, start: int, end: int, uz: bool) -> str:
    """The characters [start, end) as rich-text HTML: runs of equal formatting share one tag."""
    out: list[str] = []
    index = start
    while index < end:
        key = (st.bold[index], st.italic[index], st.href[index])
        stop = index + 1
        while stop < end and (st.bold[stop], st.italic[stop], st.href[stop]) == key:
            stop += 1
        chunk = st.text[index:stop]
        html = escape(uz_apostrophes(chunk) if uz else chunk, quote=False)
        bold, italic, href = key
        if italic:
            html = f"<i>{html}</i>"
        if bold:
            html = f"<b>{html}</b>"
        if href:
            html = f'<a href="{escape(href)}">{html}</a>'
        out.append(html)
        index = stop
    return "".join(out)


def _lines(text: str) -> list[tuple[int, int]]:
    spans, start = [], 0
    for line in text.split("\n"):
        spans.append((start, start + len(line)))
        start += len(line) + 1
    return spans


def _trim(text: str, start: int, end: int) -> tuple[int, int]:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def _is_separator(line: str) -> bool:
    stripped = "".join(line.split())
    return len(stripped) >= 2 and bool(SEPARATOR_RE.match(stripped))


def _language(text: str, minimum: int = MIN_PART_LETTERS) -> str:
    """ "uz" (Latin, or Cyrillic with ў қ ғ ҳ), "ru" (other Cyrillic) or "" (too few letters)."""
    cyrillic = sum(1 for c in text if "\u0400" <= c <= "\u04ff")
    latin = sum(1 for c in text if c.isascii() and c.isalpha())
    if cyrillic + latin < max(minimum, 1):
        return ""
    if cyrillic > latin:
        return "uz" if any(c in UZ_CYRILLIC for c in text) else "ru"
    return "uz"


def _paragraphs(text: str) -> list[list[tuple[int, int]]]:
    """The lines grouped by blank lines."""
    groups: list[list[tuple[int, int]]] = [[]]
    for start, end in _lines(text):
        if text[start:end].strip():
            groups[-1].append((start, end))
        elif groups[-1]:
            groups.append([])
    return [group for group in groups if group]


def _letters(text: str, part: list[tuple[int, int]]) -> int:
    return sum(1 for a, b in part for c in text[a:b] if c.isalpha())


def _by_language(
    text: str, parts: list[list[tuple[int, int]]]
) -> list[tuple[str, list[tuple[int, int]]]]:
    """Each part with its language; a part too short to tell (a signature, an emoji line) takes
    the language of the part before it (of the first known one, at the start). Neighbours of one
    language are merged, a blank span between them keeping the paragraph break."""
    languages = [_language("\n".join(text[a:b] for a, b in part)) for part in parts]
    known = [language for language in languages if language]
    current = known[0] if known else (_language(text, minimum=1) or "uz")
    merged: list[tuple[str, list[tuple[int, int]]]] = []
    for part, language in zip(parts, languages, strict=True):
        current = language or current
        if merged and merged[-1][0] == current:
            merged[-1][1].append((part[0][0], part[0][0]))
            merged[-1][1].extend(part)
        else:
            merged.append((current, list(part)))
    return merged


def split_languages(text: str) -> dict[str, list[tuple[int, int]]]:
    """The post's lines by language. Separator lines (➖➖➖, ——, ____) cut it into parts. A post
    without one is cut where the language changes, but only at one place and with both halves
    of some length — an Uzbek post quoting a Russian line stays one Uzbek item."""
    parts: list[list[tuple[int, int]]] = [[]]
    for start, end in _lines(text):
        if _is_separator(text[start:end]):
            parts.append([])
        else:
            parts[-1].append((start, end))
    parts = [part for part in parts if any(text[a:b].strip() for a, b in part)]
    merged = _by_language(text, parts)
    if len(parts) <= 1:
        halves = _by_language(text, _paragraphs(text))
        if len(halves) == 2 and all(_letters(text, h) >= MIN_HALF_LETTERS for _, h in halves):
            merged = halves
    result: dict[str, list[tuple[int, int]]] = {}
    for language, lines in merged:
        if language in result:  # uz, ru, uz again: one item per language
            result[language].append((lines[0][0], lines[0][0]))
        result.setdefault(language, []).extend(lines)
    return result


def _decor(char: str) -> bool:
    """Emoji, symbols, invisible joiners and spaces: trimmed from a title."""
    return unicodedata.category(char)[0] in "SZC" or char in "\ufe0f\u200d\u20e3"


def _lead_trimmed(text: str) -> str:
    """Whitespace collapsed, emoji / bullets before the first word dropped."""
    text = " ".join(text.split())
    while text and not (text[0].isalnum() or text[0] in TITLE_LEAD):
        text = text[1:].lstrip()
    return text


def _clean_title(text: str) -> str:
    """No emoji anywhere, no bullet in front, no colon or full stop at the end."""
    kept = "".join(" " if _decor(c) and not c.isspace() else c for c in text)
    return _lead_trimmed(kept).rstrip(TITLE_TAIL_TRIM + " ")


def _shorten(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    cut = text[: limit - 1].rsplit(" ", 1)[0].rstrip(TITLE_TAIL_TRIM + " ")
    return f"{cut}…"


@dataclass
class Article:
    title: str
    summary: str
    html: str  # rich text: <p> paragraphs, <br/> line breaks, <b>/<i>/<a>


def compose(st: Styled, lines: list[tuple[int, int]], uz: bool) -> Article | None:
    """Title, summary and body HTML of one language part; None when it has no words."""
    text = st.text

    def noise(start: int, end: int) -> bool:  # a line of hashtags / @mentions only
        line = text[start:end]
        rest = HASHTAG_OR_MENTION_RE.sub("", line)
        return line != rest and not any(c.isalnum() for c in rest)

    lines = [span for span in lines if not noise(*span)]
    first = next((k for k, (a, b) in enumerate(lines) if any(c.isalpha() for c in text[a:b])), -1)
    if first < 0:
        return None
    start, end = _trim(text, *lines[first])
    line = text[start:end]
    body_start = end  # where the body continues inside the title line
    if len(_clean_title(line)) > TITLE_MAX:
        sentence = None
        for match in re.finditer(r"[.!?…](?=\s)", line[: TITLE_MAX + 1]):
            if match.end() >= 30:  # the first sentence long enough to be a title
                sentence = match
                break
        if sentence is not None:
            line, body_start = line[: sentence.end()], start + sentence.end()
        else:
            body_start = start  # the whole line opens the body; the title is its shortened start
    title = _shorten(_clean_title(uz_apostrophes(line) if uz else line), TITLE_MAX)

    body_lines = [(body_start, end), *lines[first + 1 :]]
    paragraphs: list[list[tuple[int, int]]] = [[]]
    for span in body_lines:
        a, b = _trim(text, *span)
        if a == b:
            if paragraphs[-1]:
                paragraphs.append([])
        else:
            paragraphs[-1].append((a, b))
    paragraphs = [p for p in paragraphs if p]
    html = "".join(
        "<p>" + "<br/>".join(_render(st, a, b, uz) for a, b in paragraph) + "</p>"
        for paragraph in paragraphs
    )
    summary = ""
    if paragraphs:
        raw = " ".join(text[a:b] for a, b in paragraphs[0])
        summary = _shorten(_lead_trimmed(uz_apostrophes(raw) if uz else raw), SUMMARY_MAX)
    return Article(
        title=title or _shorten(" ".join(line.split()), TITLE_MAX), summary=summary, html=html
    )


# --- message → news item --------------------------------------------------------------------
def _message_text(message: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    if message.get("text"):
        return str(message["text"]), list(message.get("entities") or [])
    return str(message.get("caption") or ""), list(message.get("caption_entities") or [])


def _photo_file_id(message: dict[str, Any]) -> str:
    """The biggest photo size under the cap, else a video's / file's preview."""
    sizes = [
        size
        for size in message.get("photo") or []
        if int(size.get("file_size") or 0) <= MAX_IMAGE_BYTES
    ]
    if sizes:
        best = max(sizes, key=lambda s: int(s.get("width", 0)) * int(s.get("height", 0)))
        return str(best.get("file_id") or "")
    for kind in EMBED_KINDS:
        media = message.get(kind)
        if isinstance(media, dict):
            preview = media.get("thumbnail") or media.get("thumb") or {}
            if preview.get("file_id"):
                return str(preview["file_id"])
    return ""


def _embed_url(message: dict[str, Any]) -> str:
    """The public post's link when it carries a video / GIF / file (played through the embed)."""
    username = str(message.get("chat", {}).get("username") or "")
    if not username or not any(isinstance(message.get(kind), dict) for kind in EMBED_KINDS):
        return ""
    return f"https://t.me/{username}/{int(message['message_id'])}"


def _image(file_id: str, title: str, name: str) -> Any:
    """Download a photo once and keep it as a portal image; None when it cannot be had (the item
    is published without it rather than lost)."""
    from django.core.files.images import ImageFile
    from PIL import Image as PILImage

    from apps.media_library.models import PortalImage

    if not file_id:
        return None
    try:
        data = download(file_id)
        with PILImage.open(BytesIO(data)) as probe:
            if probe.format not in ("JPEG", "PNG", "WEBP"):
                raise TelegramError(f"photo: {probe.format} is not an image we keep")
            size = probe.size
    except (TelegramError, OSError, ValueError, PILImage.DecompressionBombError) as error:
        logger.warning("telegram: photo of %s skipped: %s", name, error)
        return None
    extension = {"PNG": "png", "WEBP": "webp"}.get(probe.format or "", "jpg")
    image = PortalImage(title=title[:255], description=title[:255], credit="Telegram")
    image.file.save(f"{name}.{extension}", ImageFile(BytesIO(data)), save=False)
    image.width, image.height = size
    image.file_size = len(data)
    image.save()
    return image


def _news_index(language: str) -> PostIndexPage | None:
    from wagtail.models import Locale

    from apps.posts.models import PostIndexPage, PostKind

    locale = Locale.objects.filter(language_code=language).first()
    if locale is None:
        return None
    return (
        PostIndexPage.objects.live()
        .filter(locale=locale, kind=PostKind.NEWS)
        .order_by("path")
        .first()
    )


RU_LATIN = {
    letter: latin.strip("-")  # ъ ь: no letter
    for letter, latin in zip(
        "абвгдеёжзийклмнопрстуфхцчшщъыьэюя",
        "a b v g d e e zh z i y k l m n o p r s t u f kh ts ch sh shch - y - e yu ya".split(),  # noqa: SIM905
        strict=True,
    )
}


def _slug(index: PostIndexPage, title: str, message_id: int) -> str:
    """The title's slug (Cyrillic spelled in Latin letters), with the message id when taken."""
    from apps.posts.models import PostPage

    latin = "".join(RU_LATIN.get(c, c) for c in title.lower())
    base = slugify(latin)[:SLUG_MAX].strip("-") or "telegram"
    slug = base
    if PostPage.objects.child_of(index).filter(slug=slug).exists():
        slug = f"{base[: SLUG_MAX - 12]}-{message_id}"
    return slug


def _body(article: Article, embed: str, keep: list[Any]) -> list[dict[str, Any]]:
    """Embed first, then the text, then what the item already had besides text (the album's
    gallery) — an edit replaces the text only."""
    body: list[dict[str, Any]] = []
    if embed and not any(block["type"] == "embed" for block in keep):
        body.append({"type": "embed", "value": {"url": embed, "caption": ""}})
    body.extend(block for block in keep if block["type"] == "embed")
    if article.html:
        body.append({"type": "rich_text", "value": article.html})
    body.extend(block for block in keep if block["type"] != "embed")
    return body


def _bot_owned(page: PostPage) -> bool:
    """True while every revision is the bot's (no user): a person's edit in the CMS wins."""
    return not page.revisions.exclude(user=None).exists()


def _publish(page: PostPage) -> None:
    page.save_revision().publish()


def _fill(page: PostPage, article: Article, embed: str) -> None:
    keep = [
        {"type": block.block_type, "value": block.block.get_prep_value(block.value)}
        for block in page.body
        if block.block_type != "rich_text"
    ]
    page.title = page.draft_title = article.title
    page.summary = article.summary
    page.body = _body(article, embed, keep)


@dataclass
class Post:
    """What the bot read from one message."""

    articles: dict[str, Article]
    topic: str
    date: dt.date
    embed: str
    photo: str


def read_post(message: dict[str, Any]) -> Post:
    from django.utils import timezone

    text, entities = _message_text(message)
    st = styled(text, entities)
    articles: dict[str, Article] = {}
    for language, lines in split_languages(text).items():
        article = compose(st, lines, uz=language == "uz")
        if article is not None:
            articles[language] = article
    stamp = dt.datetime.fromtimestamp(int(message.get("date") or 0), tz=dt.UTC)
    return Post(
        articles=articles,
        topic=guess_topic(text),
        date=timezone.localdate(stamp) if message.get("date") else timezone.localdate(),
        embed=_embed_url(message),
        photo=_photo_file_id(message),
    )


def _new_page(
    index: PostIndexPage, article: Article, post: Post, image: Any, message_id: int
) -> Any:
    from apps.posts.models import PostPage

    page = PostPage(
        title=article.title,
        slug=_slug(index, article.title, message_id),
        locale=index.locale,
        topic=post.topic,
        date=post.date,
        summary=article.summary,
        image=image,
        body=_body(article, post.embed, []),
    )
    index.add_child(instance=page)
    _publish(page)
    return page


def _create(post: Post, message: dict[str, Any], image: Any) -> tuple[Any, Any]:
    """The uz item and its ru version (or the ru item alone); (uz page, ru page)."""
    message_id = int(message["message_id"])
    uz_page = ru_page = None
    uz_article, ru_article = post.articles.get("uz"), post.articles.get("ru")
    uz_index = _news_index("uz")
    if uz_article is not None and uz_index is not None:
        uz_page = _new_page(uz_index, uz_article, post, image, message_id)
    ru_index = _news_index("ru")
    if ru_article is None or ru_index is None:
        return uz_page, ru_page
    locale = ru_index.locale
    if uz_page is not None and uz_page.get_parent().get_translation_or_none(locale) is not None:
        ru_page = uz_page.copy_for_translation(locale)  # linked: the language switch finds it
        _fill(ru_page, ru_article, post.embed)
        ru_page.slug = _slug(ru_page.get_parent(), ru_article.title, message_id)
        ru_page.save()
        _publish(ru_page)
    else:
        ru_page = _new_page(ru_index, ru_article, post, image, message_id)
    return uz_page, ru_page


def _add_photo(record: TelegramPost, file_id: str, name: str) -> None:
    """An album photo joins its item(s): the picture when there is none, else the gallery."""
    pages = [page for page in (record.page, record.ru_page) if page is not None]
    if not pages or not file_id:
        return
    image = _image(file_id, pages[0].title, name)
    if image is None:
        return
    for page in pages:
        page = page.specific
        if not _bot_owned(page):
            continue
        if page.image_id is None:
            page.image = image
        else:
            blocks = [
                {"type": block.block_type, "value": block.block.get_prep_value(block.value)}
                for block in page.body
            ]
            gallery = next((b for b in blocks if b["type"] == "image_gallery"), None)
            # ImageBlock's stored form, like the items get_prep_value gave back above
            item = {
                "image": {"image": image.pk, "alt_text": image.title, "decorative": False},
                "caption": "",
            }
            if gallery is None:
                blocks.append(
                    {
                        "type": "image_gallery",
                        "value": {"title": "", "images": [item], "downloadable": False},
                    }
                )
            else:
                gallery["value"]["images"].append(item)
            page.body = blocks
        page.save()
        _publish(page)


def _handle_new(message: dict[str, Any]) -> None:
    from apps.posts.models import TelegramPost

    chat_id, message_id = int(message["chat"]["id"]), int(message["message_id"])
    if TelegramPost.objects.filter(chat_id=chat_id, message_id=message_id).exists():
        return  # Telegram delivered it again
    group = str(message.get("media_group_id") or "")
    name = f"telegram-{abs(chat_id)}-{message_id}"
    post = read_post(message)
    album = (
        TelegramPost.objects.filter(chat_id=chat_id, media_group_id=group).order_by("message_id")
        if group
        else TelegramPost.objects.none()
    )
    joined = next((r for r in album if r.page_id or r.ru_page_id), None)
    if not post.articles:  # a photo without words: an album photo, or nothing for the site
        record = TelegramPost.objects.create(
            chat_id=chat_id,
            message_id=message_id,
            media_group_id=group,
            photo_file_id="" if joined else post.photo,
            page=joined.page if joined else None,
            ru_page=joined.ru_page if joined else None,
        )
        if joined:
            _add_photo(record, post.photo, name)
        return
    waiting = [r for r in album if r.photo_file_id and not (r.page_id or r.ru_page_id)]
    photo = post.photo
    if not photo and waiting:  # the caption came on a video: an earlier photo is the picture
        photo = waiting.pop(0).photo_file_id
    title = next(iter(post.articles.values())).title
    uz_page, ru_page = _create(post, message, _image(photo, title, name))
    record = TelegramPost.objects.create(
        chat_id=chat_id, message_id=message_id, media_group_id=group, page=uz_page, ru_page=ru_page
    )
    for earlier in album:
        if earlier.page_id or earlier.ru_page_id:
            continue
        earlier.page, earlier.ru_page = uz_page, ru_page
        file_id, earlier.photo_file_id = earlier.photo_file_id, ""
        earlier.save()
        if earlier in waiting:
            _add_photo(record, file_id, f"telegram-{abs(chat_id)}-{earlier.message_id}")
    logger.info(
        "telegram: post %s → %s",
        message_id,
        ", ".join(p.url_path for p in (uz_page, ru_page) if p is not None) or "nothing",
    )


def _handle_edit(message: dict[str, Any]) -> None:
    from apps.posts.models import TelegramPost

    chat_id, message_id = int(message["chat"]["id"]), int(message["message_id"])
    record = TelegramPost.objects.filter(chat_id=chat_id, message_id=message_id).first()
    if record is None:  # posted before the bot came: a new item
        _handle_new(message)
        return
    post = read_post(message)
    if not post.articles:
        return
    for language, page in (("uz", record.page), ("ru", record.ru_page)):
        article = post.articles.get(language)
        if page is None or article is None:
            continue
        page = page.specific
        if not _bot_owned(page):
            logger.info("telegram: edit of %s left out, %s was edited in the CMS", message_id, page)
            continue
        _fill(page, article, post.embed)
        page.topic = post.topic or page.topic
        page.save()
        _publish(page)


def handle_update(update: dict[str, Any]) -> None:
    """One webhook update. Messages of other chats and other update kinds are ignored."""
    for kind in ALLOWED_UPDATES:
        message = update.get(kind)
        if isinstance(message, dict):
            break
    else:
        return
    if not is_our_channel(message.get("chat") or {}) or "message_id" not in message:
        return
    with transaction.atomic():
        if kind == "channel_post":
            _handle_new(message)
        else:
            _handle_edit(message)
