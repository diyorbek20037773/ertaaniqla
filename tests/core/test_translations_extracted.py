"""Every `{% trans "…" %}` literal in the templates is in the uz and ru catalogues.

`scripts/check_translations.py` only inspects entries that are already in the `.po` files, so a
new template string that nobody ran `make messages` for slipped through to production in English
(M5b-4 hero buttons). This test closes that gap without needing gettext on the machine.
"""

from __future__ import annotations

import re
from pathlib import Path

import polib
import pytest

ROOT = Path(__file__).resolve().parents[2]
TRANS_RE = re.compile(
    r"""\{%\s*trans\s+(?P<q>["'])(?P<msgid>.+?)(?P=q)"""
    r"""(?:\s+context\s+(?P<cq>["']).+?(?P=cq))?(?:\s+as\s+\w+)?\s*%\}"""
)


def _template_msgids() -> set[str]:
    msgids: set[str] = set()
    for base in (ROOT / "templates", ROOT / "apps"):
        for path in base.rglob("*.html"):
            for match in TRANS_RE.finditer(path.read_text(encoding="utf-8")):
                msgids.add(match.group("msgid"))
    return msgids


@pytest.mark.parametrize("lang", ["uz", "ru"])
def test_every_template_trans_literal_is_translated(lang: str) -> None:
    po = polib.pofile(str(ROOT / "locale" / lang / "LC_MESSAGES" / "django.po"))
    translated = {e.msgid for e in po if e.msgstr and not e.obsolete and "fuzzy" not in e.flags}
    missing = sorted(_template_msgids() - translated)
    assert not missing, f"run `make messages` and translate: {missing}"
