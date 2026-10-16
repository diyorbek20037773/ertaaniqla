"""Client news template (Word) → news data the site publishes (`manage.py publish_client_news`).

The client sends news in one Word file per topic: for every item the blocks «Сарлавҳа»,
«Қисқа мазмун», «Асосий матн», «Мавзу», «Сана», «Муқова расми», each first in Uzbek (Latin)
and then in Russian. This script reads that layout, keeps the client's text as written (only
apostrophes normalised to ʻ / ʼ), and writes `apps/posts/news/<name>.json` plus the covers
(downloaded from the Google Drive links, max 1600 px) into `apps/posts/seed_media/`.

    python scripts/news_docx.py "docs/task_16.10.26/Янгиликлар (2).docx" breast 2026-10-16-breast

Body rules: a paragraph in bold → subheading (h2); a short line without final punctuation →
h2, or h3 when it starts with «1.»; Word list items → a bullet list; bold words inside a
paragraph stay bold. The first body paragraph repeats the summary and is dropped (the summary is
the page's lead). Review the JSON before publishing: it is what the site will show.
"""

from __future__ import annotations

import html
import io
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
MARKERS = {
    "сарлавҳа": "title",
    "қисқамазмун": "summary",
    "асосийматн": "body",
    "мавзу": "topic",
    "сана": "date",
    "муқовараcми": "cover",
    "муқоварасми": "cover",
}
CYRILLIC = re.compile(r"[А-Яа-яЁёЎўҚқҒғҲҳ]")
LATIN = re.compile(r"[A-Za-z]")
DRIVE_ID = re.compile(r"/file/d/([\w-]+)")
_APOS = re.compile(r"(?<=[oOgG])['’`‘]|['’`‘]")


def uz(text: str) -> str:
    """Uzbek Latin apostrophes: oʻ / gʻ take U+02BB, every other one U+02BC."""
    return _APOS.sub(lambda m: "ʻ" if m.start() and text[m.start() - 1] in "oOgG" else "ʼ", text)


def is_russian(text: str) -> bool:
    return len(CYRILLIC.findall(text)) > len(LATIN.findall(text))


class Para:
    def __init__(self, node: ET.Element, rels: dict[str, str]) -> None:
        self.is_list = node.find(f"{W}pPr/{W}numPr") is not None
        self.runs: list[tuple[str, bool]] = []
        self.links: list[str] = []
        for child in node:
            if child.tag == W + "r":
                self.runs.append(self._run(child))
            elif child.tag == W + "hyperlink":
                target = rels.get(child.get(R + "id", ""), "")
                if target:
                    self.links.append(target)
                for run in child.iter(W + "r"):
                    self.runs.append(self._run(run))
        self.text = " ".join("".join(t for t, _b in self.runs).split())

    @staticmethod
    def _run(run: ET.Element) -> tuple[str, bool]:
        props = run.find(f"{W}rPr")
        bold = props is not None and props.find(f"{W}b") is not None
        if bold:
            value = props.find(f"{W}b").get(W + "val", "true")  # type: ignore[union-attr]
            bold = value not in ("0", "false")
        return "".join(t.text or "" for t in run.iter(W + "t")), bold

    @property
    def all_bold(self) -> bool:
        words = [(t, b) for t, b in self.runs if t.strip()]
        return bool(words) and all(b for _t, b in words)

    @property
    def marker(self) -> str:
        key = re.sub(r"\s+", "", self.text).lower()
        return MARKERS.get(key, "")

    def inline_html(self, normalise: bool) -> str:
        """The paragraph's text with its bold words kept (`<b>`), escaped."""
        fix = uz if normalise else (lambda s: s)
        if self.all_bold:
            return html.escape(fix(self.text), quote=False)
        out: list[str] = []
        for text, bold in self.runs:
            if not text:
                continue
            escaped = html.escape(fix(text), quote=False)
            out.append(f"<b>{escaped}</b>" if bold and text.strip() else escaped)
        joined = "".join(out).replace("</b><b>", "")
        joined = re.sub(r"<b>(\s*)</b>", r"\1", joined)
        joined = re.sub(r"<b>(\s+)", r"\1<b>", joined)
        joined = re.sub(r"(\s+)</b>", r"</b>\1", joined)
        return " ".join(joined.split())


def read_paragraphs(path: Path) -> list[Para]:
    with zipfile.ZipFile(path) as docx:
        xml = docx.read("word/document.xml")
        rels_xml = docx.read("word/_rels/document.xml.rels").decode("utf-8")
    rels = dict(re.findall(r'Id="([^"]+)"[^>]*Target="([^"]+)"', rels_xml))
    body = ET.fromstring(xml).find(f"{W}body")
    assert body is not None
    return [Para(node, rels) for node in body.iter(W + "p")]


def split_items(paras: list[Para]) -> list[dict[str, list[Para]]]:
    items: list[dict[str, list[Para]]] = []
    current: dict[str, list[Para]] | None = None
    block = ""
    for para in paras:
        marker = para.marker
        if marker == "title":
            current = {}
            items.append(current)
        if marker:
            block = marker
            if current is not None:
                current.setdefault(block, [])
            continue
        if current is not None and block and (para.text or para.links):
            current[block].append(para)
    return items


BOLD_HEADING_MAX = 80
PLAIN_HEADING_MAX = 60
STAGE_LINE_MAX = 160
STAGE_CODE = re.compile(r"^(?:[IV]{1,3}[A-C]?\d?)\s+[—–-]")


