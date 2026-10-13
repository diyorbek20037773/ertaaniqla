"""Build the directory map geography (D-083) from geoBoundaries (OpenStreetMap, ODbL):

    uv run python scripts/build_geo.py <ADM0.geojson> <ADM1.geojson> <ADM2.geojson> <districts.csv>

* static/geo/uz-regions.json — the 14 regions (property `code` = Region.code) and the country
  outline (code "UZ"), coordinates rounded to 3 decimals and thinned for the 3G budget;
* apps/directory/data/districts.json — centre of every district of the institution list
  (`"<region>|<district key>"` → [lat, lng]); district names are matched to the Russian-style
  Latin names of geoBoundaries (Chilonzor ↔ Chilanzar) and listed when nothing fits.
"""

from __future__ import annotations

import csv
import difflib
import itertools
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from apps.directory.geo import district_key  # noqa: E402

ISO = {
    "UZ-AN": "andijan",
    "UZ-NG": "namangan",
    "UZ-FA": "fergana",
    "UZ-QR": "karakalpakstan",
    "UZ-XO": "khorezm",
    "UZ-NW": "navoi",
    "UZ-SU": "surkhandarya",
    "UZ-SA": "samarkand",
    "UZ-TO": "tashkent",
    "UZ-SI": "syrdarya",
    "UZ-JI": "jizzakh",
    "UZ-BU": "bukhara",
    "UZ-QA": "kashkadarya",
    "UZ-TK": "tashkent-city",
}
# names that no spelling rule can pair (Uzbek → geoBoundaries)
ALIASES = {
    "jizzax#city": "dzhizak#city",
    "jizzax": "sharof rashidov",
    "qarshi": "karshi",
    "toshkent": "tashkent",
    "termiz": "termez",
    "nukus": "nukus",
    "taxiatosh#city": "nukus",
    "yangi namangan": "namangan#city",
    "bandixon": "kizirik",
    "gozgon#city": "nurata",
    "bozatau": "kungrad",
    "tuproqqala": "khazarasp",
    "qongirot": "kungrad",
    "xozarasp": "khazarasp",
    "bulungur": "bulungur",
    "sux": "sokh",
    "yozyovon": "yazyavan",
    "shirin": "shirin#city",
    "yangiyer": "yangiyer#city",
    "bektemir": "bektemir",
    "yangixayot": "sergeli",
    "davlatobod": "namangan#city",
    "olmalik#city": "almalik#city",
    "chirchik#city": "chirchik#city",
    "nurafshon": "nurafshon#city",
    "angren": "angren#city",
    "uchtepa": "uchtepa",
    "mirobod": "mirabad",
    "sayxunobod": "saykhunabad",
}


def rings(geometry: dict) -> list[list[list[float]]]:
    if geometry["type"] == "Polygon":
        return [geometry["coordinates"][0]]
    return [poly[0] for poly in geometry["coordinates"]]


def thin(ring: list[list[float]], step: float = 0.012) -> list[list[float]]:
    out: list[list[float]] = []
    for lng, lat in ring:
        point = [round(lng, 3), round(lat, 3)]
        if not out or abs(point[0] - out[-1][0]) + abs(point[1] - out[-1][1]) >= step:
            out.append(point)
    if out[0] != out[-1]:
        out.append(out[0])
    return out


