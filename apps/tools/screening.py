"""Screening eligibility helper (spec A1) — table-driven from the TZ screening table:

    маммография: женщины 45–65 лет, раз в 2 года
    УЗИ:         женщины до 45 лет,  раз в 2 года
    ВПЧ-тест:    женщины 30–50 лет   (interval not given in the TZ → [[VERIFY: doctor]])

Stateless: nothing is stored. The result says which tests apply at this age, whether each is
due now (never done / last done ≥ interval ago) and when the next one is expected.
Wording shown to visitors comes from the CMS page, not from here.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

NEVER = "never"  # form value for "never had this test"


@dataclass(frozen=True)
class Rule:
    test: str
    min_age: int | None
    max_age: int | None  # inclusive
    interval_years: int | None  # None = interval defined by the doctor

    def applies(self, age: int) -> bool:
        if self.min_age is not None and age < self.min_age:
            return False
        return not (self.max_age is not None and age > self.max_age)


# Verbatim TZ facts. "до 45 лет" = up to and including 44.
RULES: tuple[Rule, ...] = (
    Rule("mammography", 45, 65, 2),
    Rule("ultrasound", None, 44, 2),
    Rule("hpv", 30, 50, None),
)
TESTS = tuple(rule.test for rule in RULES)


@dataclass(frozen=True)
class TestResult:
    test: str
    applies: bool
    due: bool
    years_since_last: int | None  # None = never
    interval_years: int | None
    next_in_years: int | None  # 0 = now

    @property
    def status(self) -> str:
        if not self.applies:
            return "not_applicable"
        if self.due:
            return "due"
        return "ok"


def years_since(value: str | int | None) -> int | None:
    """Form value → years since the last test (None = never)."""
    if value in (None, "", NEVER):
        return None
    try:
        years = int(value)
    except (TypeError, ValueError):
        return None
    return max(0, years)


def evaluate(age: int, last: Mapping[str, str | int | None] | None = None) -> list[TestResult]:
    """`last` maps test → years since last test ("never"/None when never done)."""
    last = last or {}
    results: list[TestResult] = []
    for rule in RULES:
        applies = rule.applies(age)
        since = years_since(last.get(rule.test))
        if not applies:
            results.append(TestResult(rule.test, False, False, since, rule.interval_years, None))
            continue
        if rule.interval_years is None:
            # HPV: eligible in the age band; if never done → due now; otherwise doctor decides
            due = since is None
            next_in = 0 if due else None
        elif since is None or since >= rule.interval_years:
            due, next_in = True, 0
        else:
            due, next_in = False, rule.interval_years - since
        results.append(TestResult(rule.test, True, due, since, rule.interval_years, next_in))
    return results


def any_due(results: list[TestResult]) -> bool:
    return any(r.due for r in results)
