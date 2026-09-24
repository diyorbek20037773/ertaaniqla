"""Designer illustrations shipped as static files (Figma, D-067) that blocks can reference by name.

Editors pick them from a list instead of uploading: the seed tree uses them, and swapping a file
in `static/img/figma/` (e.g. a sharper SVG re-export, H-029) needs no content change.
Uploaded Wagtail images always win over these when both are set on a block.
"""

from __future__ import annotations

from django.utils.translation import gettext_lazy as _

_W = "img/figma/women/"

# name → (static path, human label). Icons sit on the pink tile of an icon card.
ICONS: dict[str, tuple[str, str]] = {
    "women": (_W + "risk-women-risk.png", _("Woman silhouette")),
    "age": (_W + "risk-age.png", _("Age")),
    "breast-disease": (_W + "risk-breast-disease.png", _("Flower (breast disease)")),
    "other-disease": (_W + "risk-other-disease.png", _("Medical cross (white)")),
    "genes": (_W + "risk-genes.png", _("DNA and ribbon")),
    "radiation": (_W + "risk-radiation.png", _("Radiation")),
    "chronic": (_W + "risk-chronic.png", _("Medical cross (lime)")),
    "late-birth": (_W + "risk-late-birth.png", _("Heart with baby")),
    "hormone": (_W + "risk-hormone.png", _("Molecule (hormones)")),
    "habits": (_W + "risk-habits.png", _("Head (habits)")),
}

ILLUSTRATIONS: dict[str, tuple[str, str]] = {
    "mammography": (_W + "method-mammography.png", _("Mammography")),
    "ultrasound": (_W + "method-ultrasound.png", _("Ultrasound")),
    "mri": (_W + "method-mri.png", _("MRI")),
    "selfexam-1": (_W + "selfexam-1.png", _("Self-exam 1: in front of a mirror")),
    "selfexam-2": (_W + "selfexam-2.png", _("Self-exam 2: hands behind the head")),
    "selfexam-3": (_W + "selfexam-3.png", _("Self-exam 3: lying down")),
    "selfexam-4": (_W + "selfexam-4.png", _("Self-exam 4: nipple and armpit")),
}


def icon_choices() -> list[tuple[str, str]]:
    return [(key, label) for key, (_path, label) in ICONS.items()]


def illustration_choices() -> list[tuple[str, str]]:
    return [(key, label) for key, (_path, label) in ILLUSTRATIONS.items()]


def static_path(name: str) -> str | None:
    """Static path for an icon or illustration name, or None when unknown."""
    entry = ICONS.get(name) or ILLUSTRATIONS.get(name)
    return entry[0] if entry else None
