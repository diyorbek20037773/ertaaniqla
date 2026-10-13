"""Ministry of Health institution list (D-082): xlsx → import CSV conversion, and the directory's
search and pages for ~3 000 institutions."""

from __future__ import annotations

import csv
from pathlib import Path

import openpyxl
import pytest
from django.test import Client

from apps.directory.models import Institution, InstitutionKind, Region
from scripts.ssv_to_csv import convert, cyr_to_lat, kind_for, sections_for


def test_cyrillic_uzbek_to_latin() -> None:
    assert cyr_to_lat("Бухоро шаҳар кўп тармоқли марказий поликлиника") == (
        "Buxoro shahar koʻp tarmoqli markaziy poliklinika"
    )
    assert cyr_to_lat("Ғаллаорол ОШП") == "Gʻallaorol OSHP"  # abbreviations stay in capitals
    assert cyr_to_lat("Ешон, Юнусобод") == "Yeshon, Yunusobod"
    assert cyr_to_lat("Already Latin 12-OP") == "Already Latin 12-OP"


@pytest.mark.parametrize(
    ("cls", "name", "kind"),
    [
        (1, "Чинобод ОШП", "svp"),
        (2, "5 ОП", "polyclinic"),
        (3, "Туман тиббиёт бирлашмаси", "polyclinic"),
        (5, "1-сон туғруқ мажмуаси", "mother_child_centre"),
        (6, "Онкология ва радиология маркази Андижон филиали", "oncology_centre"),
        (7, "Мингбулоқ туман марказий шифохона", "hospital"),
        (4, "Sanitariya-epidemiologik osoyishtalik boʼlimi", None),
        (7, "Республика тез тиббий ёрдам маркази Жиззах филиали", None),
        (7, "Жиззах шаҳар силга қарши кураш диспансери", None),
        (3, "Вилоят стоматология поликлиникаси", None),
    ],
)
def test_kind_and_exclusions(cls: int, name: str, kind: str | None) -> None:
    assert kind_for(cls, name) == kind


def test_sections() -> None:
    assert sections_for("Андижон шаҳар болалар шифохонаси") == "children"
    assert sections_for("Перинатал маркази") == "women"
    assert sections_for("12 ОП") == "both"


@pytest.mark.django_db
def test_convert_and_import(tmp_path: Path) -> None:
    from django.core.management import call_command

    xlsx = tmp_path / "ssv.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["viloyat", "tuman", "nomi", "manzil", "class"])
    ws.append([None, None, None, None, None])
    ws.append(
        [
            "Buxoro",
            "Buxoro",
            "Бухоро шаҳар кўп тармоқли марказий поликлиника",
            "Пиридастгир 15-уй",
            3,
        ]
    )
    ws.append(["Toshkent sh", "Chilonzor", "Chilonzor tuman 33-son OP", "Bunyodkor 1", 2])
    ws.append(["QR", "Nukus", "Sanitariya boʼlimi", "Nukus", 4])
    wb.save(xlsx)
    out = tmp_path / "out.csv"
    stats = convert(xlsx, out)
    assert stats == {
        "rows": 3,
        "kept": 2,
        "dropped_class4": 1,
        "dropped_other": 0,
        "unknown_region": 0,
    }
    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    assert rows[0]["name_uz"] == "Buxoro shahar koʻp tarmoqli markaziy poliklinika"
    assert rows[0]["name_ru"] == "Бухоро шаҳар кўп тармоқли марказий поликлиника"
    assert rows[1]["name_ru"].startswith("Чилонзор")
    call_command("import_institutions", str(out), source="ssv")
    call_command("import_institutions", str(out), source="ssv")  # a newer file updates, no copies
    assert Institution.objects.filter(external_source="ssv").count() == 2


@pytest.mark.django_db
def test_directory_search_and_pages(seeded, client: Client) -> None:
    region = Region.objects.get(code="fergana")
    Institution.objects.bulk_create(
        Institution(
            name_uz=f"{n}-sonli OP",
            name_ru=f"{n}-сонли ОП",
            kind=InstitutionKind.POLYCLINIC,
            region=region,
            district_uz="Quva" if n == 7 else "Fargʻona",
        )
        for n in range(1, 41)
    )
    url = "/uz/ayollar/qayerga-murojaat/?region=fergana"
    first = client.get(url).content.decode()
    assert "40 ta muassasa" in first and first.count('class="institution"') == 30
    assert 'class="pager"' in first and "page=2" in first
    second = client.get(url + "&page=2").content.decode()
    assert second.count('class="institution"') == 10
    found = client.get(url + "&q=quva").content.decode()
    assert "1 ta muassasa" in found and "7-sonli OP" in found


def test_district_key_and_centres() -> None:
    from apps.directory.geo import district_centre, district_key

    assert district_key("Andijon sh.") == "andijon#city"
    assert district_key("Chilonzor tumani") == "chilonzor"
    assert district_key("Tuproqqalʼa_tumani") == "tuproqqala"
    lat, lng = district_centre("tashkent-city", "Chilonzor tumani")
    assert 41.1 < lat < 41.4 and 69.0 < lng < 69.4
    assert district_centre("samarkand", "Samarqand") is not None
    assert district_centre("samarkand", "Yoʻq tuman") is None


@pytest.mark.django_db
def test_map_overview_regions_districts_and_district_filter(seeded, client: Client) -> None:
    import json
    import re

    region = Region.objects.get(code="samarkand")
    for n, district in enumerate(["Urgut", "Urgut", "Samarqand"]):
        Institution.objects.create(
            name_uz=f"{n} OP",
            name_ru=f"{n} ОП",
            kind=InstitutionKind.POLYCLINIC,
            region=region,
            district_uz=district,
        )
    html = client.get("/uz/ayollar/qayerga-murojaat/?region=samarkand").content.decode()
    data = json.loads(re.search(r'id="map-data">(.*?)</script>', html, re.S).group(1))
    assert data["regions"]["samarkand"]["count"] == 3
    assert data["regions"]["samarkand"]["label"] == "3 ta muassasa"
    assert data["regions"]["fergana"]["count"] == 0  # every region is drawn
    urgut = next(d for d in data["districts"] if d["district"] == "Urgut")
    assert urgut["count"] == 2 and urgut["lat"] > 39
    assert data["selected"] == {"region": "samarkand", "district": ""}
    narrowed = client.get("/uz/ayollar/qayerga-murojaat/?region=samarkand&district=Urgut")
    assert "2 ta muassasa" in narrowed.content.decode()
    oz = client.get("/oz/ayollar/qayerga-murojaat/?region=samarkand").content.decode()
    assert '"district": "Urgut"' in oz  # the filter value stays Latin on the Cyrillic site
