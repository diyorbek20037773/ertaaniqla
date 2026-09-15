"""Latin ↔ Cyrillic normaliser and synonym expansion (spec §7)."""

from __future__ import annotations

import pytest

from apps.search.services import build_query, clean_query, expand_query
from apps.search.translit import (
    cyr_to_lat,
    lat_to_cyr,
    normalise_apostrophes,
    script_variants,
)


@pytest.mark.parametrize(
    ("cyr", "lat"),
    [
        ("скрининг", "skrining"),
        ("кўкрак", "koʻkrak"),
        ("ғалла", "gʻalla"),
        ("чақалоқ", "chaqaloq"),
        ("шифокор", "shifokor"),
        ("ёш", "yosh"),
    ],
)
def test_cyr_to_lat(cyr: str, lat: str) -> None:
    assert cyr_to_lat(cyr) == lat


@pytest.mark.parametrize(
    ("lat", "cyr"),
    [
        ("skrining", "скрининг"),
        ("koʻkrak", "кўкрак"),
        ("ko'krak", "кўкрак"),
        ("shifokor", "шифокор"),
        ("qayerga", "қайерга"),
    ],
)
def test_lat_to_cyr(lat: str, cyr: str) -> None:
    assert lat_to_cyr(lat) == cyr


def test_normalise_apostrophes() -> None:
    assert normalise_apostrophes("o'zbek o’zbek o‘zbek") == "oʻzbek oʻzbek oʻzbek"


def test_script_variants_include_both_scripts() -> None:
    assert script_variants("скрининг") == ["скрининг", "skrining"]
    assert script_variants("Skrining") == ["Skrining", "скрининг"]
    assert script_variants("  ") == []


def test_clean_query_limits_and_strips() -> None:
    assert clean_query("  mammografiya\x00  ") == "mammografiya"
    assert clean_query("a") == ""
    assert len(clean_query("x" * 500)) == 100


def test_expand_query_adds_synonyms_and_translit() -> None:
    variants = expand_query("saraton")
    assert "saraton" in variants
    assert "рак" in variants
    assert "сaратон" not in variants
    variants = expand_query("koʻkrak saraton")
    assert "грудь" in variants
    assert "рак" in variants
    assert len(variants) <= 12


def test_build_query_single_and_or() -> None:
    assert type(build_query("12345")).__name__ == "PlainText"  # no script to transliterate
    assert type(build_query("zzzzunknown")).__name__ == "Or"  # + Cyrillic transliteration
    assert type(build_query("skrining")).__name__ == "Or"
