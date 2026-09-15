"""Query helpers for the directory (fat models / thin views, spec §6)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from django.db.models import QuerySet

from apps.directory.models import Institution, InstitutionKind, InstitutionSections, Region

KIND_CODES = frozenset(InstitutionKind.values)


def published_institutions() -> QuerySet[Institution]:
    return (
        Institution.objects.filter(is_published=True)
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
) -> QuerySet[Institution]:
    """Apply the public filters. Unknown codes are ignored (never an error)."""
    qs = published_institutions() if queryset is None else queryset
    if region:
        qs = qs.filter(region__code=region)
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
