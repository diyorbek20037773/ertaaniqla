"""Map geography of the directory (D-083): region shapes for the map and the centre point of
every district, so institutions without coordinates still show on the map — as one marker per
district with the number of institutions (the Ministry list has no coordinates).

Data: geoBoundaries UZB ADM0/ADM1/ADM2 (OpenStreetMap, ODbL), built by
`scripts/build_geo.py` into `static/geo/uz-regions.json` and `apps/directory/data/districts.json`.
"""

from __future__ import annotations

import json
import re
from functools import cache
from pathlib import Path

DISTRICTS_FILE = Path(__file__).resolve().parent / "data" / "districts.json"

_CITY = re.compile(r"\b(sh|sh\.|shahar|shahri|shaxar|shaxri|city)\b\.?")
_SUFFIX = re.compile(r"\b(tumani|tuman)\b")


def district_key(name: str) -> str:
    """«Andijon sh.» → «andijon#city», «Chilonzor tumani» → «chilonzor» (case, apostrophes and
    the «tumani» suffix do not matter)."""
    text = (name or "").lower().replace("_", " ")
    text = re.sub(r"[ʻʼ'‘’`\"]", "", text)
    city = bool(_CITY.search(text))
    text = _SUFFIX.sub(" ", _CITY.sub(" ", text))
    text = re.sub(r"[^a-z0-9 ]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return f"{text}#city" if city else text


@cache
def district_centres() -> dict[str, list[float]]:
    """`"<region code>|<district key>"` → [lat, lng]."""
    try:
        return dict(json.loads(DISTRICTS_FILE.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return {}


def district_centre(region_code: str, district: str) -> list[float] | None:
    centres = district_centres()
    key = district_key(district)
    found = centres.get(f"{region_code}|{key}")
    if found is None and key.endswith("#city"):  # «Kogon sh» when only the district is known
        found = centres.get(f"{region_code}|{key[:-5]}")
    if found is None and not key.endswith("#city"):
        found = centres.get(f"{region_code}|{key}#city")
    return found
