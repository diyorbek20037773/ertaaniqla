"""`manage.py import_institutions data/institutions.csv [--dry-run] [--source dmed]`

Upserts institutions from a UTF-8 CSV (spec §4.3, F11). Rows are matched by `external_id`
(when given) else by (name_uz, region). Invalid rows are reported and skipped; the command
never deletes anything. Columns (header row required, order free):

external_id, name_uz, name_ru, kind, region, district_uz, district_ru, address_uz, address_ru,
phone, hours_uz, hours_ru, website, lat, lng, free, services, sections, verified_at

`kind` = svp|polyclinic|onco_room|mother_child_centre|oncology_centre|paediatric_oncohaematology|
psych_support|ngo; `region` = Region.code; `free` = 1/0/yes/no; `services` = codes separated by
";" (mammography;ultrasound;…); `sections` = women|children|both; `verified_at` = YYYY-MM-DD.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.directory.models import (
    Institution,
    InstitutionKind,
    InstitutionSections,
    Region,
    Service,
)

REQUIRED = ("name_uz", "name_ru", "kind", "region")
TRUE_VALUES = {"1", "yes", "true", "ha", "да", "y"}


@dataclass
class ImportReport:
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"created={self.created} updated={self.updated} skipped={self.skipped} "
            f"errors={len(self.errors)}"
        )


def _decimal(value: str) -> Decimal | None:
    value = (value or "").strip().replace(",", ".")
    if not value:
        return None
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"bad number {value!r}") from exc


def _date(value: str) -> date | None:
    value = (value or "").strip()
    return date.fromisoformat(value) if value else None


def import_rows(rows: list[dict[str, str]], source: str, dry_run: bool = False) -> ImportReport:
    report = ImportReport()
    regions = {r.code: r for r in Region.objects.all()}
    services = {s.code: s for s in Service.objects.all()}
    kinds = set(InstitutionKind.values)
    sections = set(InstitutionSections.values)
    with transaction.atomic():
        for number, raw in enumerate(rows, start=2):
            row = {k.strip().lower(): (v or "").strip() for k, v in raw.items() if k}
            missing = [c for c in REQUIRED if not row.get(c)]
            if missing:
                report.errors.append(f"row {number}: missing {', '.join(missing)}")
                report.skipped += 1
                continue
            if row["kind"] not in kinds:
                report.errors.append(f"row {number}: unknown kind {row['kind']!r}")
                report.skipped += 1
                continue
            region = regions.get(row["region"])
            if region is None:
                report.errors.append(f"row {number}: unknown region {row['region']!r}")
                report.skipped += 1
                continue
            try:
                lat, lng = _decimal(row.get("lat", "")), _decimal(row.get("lng", ""))
                verified_at = _date(row.get("verified_at", ""))
            except ValueError as exc:
                report.errors.append(f"row {number}: {exc}")
                report.skipped += 1
                continue
            section = row.get("sections") or InstitutionSections.BOTH
            if section not in sections:
                report.errors.append(f"row {number}: unknown sections {section!r}")
                report.skipped += 1
                continue
            service_codes = [c.strip() for c in row.get("services", "").split(";") if c.strip()]
            unknown = [c for c in service_codes if c not in services]
            if unknown:
                report.errors.append(f"row {number}: unknown services {', '.join(unknown)}")
                report.skipped += 1
                continue
            values: dict[str, Any] = {
                "name_uz": row["name_uz"],
                "name_ru": row["name_ru"],
                "kind": row["kind"],
                "region": region,
                "district_uz": row.get("district_uz", ""),
                "district_ru": row.get("district_ru", ""),
                "address_uz": row.get("address_uz", ""),
                "address_ru": row.get("address_ru", ""),
                "phone": row.get("phone", ""),
                "hours_uz": row.get("hours_uz", ""),
                "hours_ru": row.get("hours_ru", ""),
                "website": row.get("website", ""),
                "lat": lat,
                "lng": lng,
                "free_under_state_programme": row.get("free", "").lower() in TRUE_VALUES,
                "sections": section,
                "verified_at": verified_at,
                "external_source": source,
            }
            external_id = row.get("external_id", "")
            lookup: dict[str, Any]
            if external_id:
                lookup = {"external_id": external_id, "external_source": source}
            else:
                lookup = {"name_uz": row["name_uz"], "region": region}
            existing = Institution.objects.filter(**lookup).first()
            if existing is None:
                institution = Institution(external_id=external_id, **values)
                report.created += 1
            else:
                institution = existing
                for key, value in values.items():
                    setattr(institution, key, value)
                report.updated += 1
            if not dry_run:
                institution.full_clean(exclude=["services"])
                institution.save()
                institution.services.set([services[c] for c in service_codes])
        if dry_run:
            transaction.set_rollback(True)
    return report


class Command(BaseCommand):
    help = "Import/update institutions from a CSV file (see module docstring for columns)."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("csv_path")
        parser.add_argument("--source", default="csv", help="external_source label (e.g. dmed)")
        parser.add_argument("--dry-run", action="store_true", help="validate only, write nothing")

    def handle(self, *args: Any, **options: Any) -> None:
        path = Path(options["csv_path"])
        if not path.exists():
            raise CommandError(f"file not found: {path}")
        with path.open(encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh))
        report = import_rows(rows, source=options["source"], dry_run=options["dry_run"])
        for error in report.errors:
            self.stderr.write(error)
        style = self.style.WARNING if report.errors else self.style.SUCCESS
        prefix = "DRY RUN " if options["dry_run"] else ""
        self.stdout.write(style(f"{prefix}import_institutions: {report.summary()}"))
