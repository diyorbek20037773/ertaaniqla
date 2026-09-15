"""Self-check scoring (spec A2): women's symptom checklist and the children's warning-signs
checklist. Never a diagnosis. Nothing is stored. Items and result wording are CMS content
(`SelfCheckPage`); this module only decides the urgency level."""

from __future__ import annotations

from dataclasses import dataclass

LEVELS: tuple[str, ...] = ("none", "routine", "soon", "urgent")
_RANK = {level: index for index, level in enumerate(LEVELS)}


@dataclass(frozen=True)
class Item:
    id: str
    urgency: str  # routine | soon | urgent


@dataclass(frozen=True)
class SelfCheckResult:
    level: str
    checked: int
    total: int

    @property
    def see_doctor(self) -> bool:
        return self.level in {"soon", "urgent"}


def score(items: list[Item], checked_ids: list[str]) -> SelfCheckResult:
    """Highest urgency among checked items decides the level; unknown ids are ignored."""
    by_id = {item.id: item for item in items}
    level = "none"
    count = 0
    for item_id in checked_ids:
        item = by_id.get(item_id)
        if item is None:
            continue
        count += 1
        if _RANK.get(item.urgency, 0) > _RANK[level]:
            level = item.urgency
    return SelfCheckResult(level=level, checked=count, total=len(items))
