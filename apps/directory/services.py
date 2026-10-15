"""Query helpers for the directory (fat models / thin views, spec §6)."""

from __future__ import annotations

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