def thin_geometry(geometry: dict) -> dict:
    polys = [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
    kept = []
    for poly in polys:
        outer = thin(poly[0])
        if len(outer) >= 4:
            kept.append([outer] + [thin(r) for r in poly[1:] if len(thin(r)) >= 4])
    return {"type": "MultiPolygon", "coordinates": kept}


def centroid(ring: list[list[float]]) -> tuple[float, float, float]:
    area = cx = cy = 0.0
    for (x1, y1), (x2, y2) in itertools.pairwise(ring):
        cross = x1 * y2 - x2 * y1
        area += cross
        cx += (x1 + x2) * cross
        cy += (y1 + y2) * cross
    area /= 2
    if not area:
        return ring[0][0], ring[0][1], 0.0
    return cx / (6 * area), cy / (6 * area), abs(area)


def inside(x: float, y: float, ring: list[list[float]]) -> bool:
    result = False
    for (x1, y1), (x2, y2) in itertools.pairwise(ring):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            result = not result
    return result


def russian_style(key: str) -> list[str]:
    """Spellings of an Uzbek Latin key the way geoBoundaries writes it."""
    base, city = (key[:-5], "#city") if key.endswith("#city") else (key, "")
    variants = {base}
    text = base
    for old, new in (("sh", "§"), ("ch", "¢"), ("x", "kh"), ("q", "k"), ("j", "dzh"), ("yo", "ya")):
        text = text.replace(old, new)
    text = text.replace("§", "sh").replace("¢", "ch")
    variants.add(text)
    variants.add(text.replace("o", "a"))
    variants.add(text.replace("dzh", "j").replace("o", "a"))
    variants.add(base.replace("o", "u"))
    return [v + city for v in variants]


def main(adm0: Path, adm1: Path, adm2: Path, districts_csv: Path) -> None:
    a0 = json.loads(adm0.read_text(encoding="utf-8"))
    a1 = json.loads(adm1.read_text(encoding="utf-8"))
    a2 = json.loads(adm2.read_text(encoding="utf-8"))

    features = []
    region_rings: dict[str, list] = {}
    for feature in a1["features"]:
        code = ISO[feature["properties"]["shapeISO"]]
        region_rings[code] = rings(feature["geometry"])
        features.append(
            {
                "type": "Feature",
                "properties": {"code": code},
                "geometry": thin_geometry(feature["geometry"]),
            }
        )
    for feature in a0["features"]:
        features.append(
            {
                "type": "Feature",
                "properties": {"code": "UZ"},
                "geometry": thin_geometry(feature["geometry"]),
            }
        )
    out_regions = ROOT / "static" / "geo" / "uz-regions.json"
    out_regions.parent.mkdir(parents=True, exist_ok=True)
    out_regions.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":")),
        encoding="utf-8",
    )

    # geoBoundaries districts: centre + region (the centre's region polygon; Tashkent city wins)
    shapes: dict[str, dict[str, list[float]]] = {}
    for feature in a2["features"]:
        name = feature["properties"]["shapeName"].replace("а", "a")  # one Cyrillic «а» in the data
        best = max((centroid(r) for r in rings(feature["geometry"])), key=lambda c: c[2])
        lng, lat = best[0], best[1]
        codes = [c for c, rs in region_rings.items() if any(inside(lng, lat, r) for r in rs)]
        code = "tashkent-city" if "tashkent-city" in codes else (codes[0] if codes else "")
        key = district_key(name)
        shapes.setdefault(code, {})[key] = [round(lat, 4), round(lng, 4)]

    # border districts whose centre falls outside their region polygon in the source data
    everywhere = {key: point for pool in shapes.values() for key, point in pool.items()}
    wanted = sorted(
        {
            (r["region"], r["district_uz"])
            for r in csv.DictReader(districts_csv.open(encoding="utf-8"))
        }
    )
    result: dict[str, list[float]] = {}
    missing = []
    for region, district in wanted:
        key = district_key(district)
        pool = shapes.get(region, {})
        target = ALIASES.get(key)
        found = (pool.get(target) or everywhere.get(target)) if target else None
        if found is None:
            scored = []
            for variant in russian_style(key):
                for name, point in pool.items():
                    if variant.endswith("#city") != name.endswith("#city"):
                        continue
                    scored.append(
                        (difflib.SequenceMatcher(None, variant, name).ratio(), name, point)
                    )
            scored.sort(reverse=True)
            if scored and scored[0][0] >= 0.72:
                found = scored[0][2]
            elif key.endswith("#city"):  # a town inside its district
                plain = [
                    (difflib.SequenceMatcher(None, v[:-5], n).ratio(), p)
                    for v in russian_style(key)
                    for n, p in pool.items()
                ]
                plain.sort(reverse=True)
                found = plain[0][1] if plain and plain[0][0] >= 0.72 else None
        if found is None:
            missing.append(f"{region}|{district}")
            continue
        result[f"{region}|{key}"] = found
    out_districts = ROOT / "apps" / "directory" / "data" / "districts.json"
    out_districts.parent.mkdir(parents=True, exist_ok=True)
    out_districts.write_text(
        json.dumps(result, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8"
    )
    print(f"regions: {len(features)} features, {out_regions.stat().st_size // 1024} KB")
    print(f"districts: {len(result)} of {len(wanted)} matched; missing: {missing}")


if __name__ == "__main__":
    main(*(Path(a) for a in sys.argv[1:5]))
