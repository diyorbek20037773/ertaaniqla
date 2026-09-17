"""Uzbek Latin → Cyrillic transliteration for the `/oz/` site version (D-047, D-049).

Word rules (current Latin alphabet ↔ Cyrillic alphabet):

* sh ш · ch ч · oʻ ў · gʻ ғ · yo ё · yu ю · ya я · ye е · h ҳ · x х · q қ · j ж · y й
* e → э at the start of a word and after a vowel, otherwise е
* tutuq belgisi ʼ → ъ, except between s/c and h where it only separates the letters (Isʼhoq → Исҳоқ)
* "tsiya" / "tsion" in loanwords → ция / цион; other loanwords come from EXCEPTIONS / STEMS
* brand names and Roman numerals stay in Latin

Anything that is not a Latin word (Cyrillic, digits, URLs, e-mail addresses, [[placeholders]],
HTML entities) passes through unchanged. `transliterate_html` converts human-visible text only.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Any

TURNED_COMMA = "ʻ"  # U+02BB — letter modifier in oʻ / gʻ
TUTUQ = "ʼ"  # U+02BC — tutuq belgisi
APOSTROPHE_VARIANTS = "'’‘`´" + TURNED_COMMA + TUTUQ

LATIN_VOWELS = set("aeiou")
CYRILLIC_VOWELS = set("аеёиоуэюяў")

# Whole words (lower-case Latin) whose Cyrillic spelling is not derivable letter by letter.
# Add a word only with a source (Oʻzbek tilining imlo lugʻati); CMS-managed list = H-023.
EXCEPTIONS: dict[str, str] = {
    "yanvar": "январь",
    "fevral": "февраль",
    "aprel": "апрель",
    "iyun": "июнь",
    "iyul": "июль",
    "sentabr": "сентябрь",
    "oktabr": "октябрь",
    "noyabr": "ноябрь",
    "dekabr": "декабрь",
    "rayon": "район",
    "mayor": "майор",
    "sirk": "цирк",
    "yandex": "Яндекс",
}
# Stems: the word starts with the key, the rest is transliterated (vaksinalar → вакциналар).
STEMS: dict[str, str] = {
    "vaksin": "вакцин",
    "sitolog": "цитолог",
    "sement": "цемент",
    "kompyuter": "компьютер",
    "obyekt": "объект",
    "subyekt": "субъект",
    "aktyor": "актёр",
    "sentabr": "сентябр",
    "oktabr": "октябр",
    "noyabr": "ноябр",
    "dekabr": "декабр",
    "yanvar": "январ",
    "fevral": "феврал",
}
KEEP_LATIN = {
    "telegram",
    "whatsapp",
    "facebook",
    "instagram",
    "tiktok",
    "youtube",
    "google",
    "hpv",
    "email",
    "pdf",
    "sms",
    "wagtail",
}

_LETTERS = {
    "a": "а",
    "b": "б",
    "c": "с",  # not in the alphabet — only in foreign words
    "d": "д",
    "e": "е",
    "f": "ф",
    "g": "г",
    "h": "ҳ",
    "i": "и",
    "j": "ж",
    "k": "к",
    "l": "л",
    "m": "м",
    "n": "н",
    "o": "о",
    "p": "п",
    "q": "қ",
    "r": "р",
    "s": "с",
    "t": "т",
    "u": "у",
    "v": "в",
    "w": "в",
    "x": "х",
    "y": "й",
    "z": "з",
}
_DIGRAPHS = {
    "sh": "ш",
    "ch": "ч",
    "yo": "ё",
    "yu": "ю",
    "ya": "я",
    "ye": "е",
    "o" + TURNED_COMMA: "ў",
    "g" + TURNED_COMMA: "ғ",
}

_APOS = "[" + re.escape(APOSTROPHE_VARIANTS) + "]"
# a word: letters, inner apostrophes (maʼno, oʻrta) and a final oʻ/gʻ modifier (bogʻ)
WORD_RE = re.compile(r"[A-Za-z](?:[A-Za-z]|" + _APOS + r"(?=[A-Za-z])|(?<=[OoGg])" + _APOS + r")*")
ROMAN_RE = re.compile(r"^(?=[IVXLC])M{0,3}(C[MD]|D?C{0,3})(X[CL]|L?X{0,3})(I[XV]|V?I{0,3})$")
PROTECTED_RE = re.compile(
    r"\[\[[^\]]*\]\]"  # [[TODO: …]] placeholders
    r"|https?://\S+|www\.\S+"  # URLs
    r"|[\w.+-]+@[\w-]+\.[\w.-]+"  # e-mail addresses
    r"|&#?\w+;"  # HTML entities
)
TSIYA_RE = re.compile(r"ts(?=i[yo])")


def _normalise(word: str) -> str:
    """o'/g' (any apostrophe) → oʻ/gʻ; any other apostrophe → ʼ."""
    chars = list(word)
    for i, char in enumerate(chars):
        if char in APOSTROPHE_VARIANTS:
            previous = chars[i - 1].lower() if i else ""
            chars[i] = TURNED_COMMA if previous in ("o", "g") else TUTUQ
    return "".join(chars)


def _letters(lower: str, previous: str = "") -> str:
    out: list[str] = []
    i = 0
    while i < len(lower):
        pair = lower[i : i + 2]
        char = lower[i]
        if pair in _DIGRAPHS:
            out.append(_DIGRAPHS[pair])
            i += 2
            continue
        if char == "e":
            last = out[-1] if out else previous
            out.append("э" if not last or last in CYRILLIC_VOWELS or last == "ъ" else "е")
        elif char == TUTUQ:
            before = lower[i - 1] if i else ""
            after = lower[i + 1] if i + 1 < len(lower) else ""
            if not (before in ("s", "c") and after == "h"):
                out.append("ъ")
        else:
            out.append(_LETTERS.get(char, char))
        i += 1
    return "".join(out)


def _apply_case(original: str, converted: str) -> str:
    letters = [c for c in original if c.isascii() and c.isalpha()]  # ʻ/ʼ count as letters
    if len(letters) > 1 and all(c.isupper() for c in letters):
        return converted.upper()
    if letters and letters[0].isupper():
        return converted[:1].upper() + converted[1:]
    return converted


@lru_cache(maxsize=50_000)
def transliterate_word(word: str) -> str:
    if ROMAN_RE.match(word) or word.lower() in KEEP_LATIN:
        return word
    normalised = _normalise(word)
    lower = normalised.lower()
    if lower in EXCEPTIONS:
        converted = EXCEPTIONS[lower]
        return converted if converted[:1].isupper() else _apply_case(word, converted)
    for stem in sorted(STEMS, key=len, reverse=True):
        if lower.startswith(stem) and lower != stem:
            head = STEMS[stem]
            return _apply_case(
                word, head + _letters(TSIYA_RE.sub("ц", lower[len(stem) :]), head[-1])
            )
    return _apply_case(word, _letters(TSIYA_RE.sub("ц", lower)))


def _convert_plain(text: str) -> str:
    return WORD_RE.sub(lambda m: transliterate_word(m.group(0)), text)


def transliterate(text: str) -> str:
    """Uzbek Latin plain text → Cyrillic; protected chunks (URLs, placeholders…) untouched."""
    if not text or not re.search(r"[A-Za-z]", text):
        return text
    parts: list[str] = []
    last = 0
    for match in PROTECTED_RE.finditer(text):
        parts.append(_convert_plain(text[last : match.start()]))
        parts.append(match.group(0))
        last = match.end()
    parts.append(_convert_plain(text[last:]))
    return "".join(parts)


# --- JSON (map data island, JSON-LD) --------------------------------------------------

JSON_SKIP_KEYS = {
    "@context",
    "@type",
    "@id",
    "url",
    "href",
    "image",
    "logo",
    "sameAs",
    "id",
    "slug",
    "code",
    "kind",
    "region",
    "section",
    "services",
    "inLanguage",
}


def transliterate_json_value(value: Any, key: str = "") -> Any:
    if isinstance(value, str):
        if key in JSON_SKIP_KEYS or value.startswith(("/", "http://", "https://")):
            return value
        return transliterate(value)
    if isinstance(value, list):
        return [transliterate_json_value(item, key) for item in value]
    if isinstance(value, dict):
        return {k: transliterate_json_value(v, k) for k, v in value.items()}
    return value


# --- HTML ---------------------------------------------------------------------------------

TOKEN_RE = re.compile(
    r"(<script\b[^>]*>.*?</script\s*>|<style\b.*?</style\s*>|<!--.*?-->|<[^>]+>)",
    re.IGNORECASE | re.DOTALL,
)
JSON_SCRIPT_RE = re.compile(
    r"""^(<script\b[^>]*\btype=["']application/(?:ld\+)?json["'][^>]*>)(.*?)(</script\s*>)$""",
    re.IGNORECASE | re.DOTALL,
)
TEXT_ATTR_RE = re.compile(
    r"""(\s(?:alt|title|aria-label|placeholder|aria-description)=)(["'])(.*?)\2""",
    re.IGNORECASE | re.DOTALL,
)
META_TEXT_RE = re.compile(
    r"""^<meta\b[^>]*\b(?:name|property)=["'](?:description|og:title|og:description|"""
    r"""og:image:alt|twitter:title|twitter:description|og:site_name)["']""",
    re.IGNORECASE,
)
CONTENT_ATTR_RE = re.compile(r"""(\scontent=)(["'])(.*?)\2""", re.IGNORECASE | re.DOTALL)
SKIP_ELEMENT_RE = re.compile(
    r"""^<(?:code|pre|kbd|samp|textarea)\b|\stranslate=["']no["']|\sdata-no-translit\b""",
    re.IGNORECASE,
)
TAG_NAME_RE = re.compile(r"^</?\s*([a-zA-Z][a-zA-Z0-9-]*)")
VOID_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "source",
    "track",
    "wbr",
}


