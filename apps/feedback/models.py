"""Generic feedback form (F5): bug / feedback / partnership. Contact encrypted, retention
180 days (spec §8). No accounts, no tracking beyond page URL + user agent."""

from __future__ import annotations

from typing import Any

from django.db import models
from django.http import Http404
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.fields import RichTextField, StreamField
from wagtail.models import Page
from wagtail.snippets.models import register_snippet

from apps.articles.blocks import IntroBlock, stream_plain_text
from apps.core.antispam import form_is_ratelimited
from apps.core.fields import EncryptedCharField
from apps.core.models import BasePage, TimeStampedModel


class FeedbackKind(models.TextChoices):
    FEEDBACK = "feedback", _("Feedback about the site")
    BUG = "bug", _("Something is broken")
    PARTNERSHIP = "partnership", _("Partnership / volunteering")


@register_snippet
class FeedbackSubmission(TimeStampedModel):
    kind = models.CharField(_("kind"), max_length=16, choices=FeedbackKind.choices, db_index=True)
    text = models.TextField(_("message"), max_length=3000)
    contact = EncryptedCharField(_("contact (optional, encrypted)"), max_length=200, blank=True)
    page_url = models.CharField(_("page"), max_length=500, blank=True)
    user_agent = models.CharField(_("browser"), max_length=300, blank=True)
    language = models.CharField(_("language"), max_length=8, default="uz")
    handled = models.BooleanField(_("handled"), default=False, db_index=True)

    panels = [
        MultiFieldPanel(
            [FieldPanel("kind", read_only=True), FieldPanel("handled")], heading=_("Status")
        ),
        MultiFieldPanel(
            [
                FieldPanel("text", read_only=True),
                FieldPanel("contact", read_only=True),
                FieldPanel("page_url", read_only=True),
                FieldPanel("user_agent", read_only=True),
                FieldPanel("language", read_only=True),
            ],
            heading=_("Submission"),
        ),
    ]

    class Meta:
        verbose_name = _("feedback submission")
        verbose_name_plural = _("feedback submissions")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"#{self.pk} {self.get_kind_display()}: {self.text[:50]}"


class FeedbackPage(BasePage):
    """`/uz/qayta-aloqa/` `/ru/obratnaya-svyaz/`."""

    intro = StreamField(IntroBlock(), blank=True, verbose_name=_("intro"))
    thanks_text = RichTextField(
        _("thank-you text"), editor="minimal", default="<p>[[TODO: content — copywriter]]</p>"
    )

    content_panels = [*Page.content_panels, FieldPanel("intro"), FieldPanel("thanks_text")]
    parent_page_types = ["home.HomePage"]
    subpage_types: list[str] = []
    template = "feedback/feedback_page.html"

    class Meta:
        verbose_name = _("feedback page")

    def get_body_text(self) -> str:
        return stream_plain_text(self.intro)

    def get_context(self, request: Any, *args: Any, **kwargs: Any) -> dict[str, Any]:
        from apps.feedback.forms import FeedbackForm

        context = super().get_context(request, *args, **kwargs)
        context["form"] = kwargs.get("form") or FeedbackForm(
            request=request, initial={"page_url": request.GET.get("from", "")[:500]}
        )
        context["submitted"] = kwargs.get("submitted", False)
        return context

    def serve(self, request: Any, *args: Any, **kwargs: Any) -> Any:
        from apps.feedback.forms import FeedbackForm
        from apps.feedback.services import submit_feedback

        if not self.live:
            raise Http404
        is_htmx = bool(request.headers.get("HX-Request"))
        if request.method == "POST":
            if form_is_ratelimited(request, group="feedback.submit"):
                return TemplateResponse(request, "429.html", status=429)
            form = FeedbackForm(request.POST, request=request)
            if form.is_valid():
                submit_feedback(form, request)
                template = "feedback/_form.html" if is_htmx else self.template
                return TemplateResponse(
                    request, template, self.get_context(request, submitted=True)
                )
            template = "feedback/_form.html" if is_htmx else self.template
            return TemplateResponse(
                request,
                template,
                self.get_context(request, form=form),
                status=400 if is_htmx else 200,
            )
        return super().serve(request, *args, **kwargs)
