"""Forms for the stateless tools (spec A1, A2)."""

from __future__ import annotations

from typing import Any

from django import forms
from django.utils.translation import gettext_lazy as _

from apps.tools.screening import NEVER, TESTS

YEARS_CHOICES = [
    (NEVER, _("Never")),
    ("0", _("Less than a year ago")),
    ("1", _("About a year ago")),
    ("2", _("2 years ago")),
    ("3", _("3 years ago or more")),
]

TEST_LABELS = {
    "mammography": _("Mammography"),
    "ultrasound": _("Breast ultrasound"),
    "hpv": _("HPV test"),
}


class ScreeningForm(forms.Form):
    age = forms.IntegerField(
        label=_("Your age"),
        min_value=18,
        max_value=100,
        widget=forms.NumberInput(attrs={"inputmode": "numeric", "autocomplete": "off"}),
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        for test in TESTS:
            self.fields[f"last_{test}"] = forms.ChoiceField(
                label=_("Last %(test)s") % {"test": TEST_LABELS[test]},
                choices=YEARS_CHOICES,
                initial=NEVER,
                required=False,
            )

    def last_tests(self) -> dict[str, str]:
        return {test: str(self.cleaned_data.get(f"last_{test}") or NEVER) for test in TESTS}


class SelfCheckForm(forms.Form):
    """Checkbox list built from the page's items (ids = block ids)."""

    def __init__(self, items: list[tuple[str, str]], *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["items"] = forms.MultipleChoiceField(
            label=_("Tick everything you have noticed"),
            choices=items,
            required=False,
            widget=forms.CheckboxSelectMultiple,
        )
