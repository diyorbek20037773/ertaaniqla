"""Fail when any `uz` or `ru` `.po` catalogue has untranslated or fuzzy entries (spec §7).

Usage: python scripts/check_translations.py [--allow-empty]
Exit code 1 lists every offending msgid so the developer can fix them.
"""

from __future__ import annotations

import sys
from pathlib import Path

import polib

ROOT = Path(__file__).resolve().parent.parent
LANGS = ("uz", "ru")
DOMAINS = ("django", "djangojs")


def main() -> int:
    problems: list[str] = []
    found_any = False
    for lang in LANGS:
        for domain in DOMAINS:
            po_path = ROOT / "locale" / lang / "LC_MESSAGES" / f"{domain}.po"
            if not po_path.exists():
                if domain == "django":
                    problems.append(f"{po_path.relative_to(ROOT)}: missing")
                continue
            found_any = True
            po = polib.pofile(str(po_path))
            for entry in po.untranslated_entries():
                if entry.obsolete:
                    continue
                problems.append(f"{lang}/{domain}: untranslated: {entry.msgid!r}")
            for entry in po.fuzzy_entries():
                problems.append(f"{lang}/{domain}: fuzzy: {entry.msgid!r}")
    if not found_any and "--allow-empty" not in sys.argv:
        problems.append("no .po catalogues found — run `make messages`")
    if problems:
        sys.stdout.write("\n".join(problems) + "\n")
        sys.stdout.write(f"\n{len(problems)} translation problem(s)\n")
        return 1
    sys.stdout.write("translations: uz + ru complete\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
