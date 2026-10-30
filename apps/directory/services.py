"""Query helpers for the directory (fat models / thin views, spec §6)."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from django.db.models import Q, QuerySet

from apps.directory.models import Institution, InstitutionKind, InstitutionSections, Region

KIND_CODES = frozenset(InstitutionKind.values)


def published_institutions() -> QuerySet[Institution]:
    from apps.core.visibility import hidden_sections

    return (
        Institution.objects.filter(is_published=True)
        .exclude(sections__in=hidden_sections())  # D-087: only a hidden section's places
        .select_related("region")
        .prefetch_related("services")
    )


def filter_institutions(
    queryset: QuerySet[Institution] | None = None,
    *,
    region: str = "",
    kind: str = "",
    section: str = "",
    free_only: bool = False,
    query: str = "",
    district: str = "",
) -> QuerySet[Institution]:
    """Apply the public filters. Unknown codes are ignored (never an error). `query` matches the
    name, district or address in either language (the visitor types a village or a number)."""
    qs = published_institutions() if queryset is None else queryset
    if query:
        qs = qs.filter(
            Q(name_uz__icontains=query)
            | Q(name_ru__icontains=query)
            | Q(district_uz__icontains=query)
            | Q(district_ru__icontains=query)
            | Q(address_uz__icontains=query)
            | Q(address_ru__icontains=query)
        )
    if region:
        qs = qs.filter(region__code=region)
    if district:
        qs = qs.filter(district_uz=district)
    if kind in KIND_CODES:
        qs = qs.filter(kind=kind)
    if section in {InstitutionSections.WOMEN, InstitutionSections.CHILDREN}:
        qs = qs.filter(sections__in=[section, InstitutionSections.BOTH])
    if free_only:
        qs = qs.filter(free_under_state_programme=True)
    return qs


def institutions_for_block(value: Mapping[str, Any]) -> list[Institution]:
    """Institutions for the `institution_list` StreamField block."""
    qs = filter_institutions(
        region=str(value.get("region") or ""),
        kind=str(value.get("kind") or ""),
        free_only=bool(value.get("free_only")),
    )
    limit = int(value.get("limit") or 20)
    return list(qs[:limit])


def region_list() -> list[Region]:
    return list(Region.objects.all())


def map_payload(institutions: list[Institution], language: str) -> list[dict[str, Any]]:
    """Marker data for map.js (only institutions with coordinates)."""
    from django.utils.translation import gettext as _

    free_label = _("Free under the state programme")
    payload: list[dict[str, Any]] = []
    for item in institutions:
        if item.lat is None or item.lng is None:
            continue
        payload.append(
            {
                "id": item.pk,
                "name": item.name_for(language),
                "kind": str(item.get_kind_display()),
                "address": ", ".join(
                    part
                    for part in (
                        item.region.name_for(language),
                        item.district_for(language),
                        item.address_for(language),
                    )
                    if part
                ),
                "phone": item.phone,
                "lat": float(item.lat),
                "lng": float(item.lng),
                "sections": item.sections,
                "free": item.free_under_state_programme,
                "free_label": free_label,
            }
        )
    return payload


def map_overview(
    queryset: QuerySet[Institution], language: str, *, region: str = "", district: str = ""
) -> dict[str, Any]:
    """Data of the directory map (D-083), from the list filtered by everything but the place:
    per region the number of institutions (the colour of the region shape), per district its
    centre and number (one marker per district — the Ministry list has no coordinates), and the
    institutions that do have coordinates. Labels are in the page language."""
    from django.db.models import Count
    from django.utils.translation import ngettext

    from apps.directory.geo import district_centre

    def label(count: int) -> str:
        return ngettext("%(count)s institution", "%(count)s institutions", count) % {"count": count}

    names = {r.code: r.name_for(language) for r in Region.objects.all()}
    regions = {
        row["region__code"]: {
            "name": names.get(row["region__code"], ""),
            "count": row["n"],
            "label": label(row["n"]),
        }
        for row in queryset.values("region__code").annotate(n=Count("id"))
    }
    for code, name in names.items():
        regions.setdefault(code, {"name": name, "count": 0, "label": label(0)})
    districts = []
    rows = queryset.values("region__code", "district_uz", "district_ru").annotate(n=Count("id"))
    for row in rows.order_by("region__code", "district_uz"):
        centre = district_centre(row["region__code"], row["district_uz"])
        if centre is None or not row["district_uz"]:
            continue
        ru = language == "ru" and row["district_ru"]
        shown = row["district_ru"] if ru else row["district_uz"]
        districts.append(
            {
                "region": row["region__code"],
                "district": row["district_uz"],
                "name": shown,
                "lat": centre[0],
                "lng": centre[1],
                "count": row["n"],
                "label": label(row["n"]),
            }
        )
    exact = list(queryset.exclude(lat=None).exclude(lng=None)[:500])
    return {
        "regions": regions,
        "districts": districts,
        "points": map_payload(exact, language),
        "selected": {"region": region, "district": district},
    }


# --- screening route (D-105): the visitor picks a region and a district, nothing else -------------
ROUTE_DISTRICT_PLACES = "district_polyclinics"
ROUTE_REGION_BRANCH = "region_branch"
ROUTE_STEP_KINDS = (InstitutionKind.POLYCLINIC, InstitutionKind.ONCO_ROOM)


def route_districts(region: str, language: str) -> list[tuple[str, str]]:
    """(value, label) of the districts of `region` that have a step-one place. The value is the
    Uzbek name — the key every institution carries; the label follows the page language."""
    if not region:
        return []
    rows = (
        filter_institutions(region=region, section=InstitutionSections.WOMEN)
        .filter(kind__in=ROUTE_STEP_KINDS)
        .exclude(district_uz="")
        .values_list("district_uz", "district_ru")
        .distinct()
    )
    names = {uz: (ru if language == "ru" and ru else uz) for uz, ru in rows}
    return sorted(names.items(), key=lambda item: item[1].lower())


def route_places(places: str, region: str, district: str, limit: int = 12) -> dict[str, Any]:
    """Institutions for one step of the screening route: the district's polyclinics (where the
    samples are taken) or the region's Mother & Child Health Centre branch (colposcopy). When the
    region has no branch on record yet, every branch is listed (`fallback`)."""
    women = filter_institutions(section=InstitutionSections.WOMEN)
    if places == ROUTE_DISTRICT_PLACES:
        if not (region and district):
            return {"items": [], "fallback": False}
        qs = filter_institutions(women, region=region, district=district).filter(
            kind__in=ROUTE_STEP_KINDS
        )
        return {"items": list(qs.order_by("kind", "name_uz")[:limit]), "fallback": False}
    if places == ROUTE_REGION_BRANCH:
        if not region:
            return {"items": [], "fallback": False}
        branches = women.filter(colposcopy_branch=True)
        local = list(branches.filter(region__code=region).order_by("name_uz")[:limit])
        if local:
            return {"items": local, "fallback": False}
        return {"items": _nearest(branches, region, district), "fallback": True}
    return {"items": [], "fallback": False}


def _nearest(
    branches: QuerySet[Institution], region: str, district: str, count: int = 2
) -> list[Institution]:
    """The branches closest to the district (or the region) when the region has none on record:
    two cards instead of every branch in the country (a long list on a phone). The registry has
    no coordinates, so a place without its own falls back to its district's centre (D-083)."""
    from apps.directory.geo import district_centre, district_centres

    here: list[float] | None = district_centre(region, district) if district else None
    if here is None:
        points = [c for key, c in district_centres().items() if key.startswith(f"{region}|")]
        if points:
            here = [
                sum(p[0] for p in points) / len(points),
                sum(p[1] for p in points) / len(points),
            ]

    def point(place: Institution) -> list[float] | None:
        if place.lat is not None and place.lng is not None:
            return [float(place.lat), float(place.lng)]
        return district_centre(place.region.code, place.district_uz)

    located = [(place, point(place)) for place in branches]
    known = [(place, p) for place, p in located if p is not None]
    if here is None or not known:
        return list(branches.order_by("region__sort_order", "name_uz")[:count])
    origin = here

    def distance(item: tuple[Institution, list[float]]) -> float:
        return (item[1][0] - origin[0]) ** 2 + (item[1][1] - origin[1]) ** 2

    return [place for place, _p in sorted(known, key=distance)[:count]]


