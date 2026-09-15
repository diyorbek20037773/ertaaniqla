"""Uzbek Cyrillic ↔ Latin transliteration for search queries (spec §7).

Deliberately simple: good enough to make «скрининг» find "Skrining" and "koʻkrak" find
«кўкрак». Russian text transliterates with the same table (ш → sh, ч → ch, …).
"""

from __future__ import annotations

import re

APOSTROPHES = "ʻʼ'’‘`´"
MODIFIER = "ʻ"  # U+02BB, the letter used in content (ADR-0003)

_CYR_TO_LAT: list[tuple[str, str]] = [
    ("ё", "yo"),
    ("ю", "yu"),
    ("я", "ya"),
    ("ц", "ts"),
    ("ч", "ch"),
    ("ш", "sh"),
    ("щ", "sh"),
    ("ў", "oʻ"),
    ("ғ", "gʻ"),
    ("қ", "q"),
    ("ҳ", "h"),
    ("х", "x"),
    ("ж", "j"),
    ("э", "e"),
    ("а", "a"),
    ("б", "b"),
    ("в", "v"),
    ("г", "g"),
    ("д", "d"),
    ("е", "e"),
    ("з", "z"),
    ("и", "i"),
    ("й", "y"),
    ("к", "k"),
    ("л", "l"),
    ("м", "m"),
    ("н", "n"),
    ("о", "o"),
    ("п", "p"),
    ("р", "r"),
    ("с", "s"),
    ("т", "t"),
    ("у", "u"),
    ("ф", "f"),
    ("ъ", "ʼ"),
    ("ь", ""),
    ("ы", "i"),
]

_LAT_TO_CYR: list[tuple[str, str]] = [
    ("oʻ", "ў"),
    ("gʻ", "ғ"),
    ("sh", "ш"),
    ("ch", "ч"),
    ("yo", "ё"),
    ("yu", "ю"),
    ("ya", "я"),
    ("ts", "ц"),
    ("ng", "нг"),
    ("a", "а"),
    ("b", "б"),
    ("d", "д"),
    ("e", "е"),
    ("f", "ф"),
    ("g", "г"),
    ("h", "ҳ"),
    ("i", "и"),
    ("j", "ж"),
    ("k", "к"),
    ("l", "л"),
    ("m", "м"),
    ("n", "н"),
    ("o", "о"),
    ("p", "п"),
    ("q", "қ"),
    ("r", "р"),
    ("s", "с"),
    ("t", "т"),
    ("u", "у"),
    ("v", "в"),
    ("x", "х"),
    ("y", "й"),
    ("z", "з"),
    ("ʼ", "ъ"),
    ("c", "к"),
]

_CYRILLIC = re.compile(r"[Ѐ-ӿ]")
_LATIN = re.compile(r"[A-Za-z]")


def normalise_apostrophes(text: str) -> str:
    """Every apostrophe-like character → U+02BB, the form used in content."""
    for ch in APOSTROPHES:
        text = text.replace(ch, MODIFIER)
    return text


def _apply(text: str, table: list[tuple[str, str]]) -> str:
    out = []
    i = 0
    lower = text.lower()
    while i < len(lower):
        for src, dst in table:
            if lower.startswith(src, i):
                out.append(dst)
                i += len(src)
                break
        else:
            out.append(lower[i])
            i += 1
    return "".join(out)


def cyr_to_lat(text: str) -> str:
    return _apply(text, _CYR_TO_LAT)


def lat_to_cyr(text: str) -> str:
    return _apply(normalise_apostrophes(text), _LAT_TO_CYR)


def has_cyrillic(text: str) -> bool:
    return bool(_CYRILLIC.search(text))


def has_latin(text: str) -> bool:
    return bool(_LATIN.search(text))


def script_variants(text: str) -> list[str]:
    """The query plus its transliteration into the other script (deduplicated, in order)."""
    text = normalise_apostrophes(text.strip())
    variants = [text]
    if has_cyrillic(text):
        variants.append(cyr_to_lat(text))
    if has_latin(text):
        variants.append(lat_to_cyr(text))
    seen: set[str] = set()
    result = []
    for item in variants:
        key = item.lower()
        if item and key not in seen:
            seen.add(key)
            result.append(item)
    return result
