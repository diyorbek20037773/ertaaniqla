"""Editor placeholders never reach visitors (client request 2026-10-15, D-087).

Seeded content carries `[[TODO: content — copywriter]]`, `[[VERIFY: doctor]]`,
`[[TODO: legal text — client lawyer]]` and similar markers (spec: never write medical content).
They stay in the database — `manage.py find_placeholders` and the CMS preview still show them to
editors — but public HTML / JSON is cleaned on the way out:

* every `[[TODO…]]` / `[[VERIFY…]]` marker is removed, together with the «Matn shifokor
  tekshiruvini kutmoqda.» note that goes with a marker;
* paragraphs and italics left empty are dropped; a text card left without text is hidden by CSS.

Place right after `PageCacheMiddleware`, so the cached copy is already clean and the `/oz/`
Cyrillic view (outer) converts the clean text.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse

MARKER_RE = re.compile(r"[ \t]*\[\[(?:TODO|VERIFY)\b[^\]]*\]\]")
NOTE_RE = re.compile(
    r"(?:Matn shifokor tekshiruvini kutmoqda\.|Текст ожидает проверки врачом\.)"
    r"(?=\s*\[\[(?:TODO|VERIFY)\b)"
)
# only bare rich-text tags (Wagtail adds data-block-key): a template's empty live region or icon
# element keeps its class / aria attributes and is never touched
_BARE = r'(?:\s+data-block-key="[^"]*")?'
EMPTY_TAG_RE = re.compile(rf"<(p|i|em|b|strong|li|h[2-4]){_BARE}>(?:\s|&nbsp;|<br\s*/?>)*</\1>")
EMPTY_LIST_RE = re.compile(rf"<(ul|ol){_BARE}>\s*</\1>")
CLEANED_TYPES = ("text/html", "application/json")


def strip_placeholders(text: str) -> str:
    if "[[" not in text:
        return text
    text = MARKER_RE.sub("", NOTE_RE.sub("", text))
    for _ in range(3):  # <p><i></i></p> → <p></p> → gone
        cleaned = EMPTY_LIST_RE.sub("", EMPTY_TAG_RE.sub("", text))
        if cleaned == text:
            break
        text = cleaned
    return text


class PlaceholderStripMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response
        self.skip = (f"/{settings.CMS_URL_PREFIX}/", "/django-admin/")

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        if request.path_info.startswith(self.skip) or response.streaming:
            return response
        if not response.get("Content-Type", "").startswith(CLEANED_TYPES):
            return response
        charset = response.charset or "utf-8"
        body = response.content.decode(charset)
        cleaned = strip_placeholders(body)
        if cleaned != body:
            response.content = cleaned.encode(charset)
            if response.has_header("Content-Length"):
                response["Content-Length"] = str(len(response.content))
        return response
