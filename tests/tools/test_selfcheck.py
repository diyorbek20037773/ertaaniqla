from __future__ import annotations

from apps.tools.selfcheck import Item, score

ITEMS = [Item("a", "routine"), Item("b", "soon"), Item("c", "urgent"), Item("d", "bogus")]


def test_none_checked() -> None:
    r = score(ITEMS, [])
    assert r.level == "none" and r.checked == 0 and r.total == 4 and not r.see_doctor


def test_highest_urgency_wins() -> None:
    assert score(ITEMS, ["a"]).level == "routine"
    assert score(ITEMS, ["a", "b"]).level == "soon"
    assert score(ITEMS, ["c", "a"]).level == "urgent"
    assert score(ITEMS, ["c"]).see_doctor


def test_unknown_ids_and_bogus_urgency_ignored() -> None:
    r = score(ITEMS, ["zzz", "d"])
    assert r.level == "none"
    assert r.checked == 1  # "d" exists but has no valid urgency