# ---------------------------------------------------------------------------------------------
# Registry text (expert review, D-106)
# ---------------------------------------------------------------------------------------------
_DOUBLE_QUOTES = frozenset('"“”„')
_OPENS_AFTER = frozenset("([«/-,;:")
TIDY_FIELDS = ("name_uz", "name_ru", "address_uz", "address_ru")


def _dropped(chars: list[str], i: int) -> str:
    """An unpaired quote goes; between two words it leaves a space («Fayzobod"koʻchasi»)."""
    if chars[i] not in _DOUBLE_QUOTES:
        return chars[i]
    glued = 0 < i < len(chars) - 1 and chars[i - 1].isalnum() and chars[i + 1].isalnum()
    return " " if glued else ""


def tidy_quotes(text: str) -> str:
    """The registry's straight quotes → «», unpaired ones dropped:
    `"Kelovchi" oilaviy shifokor punkti"` → `«Kelovchi» oilaviy shifokor punkti`,
    `"26- OP "Uyrot"` → `26- OP «Uyrot»`, `MFY"Uxum"` → `MFY «Uxum»`,
    `"Yunusobod tumani,"Amir Temur" kuchasi"` → `Yunusobod tumani, «Amir Temur» kuchasi`."""
    text = text.replace("''", '"')
    if not _DOUBLE_QUOTES.intersection(text):
        return text
    text = text.replace("«", '"').replace("»", '"')  # «"A. Dosnazarov»" — mixed in one field
    inner = [c for c in text[1:-1] if c in _DOUBLE_QUOTES]
    if len(text) > 1 and {text[0], text[-1]} <= _DOUBLE_QUOTES and inner and len(inner) % 2 == 0:
        text = text[1:-1]  # the whole field wrapped in quotes around quoted names inside
    chars = list(text)
    marks: dict[int, str] = {}
    opened: list[int] = []
    for i, char in enumerate(chars):
        if char not in _DOUBLE_QUOTES:
            continue
        before = chars[i - 1] if i else " "
        after = chars[i + 1] if i + 1 < len(chars) else " "
        if (before.isspace() or before in _OPENS_AFTER) and not after.isspace():
            opened.append(i)
        elif opened:
            marks[opened.pop()] = "«"
            marks[i] = "»"
        elif after.isalnum():
            opened.append(i)  # «MFY"Uxum"»: glued to the word before it
    out = "".join(marks.get(i, _dropped(chars, i)) for i in range(len(chars)))
    out = re.sub(r"(?<=[\w,;:])«", " «", out)
    out = re.sub(r"»(?=\w)", "» ", out)
    out = re.sub(r"«\s+", "«", re.sub(r"\s+»", "»", out))
    return re.sub(r"\s{2,}", " ", out).strip()
