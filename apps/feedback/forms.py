from __future__ import annotations

from typing import Any

from django import forms
from django.utils.translation import gettext_lazy as _

from apps.core.forms import AntiSpamFormMixin, add_error_attrs
from apps.feedback.models import FeedbackKind, FeedbackSubmission


class FeedbackForm(AntiSpamFormMixin, forms.ModelForm):
    kind = forms.ChoiceField(label=_("What is it about?"), choices=FeedbackKind.choices)
    page_url = forms.CharField(required=False, widget=forms.HiddenInput, max_length=500)
    consent_privacy = forms.BooleanField(
        label=_("I agree to the processing of my data as described in the privacy policy"),
        required=True,
    )

    class Meta:
        model = FeedbackSubmission
        fields = ["kind", "text", "contact", "page_url"]
        labels = {
            "text": _("Your message"),
            "contact": _("Phone or e-mail (optional, if you want a reply)"),
        }
        widgets = {
            "text": forms.Textarea(attrs={"rows": 5, "maxlength": 3000}),
            "contact": forms.TextInput(attrs={"autocomplete": "off", "maxlength": 200}),
        }

    def clean_text(self) -> str:
        text = " ".join(str(self.cleaned_data.get("text", "")).split())
        if len(text) < 5:
            raise forms.ValidationError(_("Please write a few words."))
        return text

    def clean_page_url(self) -> str:
        value = str(self.cleaned_data.get("page_url") or "")
        return value if value.startswith("/") else ""

    def full_clean(self) -> None:
        super().full_clean()
        add_error_attrs(self)

    def save(self, commit: bool = True) -> Any:
        return super().save(commit=commit)