def _attr_sub(match: re.Match[str]) -> str:
    return f"{match.group(1)}{match.group(2)}{transliterate(match.group(3))}{match.group(2)}"


def _json_script(token: str) -> str:
    match = JSON_SCRIPT_RE.match(token)
    if not match:
        return token
    try:
        data = json.loads(match.group(2))
    except ValueError:
        return token
    payload = json.dumps(transliterate_json_value(data), ensure_ascii=False)
    # keep the payload safe inside <script>
    payload = payload.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return f"{match.group(1)}{payload}{match.group(3)}"


def transliterate_html(html: str) -> str:
    """Transliterate the visible text of an HTML document or fragment.

    Converted: text nodes, alt/title/aria-label/placeholder, description/OpenGraph meta content,
    string values in JSON data islands and JSON-LD. Untouched: markup, URLs, <script>/<style>
    code, comments, <code>/<pre>/<kbd>/<samp>/<textarea>, and every element (with its subtree)
    carrying `translate="no"` or `data-no-translit`.
    """
    out: list[str] = []
    skip: list[str] = []  # open elements whose subtree is skipped (tag names)
    for token in TOKEN_RE.split(html):
        if not token:
            continue
        if token[0] != "<":
            out.append(token if skip else transliterate(token))
            continue
        head = token[:8].lower()
        if head.startswith("<!--") or head.startswith("<style"):
            out.append(token)
            continue
        if head.startswith("<script"):
            out.append(token if skip else _json_script(token))
            continue
        name_match = TAG_NAME_RE.match(token)
        name = name_match.group(1).lower() if name_match else ""
        closing = token.startswith("</")
        self_closing = token.endswith("/>") or name in VOID_TAGS
        if skip:
            if closing and name == skip[-1]:
                skip.pop()
            elif not closing and not self_closing and name == skip[-1]:
                skip.append(name)  # same tag nested inside a skipped subtree
            out.append(token)
            continue
        if closing:
            out.append(token)
            continue
        if SKIP_ELEMENT_RE.search(token):
            if not self_closing:
                skip.append(name)
            out.append(token)
            continue
        token = TEXT_ATTR_RE.sub(_attr_sub, token)
        if name == "meta" and META_TEXT_RE.match(token):
            token = CONTENT_ATTR_RE.sub(_attr_sub, token)
        out.append(token)
    return "".join(out)
