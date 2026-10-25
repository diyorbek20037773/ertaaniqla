"""Screening route (D-105, the doctor's feedback of 2026-10-25): the woman picks her region and
district — no institution type — and sees the polyclinic for the test and the Mother & Child
Health Centre branch for colposcopy."""

from __future__ import annotations

import importlib

import pytest
from django.apps import apps as django_apps
from django.core.management import call_command
from django.test import Client
from wagtail.models import Page

from apps.directory.models import DirectoryPage, Institution, InstitutionKind, Region
from apps.directory.services import route_districts, route_places

pytestmark = pytest.mark.django_db

SCREENING = "/uz/ayollar/skrining/bachadon-boyni-saratoni/"


def _place(name: str, kind: str, region: str, district: str, **extra: object) -> Institution:
    return Institution.objects.create(
        name_uz=name,
        name_ru=name,
        kind=kind,
        region=Region.objects.get(code=region),
        district_uz=district,
        district_ru=district,
        **extra,
    )


@pytest.fixture
def places() -> dict[str, Institution]:
    return {
        "uchtepa": _place(
            "Uchtepa 5-poliklinika", InstitutionKind.POLYCLINIC, "tashkent-city", "Uchtepa tumani"
        ),
        "chilonzor": _place(
            "Chilonzor 1-poliklinika",
            InstitutionKind.POLYCLINIC,
            "tashkent-city",
            "Chilonzor tumani",
        ),
        "maternity": _place(
            "Tugʻruq kompleksi",
            InstitutionKind.MOTHER_CHILD_CENTRE,
            "tashkent-city",
            "Uchtepa tumani",
        ),
        "branch": _place(
            "Ona va bola salomatligi markazi Fargʻona filiali",
            InstitutionKind.MOTHER_CHILD_CENTRE,
            "fergana",
            "Fargʻona sh.",
            colposcopy_branch=True,
        ),
    }


def test_districts_and_places_for_each_step(places) -> None:
    assert ("Uchtepa tumani", "Uchtepa tumani") in route_districts("tashkent-city", "uz")
    step1 = route_places("district_polyclinics", "tashkent-city", "Uchtepa tumani")
    assert step1["items"] == [places["uchtepa"]]  # not Chilonzor, not the maternity complex
    step2 = route_places("region_branch", "fergana", "")
    assert step2 == {"items": [places["branch"]], "fallback": False}
    # no branch on record for the region yet: every branch is listed, flagged as a fallback
    assert route_places("region_branch", "tashkent-city", "") == {
        "items": [places["branch"]],
        "fallback": True,
    }
    assert route_places("district_polyclinics", "tashkent-city", "")["items"] == []


def test_the_screening_page_shows_the_route(seeded, places, client: Client) -> None:
    html = client.get(SCREENING).content.decode()
    assert 'id="screening-route"' in html and 'name="sr"' in html
    assert "Uchtepa 5-poliklinika" not in html  # nothing until a district is chosen
    html = client.get(SCREENING, {"sr": "tashkent-city", "sd": "Uchtepa tumani"}).content.decode()
    route = html.split('id="screening-route"', 1)[1].split("</section>", 1)[0]
    assert "Uchtepa 5-poliklinika" in route and "Chilonzor 1-poliklinika" not in route
    assert '<option value="Uchtepa tumani" selected>' in route
    assert "Fargʻona filiali" in route  # step 2: the branches (none recorded in Tashkent here)
    # an unknown district is ignored, never an error
    assert client.get(SCREENING, {"sr": "tashkent-city", "sd": "<x>"}).status_code == 200


def test_branches_are_marked_by_the_migration(places) -> None:
    """The data step of 0009 marks the Centre and its branches by name, not maternity units."""
    Institution.objects.update(colposcopy_branch=False)
    migration = importlib.import_module(
        "apps.directory.migrations.0009_institution_colposcopy_branch"
    )
    migration.mark_branches(django_apps, None)
    marked = set(
        Institution.objects.filter(colposcopy_branch=True).values_list("name_uz", flat=True)
    )
    assert marked == {"Ona va bola salomatligi markazi Fargʻona filiali"}


