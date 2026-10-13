"""Convert the Ministry of Health institution list (``ssv_organization*.xlsx``, columns viloyat,
tuman, nomi, manzil, class) into the CSV that ``manage.py import_institutions`` reads.

    uv run python scripts/ssv_to_csv.py "docs/ssv_organization (7).xlsx" data/institutions.ssv.csv

What it does (D-082):
* region names → Region codes; the 14 regions of the file map one to one;
* names / addresses written in Cyrillic Uzbek are transliterated to Latin for ``*_uz`` (the
  ``/oz/`` site transliterates back); ``*_ru`` keeps the Cyrillic original (or a Cyrillic
  transliteration of a Latin original) — the file has no Russian names;
* ``class`` → institution kind; class 4 (sanitary-epidemiological services) and the class 7
  entries that are not places for a check-up (ambulance, infectious / TB / narcology hospitals,
  administrations, laboratories …) are left out — the directory answers «where can I be
  screened»;
* a stable ``external_id`` (hash of region, district, name, address) so a newer file updates
  the same rows instead of duplicating them.
"""

from __future__ import annotations

import csv
import hashlib
import re
import sys
from pathlib import Path

import openpyxl

REGIONS = {
    "toshkent sh": "tashkent-city",
    "toshkent": "tashkent",
    "andijon": "andijan",
    "buxoro": "bukhara",
    "farg‘ona": "fergana",
    "fargʻona": "fergana",
    "farg'ona": "fergana",
    "jizzax": "jizzakh",
    "qashqadaryo": "kashkadarya",
    "xorazm": "khorezm",
    "namangan": "namangan",
    "navoiy": "navoi",
    "samarqand": "samarkand",
    "surxondaryo": "surkhandarya",
    "sirdaryo": "syrdarya",
    "qr": "karakalpakstan",
}

CYR = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "yo",
    "ж": "j",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "x",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "sh",
    "ъ": "ʼ",
    "ы": "i",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
    "ў": "oʻ",
    "қ": "q",
    "ғ": "gʻ",
    "ҳ": "h",
}
VOWELS = set("аеёиоуэюяўaeiou")


def cyr_to_lat(text: str) -> str:
    """Uzbek Cyrillic → Latin (official 1995 alphabet); Latin text passes through."""
    out = []
    for i, ch in enumerate(text):
        low = ch.lower()
        if low not in CYR:
            out.append(ch)
            continue
        lat = CYR[low]
        prev = text[i - 1].lower() if i else " "
        if low == "е" and (not prev.isalpha() or prev in VOWELS or prev in "ъь"):
            lat = "ye"  # word-initial / after a vowel
        if ch.isupper() and lat:
            # ОШП → OSHP inside an all-caps abbreviation (the /oz/ site turns it back into ОШП),
            # Шифохона → Shifoxona in a word
            nxt = text[i + 1] if i + 1 < len(text) else ""
            prv = text[i - 1] if i else ""
            caps = (nxt.isalpha() and nxt.isupper()) or (prv.isalpha() and prv.isupper())
            lat = lat.upper() if caps else lat[0].upper() + lat[1:]
        out.append(lat)
    return "".join(out)


def has_cyrillic(text: str) -> bool:
    return bool(re.search(r"[А-Яа-яЁёЎўҚқҒғҲҳ]", text))


def clean(value: object) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text.replace("ʼ", "ʼ").replace("‘", "ʻ").replace("’", "ʼ")


def norm(text: str) -> str:
    """Lower-case Latin form for keyword matching (works for both scripts)."""
    return cyr_to_lat(text).lower().replace("ʻ", "'").replace("ʼ", "'")