def heading_level(para: Para) -> int:
    """2 or 3 for a subheading, 0 for a paragraph. A bold lead-in that ends with «:» or a long
    bold sentence stays a (bold) paragraph."""
    text = para.text
    if para.is_list or not text or text.endswith(":"):
        return 0
    if STAGE_CODE.match(text) and len(text) <= STAGE_LINE_MAX:
        return 3  # «IIIB — …»: every sub-stage line is a small heading, long or short
    if para.all_bold:
        heading = len(text) <= BOLD_HEADING_MAX and not text.endswith(".")  # a bold sentence
    else:
        heading = (
            len(text) <= PLAIN_HEADING_MAX
            and not re.search(r"[.;!?…»”\",]$", text)
            and not text[0].islower()
        )
    if not heading:
        return 0
    return 3 if re.match(r"^\d+\.\s", text) or STAGE_CODE.match(text) else 2


def body_html(paras: list[Para], summary: str, normalise: bool, title: str = "") -> str:
    out: list[str] = []
    items: list[str] = []
    repeated = {" ".join(summary.split()), " ".join(title.split())}
    for index, para in enumerate(paras):
        if index < 2 and " ".join(para.text.split()) in repeated:
            continue  # the lead or the title repeated at the top
        if para.is_list:
            items.append(f"<li>{para.inline_html(normalise)}</li>")
            continue
        if items:
            out.append("<ul>" + "".join(items) + "</ul>")
            items = []
        text = para.inline_html(normalise)
        level = heading_level(para)
        if level:
            plain = html.escape(uz(para.text) if normalise else para.text, quote=False)
            out.append(f"<h{level}>{plain}</h{level}>")
        elif para.all_bold:
            out.append(f"<p><b>{text}</b></p>")
        else:
            out.append(f"<p>{text}</p>")
    if items:
        out.append("<ul>" + "".join(items) + "</ul>")
    return "".join(out)


def by_language(paras: list[Para]) -> tuple[list[Para], list[Para]]:
    """Each paragraph by its script (the files put either language first); a line with few
    letters (a stage code, a number) goes with the paragraph before it."""
    uzbek: list[Para] = []
    russian: list[Para] = []
    previous_russian = False
    for para in paras:
        letters = len(CYRILLIC.findall(para.text)) + len(LATIN.findall(para.text))
        russian_now = is_russian(para.text) if letters >= 6 else previous_russian
        (russian if russian_now else uzbek).append(para)
        previous_russian = russian_now
    return uzbek, russian


def download_cover(drive_id: str, slug: str) -> str:
    from PIL import Image, ImageOps

    url = f"https://drive.google.com/uc?export=download&id={drive_id}"
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read()
    image = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
    image.thumbnail((1600, 1600))
    name = f"{slug}.jpg"
    image.save(
        ROOT / "apps" / "posts" / "seed_media" / name,
        "JPEG",
        quality=82,
        optimize=True,
        progressive=True,
    )
    return name


def slug_of(text: str) -> str:
    from anyascii import anyascii

    ascii_text = anyascii(text.replace("ʻ", "").replace("ʼ", "").replace("'", "")).lower()
    return re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")[:80].rstrip("-")


def convert(path: Path, topic: str) -> list[dict[str, object]]:
    result = []
    for raw in split_items(read_paragraphs(path)):
        titles = [p.text for p in raw.get("title", [])]
        summaries = [p.text for p in raw.get("summary", [])]
        title_uz = next(t for t in titles if not is_russian(t))
        title_ru = next((t for t in titles if is_russian(t)), "")
        summary_uz = next(t for t in summaries if not is_russian(t))
        summary_ru = next((t for t in summaries if is_russian(t)), "")
        body_uz, body_ru = by_language(raw.get("body", []))
        date = next(p.text for p in raw.get("date", []))
        day, month, year = re.findall(r"\d+", date)[:3]
        links = [link for p in raw.get("cover", []) for link in p.links] + [
            p.text for p in raw.get("cover", []) if "drive.google" in p.text
        ]
        drive = next(
            (DRIVE_ID.search(link).group(1) for link in links if DRIVE_ID.search(link)), ""
        )
        slug = slug_of(uz(title_uz))
        result.append(
            {
                "slug": slug,
                "slug_ru": slug_of(title_ru) if title_ru else "",
                "topic": topic,
                "date": f"{year}-{int(month):02d}-{int(day):02d}",
                "cover": download_cover(drive, slug) if drive else "",
                "uz": {
                    "title": uz(title_uz),
                    "summary": uz(summary_uz),
                    "body": body_html(body_uz, summary_uz, normalise=True, title=title_uz),
                },
                "ru": {
                    "title": title_ru,
                    "summary": summary_ru,
                    "body": body_html(body_ru, summary_ru, normalise=False, title=title_ru)
                    if body_ru
                    else "",
                },
            }
        )
    return result


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    path, topic, name = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    items = convert(path, topic)
    target = ROOT / "apps" / "posts" / "news" / f"{name}.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(items, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for item in items:
        print(
            item["date"],
            item["slug"],
            "| cover:",
            item["cover"] or "-",
            "| ru:",
            bool(item["ru"]["body"]),
        )  # type: ignore[index]
    print("→", target.relative_to(ROOT))


if __name__ == "__main__":
    main()