def test_live_update_adds_the_route_once_and_fixes_the_infections(seeded, client: Client) -> None:
    from apps.core.management.commands.client_update_20261025 import ROUTE

    screening = Page.objects.get(
        url_path__endswith="/ayollar/skrining/bachadon-boyni-saratoni/", locale__language_code="uz"
    ).specific
    awareness = Page.objects.get(
        url_path__endswith="/ayollar/ogohlik/bachadon-boyni-saratoni/", locale__language_code="uz"
    ).specific
    # what live sites had before D-105: no route, cytomegalovirus in the infections tile
    screening.body = [b for b in screening.body.raw_data if b["type"] != ROUTE]
    screening.save_revision().publish()
    for page in DirectoryPage.objects.all():
        page.intro = [b for b in page.intro.raw_data if b["type"] != ROUTE]
        page.save_revision().publish()
    import json

    raw = json.dumps(list(awareness.body.raw_data), ensure_ascii=False).replace(
        "OIV, genital gerpes, xlamidioz. Bu infeksiyalar mahalliy immunitetni pasaytirishi mumkin.",
        "OIV, genital gerpes, sitomegalovirus, xlamidioz.",
    )
    awareness.body = json.loads(raw)
    awareness.save_revision().publish()

    call_command("client_update_20261025")
    call_command("client_update_20261025")  # a second run changes nothing

    screening.refresh_from_db()
    assert [b["type"] for b in screening.body.raw_data].count(ROUTE) == 1
    for page in DirectoryPage.objects.all():
        page.refresh_from_db()
        assert [b["type"] for b in page.intro.raw_data].count(ROUTE) == 1
    awareness.refresh_from_db()
    text = json.dumps(list(awareness.body.raw_data), ensure_ascii=False)
    assert "sitomegalovirus" not in text and "mahalliy immunitetni" in text
    assert (
        "цитомегаловирус"
        not in client.get("/ru/zhenskiy/osvedomlennost/rak-sheyki-matki/").content.decode()
    )


def test_live_update_never_publishes_an_editors_draft(seeded) -> None:
    screening = Page.objects.get(
        url_path__endswith="/ayollar/skrining/bachadon-boyni-saratoni/", locale__language_code="uz"
    ).specific
    screening.body = [b for b in screening.body.raw_data if b["type"] != "screening_route"]
    screening.save_revision().publish()
    screening.title = "Muharrir qoralamasi"
    screening.save_revision()  # a draft, not published
    call_command("client_update_20261025")
    screening.refresh_from_db()
    assert screening.title != "Muharrir qoralamasi"
    assert all(b["type"] != "screening_route" for b in screening.body.raw_data)


def test_a_region_without_a_branch_gets_the_two_nearest(places) -> None:
    """Not every branch in the country on a phone: the two closest to the chosen district."""
    for name, region, lat, lng in (
        ("Toshkent viloyati filiali", "tashkent", "41.10", "69.30"),
        ("Sirdaryo filiali", "syrdarya", "40.50", "68.80"),
        ("Qoraqalpogʻiston filiali", "karakalpakstan", "42.45", "59.60"),
    ):
        _place(
            name,
            InstitutionKind.MOTHER_CHILD_CENTRE,
            region,
            "",
            colposcopy_branch=True,
            lat=lat,
            lng=lng,
        )
    Institution.objects.filter(pk=places["uchtepa"].pk).update(lat="41.29", lng="69.18")
    result = route_places("region_branch", "tashkent-city", "Uchtepa tumani")
    assert result["fallback"] is True
    assert [i.name_uz for i in result["items"]] == ["Toshkent viloyati filiali", "Sirdaryo filiali"]


def test_nearest_branches_without_coordinates_use_district_centres(places) -> None:
    """The ministry registry has no coordinates: Bukhara (no branch on record) gets Navoi first,
    by the centres of the districts."""
    Institution.objects.filter(colposcopy_branch=True).update(colposcopy_branch=False)
    for name, region, district in (
        ("Navoiy filiali", "navoi", "Navoiy sh."),
        ("Qoraqalpogʻiston filiali", "karakalpakstan", "Nukus"),
        ("Toshkent viloyati filiali", "tashkent", "Nurafshon"),
    ):
        _place(name, InstitutionKind.MOTHER_CHILD_CENTRE, region, district, colposcopy_branch=True)
    _place("Buxoro 1-poliklinika", InstitutionKind.POLYCLINIC, "bukhara", "Buxoro sh.")
    result = route_places("region_branch", "bukhara", "Buxoro sh.")
    assert result["fallback"] is True
    assert result["items"][0].name_uz == "Navoiy filiali"
    assert route_places("region_branch", "bukhara", "")["items"][0].name_uz == "Navoiy filiali"