# class 7 keeps only places where a person can be examined
KEEP_7 = re.compile(
    r"tibbiyot birlashma|poliklinik|\boshp\b|\bqvp\b|\bkvp\b|\bop\b|\bkop\b|\bktmp\b|oilaviy|"
    r"tug'ruq|tugruq|perinatal|ona va bola|onkolog|ayollar|ko'p tarmoqli|kup tarmokli|"
    r"oilaviy shifokor|shifokorlik punkti|markaziy shif|tuman shifox|klinik shifox|\bttb\b|"
    r"\bqpp\b|tibbiyot punkti"
)
# never a place for a check-up, whatever the class
DROP = re.compile(
    r"boshqarma|tez tibbiy|shoshilinch|yuqumli|yukumli|ftiziatr|\bsil\b|narkolog|psixiatr|"
    r"laborator|universitet|institut|sanatori|qon quyish|qon xizmati|sud-tibbiy|dezinfeks|ulat|"
    r"tez yordam|stantsiya|teri-tanosil|dermatovenerolog|stomatolog|omborxona|byuro"
)


def kind_for(cls: int, name: str) -> str | None:
    n = norm(name)
    if cls == 4 or DROP.search(n) or (cls == 7 and not KEEP_7.search(n)):
        return None
    if "onkolog" in n:
        return "oncology_centre"
    if re.search(r"tug'ruq|tugruq|perinatal|ona va bola", n):
        return "mother_child_centre"
    if cls == 1 or re.search(
        r"\boshp\b|\bqvp\b|\bkvp\b|\bqpp\b|shifokorlik punkti|tibbiyot punkti", n
    ):
        return "svp"
    if cls in (2, 3) or re.search(r"poliklinik|\bop\b|\bkop\b|\bktmp\b|\bttb\b|birlashma", n):
        return "polyclinic"
    return "hospital"


def sections_for(name: str) -> str:
    n = norm(name)
    if "bolalar" in n:
        return "children"
    if re.search(r"tug'ruq|tugruq|perinatal|ayollar|ginekolog", n):
        return "women"
    return "both"


def convert(xlsx: Path, out: Path) -> dict[str, int]:
    from apps.core.uzcyrl import transliterate  # Latin → Cyrillic for *_ru

    wb = openpyxl.load_workbook(xlsx, read_only=True, data_only=True)
    ws = wb.worksheets[0]
    stats = {"rows": 0, "kept": 0, "dropped_class4": 0, "dropped_other": 0, "unknown_region": 0}
    seen: set[str] = set()
    fields = [
        "external_id",
        "name_uz",
        "name_ru",
        "kind",
        "region",
        "district_uz",
        "district_ru",
        "address_uz",
        "address_ru",
        "phone",
        "hours_uz",
        "hours_ru",
        "website",
        "lat",
        "lng",
        "free",
        "services",
        "sections",
        "verified_at",
    ]
    with out.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in ws.iter_rows(min_row=2, values_only=True):
            region_name, district, name, address, cls = (clean(v) for v in row[:5])
            if not name:
                continue
            stats["rows"] += 1
            region = REGIONS.get(region_name.lower())
            if region is None:
                stats["unknown_region"] += 1
                continue
            kind = kind_for(int(float(cls or 0)), name)
            if kind is None:
                stats["dropped_class4" if cls in ("4", "4.0") else "dropped_other"] += 1
                continue
            key = "|".join((region, district, name, address)).lower()
            external_id = "SSV-" + hashlib.sha1(key.encode()).hexdigest()[:12]
            if external_id in seen:
                continue
            seen.add(external_id)

            def both(text: str) -> tuple[str, str]:
                if has_cyrillic(text):
                    return cyr_to_lat(text), text
                return text, transliterate(text)

            name_uz, name_ru = both(name)
            district_uz, district_ru = both(district)
            address_uz, address_ru = both(address)
            writer.writerow(
                {
                    "external_id": external_id,
                    "name_uz": name_uz[:200],
                    "name_ru": name_ru[:200],
                    "kind": kind,
                    "region": region,
                    "district_uz": district_uz[:120],
                    "district_ru": district_ru[:120],
                    "address_uz": address_uz[:300],
                    "address_ru": address_ru[:300],
                    "sections": sections_for(name),
                }
            )
            stats["kept"] += 1
    return stats


if __name__ == "__main__":
    import os

    import django

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")
    django.setup()
    print(convert(Path(sys.argv[1]), Path(sys.argv[2])))
