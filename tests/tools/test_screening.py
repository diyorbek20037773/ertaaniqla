"""Screening rules — table-driven from the TZ (A1). Every age boundary is checked."""

from __future__ import annotations

import pytest

from apps.tools.screening import NEVER, RULES, TESTS, any_due, evaluate, years_since


def result(age: int, test: str, **last):
    return next(r for r in evaluate(age, last) if r.test == test)


@pytest.mark.parametrize(
    ("age", "mammography", "ultrasound", "hpv"),
    [
        (18, False, True, False),
        (29, False, True, False),
        (30, False, True, True),  # HPV band starts
        (44, False, True, True),  # last ultrasound age ("до 45")
        (45, True, False, True),  # mammography starts
        (50, True, False, True),  # last HPV age
        (51, True, False, False),
        (65, True, False, False),  # last mammography age
        (66, False, False, False),
        (100, False, False, False),
    ],
)
def test_age_bands(age: int, mammography: bool, ultrasound: bool, hpv: bool) -> None:
    assert result(age, "mammography").applies is mammography
    assert result(age, "ultrasound").applies is ultrasound
    assert result(age, "hpv").applies is hpv


@pytest.mark.parametrize(
    ("last", "due", "next_in"),
    [
        (NEVER, True, 0),
        ("0", False, 2),
        ("1", False, 1),
        ("2", True, 0),
        ("3", True, 0),
        (None, True, 0),
        ("garbage", True, 0),
    ],
)
def test_two_year_interval(last: str | None, due: bool, next_in: int) -> None:
    mammo = result(50, "mammography", mammography=last)
    assert mammo.due is due
    assert mammo.next_in_years == next_in
    assert mammo.status == ("due" if due else "ok")
    ultra = result(40, "ultrasound", ultrasound=last)
    assert ultra.due is due


def test_hpv_interval_is_doctor_decided() -> None:
    never = result(35, "hpv", hpv=NEVER)
    assert never.due and never.next_in_years == 0
    done = result(35, "hpv", hpv="1")
    assert not done.due and done.next_in_years is None
    assert done.interval_years is None


def test_not_applicable_status_and_any_due() -> None:
    results = evaluate(70)
    assert all(r.status == "not_applicable" for r in results)
    assert not any_due(results)
    assert any_due(evaluate(45))


def test_rules_are_the_tz_table() -> None:
    assert TESTS == ("mammography", "ultrasound", "hpv")
    by_test = {r.test: r for r in RULES}
    assert (by_test["mammography"].min_age, by_test["mammography"].max_age) == (45, 65)
    assert (by_test["ultrasound"].min_age, by_test["ultrasound"].max_age) == (None, 44)
    assert (by_test["hpv"].min_age, by_test["hpv"].max_age) == (30, 50)
    assert by_test["mammography"].interval_years == by_test["ultrasound"].interval_years == 2


def test_years_since_parsing() -> None:
    assert years_since(NEVER) is None
    assert years_since("") is None
    assert years_since("-3") == 0
    assert years_since(2) == 2
