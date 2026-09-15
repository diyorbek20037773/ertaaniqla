from __future__ import annotations

from typing import Any

from django import forms
from django.utils.translation import gettext_lazy as _

from apps.core.forms import AntiSpamFormMixin, add_error_attrs
from apps.faq.models import Question, QuestionSection


class QuestionForm(AntiSpamFormMixin, forms.ModelForm):
    section = forms.ChoiceField(label=_("Section"), choices=QuestionSection.choices)
    consent_privacy = forms.BooleanField(
        label=_("I agree to the processing of my data as described in the privacy policy"),
        required=True,
    )

    class Meta:
        model = Question
        fields = ["name", "contact", "section", "text", "consent_to_publish"]
        labels = {
            "name": _("Your name (optional)"),
            "contact": _("Phone or e-mail (optional, for a private reply)"),
            "text": _("Your question"),
            "consent_to_publish": _("My question may be published anonymously with the answer"),
        }
        widgets = {
            "text": forms.Textarea(attrs={"rows": 5, "maxlength": 2000}),
            "contact": forms.TextInput(attrs={"autocomplete": "off", "maxlength": 200}),
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["text"].min_length = 10  # type: ignore[attr-defined]
        self.fields["text"].validators.append(_min_length(10))

    def clean_text(self) -> str:
        text = " ".join(str(self.cleaned_data.get("text", "")).split())
        if len(text) < 10:
            raise forms.ValidationError(_("Please describe your question in a few words."))
        return text

    def full_clean(self) -> None:
        super().full_clean()
        add_error_attrs(self)


def _min_length(n: int) -> Any:
    from django.core.validators import MinLengthValidator

    return MinLengthValidator(n)
