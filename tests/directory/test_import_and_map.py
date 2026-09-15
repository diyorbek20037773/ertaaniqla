"""CSV import command (F11) and the directory page's HTMX partial + map data."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from django.core.management import call_command
from django.test import Client

from apps.directory.management.commands.import_institutions import import_rows
from apps.directory.models import DirectoryPage, Institution

pytestmark = pytest.mark.django_db

SAMPLE = Path(__file__).resolve().parents[2] / "data" / "institutions.sample.csv"


def test_sample_csv_imports_and_is_idempotent(capsys) -> None:
    call_command("import_institutions", str(SAMPLE))
    assert Institution.objects.count() == 12
    out = capsys.readouterr().out
    assert "created=12 updated=0" in out
    call_command("import_institutions", str(SAMPLE))
    assert Institution.objects.count() == 12
    assert "created=0 updated=12" in capsys.readouterr().out
    inst = Institution.objects.get(external_id="SAMPLE-003")
    assert inst.services.count() == 4 and inst.free_under_state_programme
    assert str(inst.verified_at) == "2026-09-01"


def test_dry_run_writes_nothing(capsys) -> None:
    call_command("import_institutions", str(SAMPLE), "--dry-run")
    assert Institution.objects.count() == 0
    assert "DRY RUN" in capsys.readouterr().out


def test_invalid_rows_are_reported_not_imported() -> None:
    rows = [
        {"name_uz": "A", "name_ru": "А", "kind": "bogus", "region": "tashkent-city"},
        {"name_uz": "B", "name_ru": "Б", "kind": "svp", "region": "nowhere"},
        {"name_uz": "C", "name_ru": "В", "kind": "svp", "region": "fergana", "lat": "x"},
        {"name_uz": "D", "name_ru": "Г", "kind": "svp", "region": "fergana", "services": "zzz"},
        {"name_uz": "", "name_ru": "Д", "kind": "svp", "region": "fergana"},
        {"name_uz": "E", "name_ru": "Е", "kind": "ngo", "region": "fergana", "sections": "all"},
        {"name_uz": "OK", "name_ru": "ОК", "kind": "svp", "region": "fergana", "free": "yes"},
    ]
    report = import_rows(rows, source="test")
    assert report.created == 1 and report.skipped == 6 and len(report.errors) == 6
    assert Institution.objects.get(name_uz="OK").free_under_state_programme
    # match by name+region when no external id
    report = import_rows(rows[-1:], source="test")
    assert report.updated == 1 and Institution.objects.count() == 1


def test_missing_file_errors() -> None:
    from django.core.management.base import CommandError

    with pytest.raises(CommandError):
        call_command("import_institutions", "nope.csv")


def test_directory_htmx_partial_and_map_data(seeded, client: Client) -> None:
    call_command("import_institutions", str(SAMPLE))
    page = DirectoryPage.objects.get(locale__language_code="uz")
    html = client.get(page.url).content.decode()
    assert 'id="map"' in html and "dist/map.js" in html and 'id="map-data"' in html
    partial = client.get(page.url, {"region": "fergana"}, HTTP_HX_REQUEST="true")
    text = partial.content.decode()
    assert "<html" not in text
    assert "Fargʻona tumani oilaviy shifokorlik punkti" in text
    data = json.loads(text.split('id="map-data">')[1].split("</script>")[0])
    assert len(data) == 1 and data[0]["lat"] == 40.38 and data[0]["sections"] == "women"
    ru = client.get("/ru/zhenskiy/kuda-obratitsya/", {"kind": "ngo"}, HTTP_HX_REQUEST="true")
    assert "Умид" in ru.content.decode()
