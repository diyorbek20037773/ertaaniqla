"""Directory reference data, model helpers, filters and the DirectoryPage (M1 scope)."""

from __future__ import annotations

import pytest
from django.test import Client

from apps.directory.models import (
    DirectoryPage,
    Institution,
    InstitutionKind,
    InstitutionSections,
    Region,
    Service,
)
from apps.directory.services import filter_institutions, institutions_for_block

pytestmark = pytest.mark.django_db


def test_fourteen_regions_and_services_exist() -> None:
    assert Region.objects.count() == 14
    assert Region.objects.get(code="karakalpakstan").name_ru == "Республика Каракалпакстан"
    assert Region.objects.first().code == "tashkent-city"
    assert Service.objects.filter(code__in=["mammography", "ultrasound", "hpv_test"]).count() == 3


@pytest.fixture
def institutions() -> list[Institution]:
    tashkent = Region.objects.get(code="tashkent-city")
    fergana = Region.objects.get(code="fergana")
    a = Institution.objects.create(
        name_uz="A poliklinika",
        name_ru="Поликлиника А",
        kind=InstitutionKind.POLYCLINIC,
        region=tashkent,
        free_under_state_programme=True,
        sections=InstitutionSections.WOMEN,
        lat="41.3",
        lng="69.2",
        phone="+998712001122",
        hours_uz="9-18",
        hours_ru="9–18",
    )
    b = Institution.objects.create(
        name_uz="B onkogematologiya",
        name_ru="Онкогематология Б",
        kind=InstitutionKind.PAEDIATRIC_ONCOHAEMATOLOGY,
        region=fergana,
        sections=InstitutionSections.CHILDREN,
    )
    c = Institution.objects.create(
        name_uz="C NNT",
        name_ru="НКО В",
        kind=InstitutionKind.NGO,
        region=fergana,
        sections=InstitutionSections.BOTH,
        is_published=False,
    )
    a.services.add(Service.objects.get(code="mammography"))
    return [a, b, c]


def test_model_helpers(institutions) -> None:
    a, b, _ = institutions
    assert str(a) == "A poliklinika"
    assert a.name_for("ru") == "Поликлиника А"
    assert a.address_for("uz") == ""
    assert a.district_for("ru") == ""
    assert a.hours_for("ru") == "9–18"
    assert a.has_coordinates is True
    assert b.has_coordinates is False
    assert str(Region.objects.first()) == "Toshkent shahri"
    assert Region.objects.first().name_for("ru") == "город Ташкент"
    assert str(Service.objects.get(code="hpv_test")) == "HPV-test"
    assert Service.objects.get(code="hpv_test").name_for("ru") == "ВПЧ-тест"


def test_filters(children_visible, institutions) -> None:
    a, b, _ = institutions
    assert set(filter_institutions()) == {a, b}  # unpublished hidden
    assert list(filter_institutions(region="fergana")) == [b]
    assert list(filter_institutions(kind="polyclinic")) == [a]
    assert list(filter_institutions(kind="bogus")) == [a, b]
    assert list(filter_institutions(section="children")) == [b]
    assert list(filter_institutions(section="women")) == [a]
    assert list(filter_institutions(free_only=True)) == [a]
    assert institutions_for_block({"region": "", "kind": "", "free_only": False, "limit": 1}) == [a]


def test_directory_page_renders_filters_and_results(
    children_visible, seeded, institutions, client: Client
) -> None:
    page = DirectoryPage.objects.get(locale__language_code="uz")
    html = client.get(page.url).content.decode()
    assert "A poliklinika" in html
    assert "B onkogematologiya" in html
    assert 'name="region"' in html
    assert html.count("<option") >= 14 + 8
    filtered = client.get(page.url, {"region": "fergana", "section": "children"}).content.decode()
    assert "B onkogematologiya" in filtered
    assert "A poliklinika" not in filtered
    empty = client.get(page.url, {"q": "Hech qayer"}).content.decode()
    assert "institution-list__empty" in empty
    ru_page = DirectoryPage.objects.get(locale__language_code="ru")
    assert client.get(ru_page.url).status_code == 200


def _kind_options(html: str) -> list[str]:
    field = html.split('id="filter-kind-field"', 1)[1].split("</select>", 1)[0]
    return [part.split('"', 1)[0] for part in field.split('<option value="')[2:]]


def test_type_options_follow_region_and_section(
    children_visible, seeded, institutions, client: Client
) -> None:
    """Region first, then the section; «Type» offers only the kinds found there and drops one
    the new choice has none of (client 2026-11-17, D-114)."""
    page = DirectoryPage.objects.get(locale__language_code="uz")
    html = client.get(page.url).content.decode()
    form = html.split('class="filter-form"', 1)[1]
    order = [form.index(f'for="filter-{name}"') for name in ("region", "section", "kind", "q")]
    assert order == sorted(order)
    assert _kind_options(html) == ["polyclinic", "paediatric_oncohaematology"]  # NGO unpublished
    assert _kind_options(client.get(page.url, {"section": "women"}).content.decode()) == [
        "polyclinic"
    ]
    assert _kind_options(client.get(page.url, {"region": "fergana"}).content.decode()) == [
        "paediatric_oncohaematology"
    ]
    # HTMX: the options come back out of band; a kind the new region lacks is dropped
    partial = client.get(
        page.url, {"region": "fergana", "kind": "polyclinic"}, HTTP_HX_REQUEST="true"
    ).content.decode()
    assert 'id="filter-kind-field" hx-swap-oob="true"' in partial
    assert _kind_options(partial) == ["paediatric_oncohaematology"]
    assert "B onkogematologiya" in partial and "selected>" not in partial.split("</select>")[0]
    assert "hx-swap-oob" not in html  # the full page has the field once


def test_directory_page_default_section_filter(seeded, institutions, client: Client) -> None:
    page = DirectoryPage.objects.get(locale__language_code="ru")
    page.default_section = InstitutionSections.WOMEN
    page.save_revision().publish()
    html = client.get(page.url).content.decode()
    assert "Поликлиника А" in html
    assert "Онкогематология Б" not in html
    assert "+998 71 200-11-22" in html
    assert page.get_body_text() != ""
