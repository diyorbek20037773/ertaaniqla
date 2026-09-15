"""Ask-a-question form with moderated public FAQ (spec A3, §4.3 `Question`, §8 retention).

Flow: visitor submits → `Question(status=new)` → moderators are emailed → a doctor answers in
the CMS (snippet) → status `published` (with the visitor's consent) → shown on `FAQPage`.
The optional contact is encrypted at rest and purged 90 days after the answer.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.db import models
from django.http import Http404
from django.template.response import TemplateResponse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.fields import RichTextField, StreamField
from wagtail.models import Page
from wagtail.search import index
from wagtail.snippets.models import register_snippet

from apps.articles.blocks import IntroBlock, stream_plain_text
from apps.core.antispam import form_is_ratelimited
from apps.core.fields import EncryptedCharField
from apps.core.models import BasePage, SectionKey, TimeStampedModel


class QuestionSection(models.TextChoices):
    WOMEN = SectionKey.WOMEN.value, SectionKey.WOMEN.label
    CHILDREN = SectionKey.CHILDREN.value, SectionKey.CHILDREN.label
    OTHER = "other", _("Other")


class QuestionStatus(models.TextChoices):
    NEW = "new", _("New")
    ANSWERED = "answered", _("Answered (private)")
    PUBLISHED = "published", _("Published")
    REJECTED = "rejected", _("Rejected")


@register_snippet
class Question(index.Indexed, TimeStampedModel):
    name = models.CharField(_("name (optional)"), max_length=120, blank=True)
    contact = EncryptedCharField(
        _("contact (optional, encrypted)"),
        max_length=200,
        blank=True,
        help_text=_("Phone or e-mail. Encrypted at rest, deleted 90 days after the answer."),
    )
    section = models.CharField(
        _("section"), max_length=16, choices=QuestionSection.choices, db_index=True
    )
    text = models.TextField(_("question"), max_length=2000)
    consent_to_publish = models.BooleanField(_("may be published anonymously"), default=False)
    language = models.CharField(_("language"), max_length=8, default="uz")
    status = models.CharField(
        _("status"),
        max_length=16,
        choices=QuestionStatus.choices,
        default=QuestionStatus.NEW,
        db_index=True,
    )
    public_question = models.TextField(
        _("question as published"),
        blank=True,
        help_text=_("Edited/anonymised wording shown on the site (empty = original text)."),
    )
    answer = RichTextField(_("answer"), blank=True, editor="minimal")
    answered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("answered by"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    answered_at = models.DateTimeField(_("answered at"), null=True, blank=True)
    published_at = models.DateTimeField(_("published at"), null=True, blank=True)
    contact_purged_at = models.DateTimeField(_("contact purged at"), null=True, blank=True)

    panels = [
        MultiFieldPanel(
            [
                FieldPanel("status"),
                FieldPanel("section"),
                FieldPanel("language", read_only=True),
                FieldPanel("consent_to_publish", read_only=True),
            ],
            heading=_("Moderation"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("name", read_only=True),
                FieldPanel("contact"),
                FieldPanel("text", read_only=True),
            ],
            heading=_("Submitted"),
        ),
        MultiFieldPanel(
            [FieldPanel("public_question"), FieldPanel("answer"), FieldPanel("answered_by")],
            heading=_("Answer"),
        ),
    ]
    search_fields = [
        index.SearchField("text"),
        index.SearchField("answer"),
        index.FilterField("status"),
        index.FilterField("section"),
    ]

    class Meta:
        verbose_name = _("question to a doctor")
        verbose_name_plural = _("questions to a doctor")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"#{self.pk} {self.text[:60]}"

    @property
    def display_question(self) -> str:
        return self.public_question or self.text

    def save(self, *args: Any, **kwargs: Any) -> None:
        now = timezone.now()
        if (
            self.status in {QuestionStatus.ANSWERED, QuestionStatus.PUBLISHED}
            and not self.answered_at
        ):
            self.answered_at = now
        if self.status == QuestionStatus.PUBLISHED and not self.published_at:
            self.published_at = now
        if self.status == QuestionStatus.PUBLISHED and not self.consent_to_publish:
            # never publish without the visitor's consent — downgrade silently to "answered"
            self.status = QuestionStatus.ANSWERED
            self.published_at = None
        super().save(*args, **kwargs)

    def purge_contact(self) -> None:
        self.contact = ""
        self.contact_purged_at = timezone.now()
        self.save(update_fields=["contact", "contact_purged_at", "updated_at"])


class FAQPage(BasePage):
    """`/uz/savol-javob/` `/ru/voprosy-otvety/` — form + published questions."""

    intro = StreamField(IntroBlock(), blank=True, verbose_name=_("intro"))
    form_intro = RichTextField(_("text above the form"), blank=True, editor="minimal")
    thanks_text = RichTextField(
        _("thank-you text"),
        editor="minimal",
        default="<p>[[TODO: content — copywriter]]</p>",
    )

    content_panels = [
        *Page.content_panels,
        FieldPanel("intro"),
        FieldPanel("form_intro"),
        FieldPanel("thanks_text"),
    ]
    parent_page_types = ["home.HomePage"]
    subpage_types: list[str] = []
    template = "faq/faq_page.html"

    class Meta:
        verbose_name = _("questions & answers page")

    def get_body_text(self) -> str:
        return stream_plain_text(self.intro)

    def published_questions(self, section: str = "") -> list[Question]:
        qs = Question.objects.filter(status=QuestionStatus.PUBLISHED).select_related("answered_by")
        if section in QuestionSection.values:
            qs = qs.filter(section=section)
        return list(qs.order_by("-published_at")[:200])

    def get_context(self, request: Any, *args: Any, **kwargs: Any) -> dict[str, Any]:
        from apps.faq.forms import QuestionForm

        context = super().get_context(request, *args, **kwargs)
        section = request.GET.get("section", "")
        context["section_filter"] = section if section in QuestionSection.values else ""
        context["questions"] = self.published_questions(context["section_filter"])
        context["form"] = kwargs.get("form") or QuestionForm(request=request)
        context["submitted"] = kwargs.get("submitted", False)
        return context

    def serve(self, request: Any, *args: Any, **kwargs: Any) -> Any:
        from apps.faq.forms import QuestionForm
        from apps.faq.services import submit_question

        if not self.live:
            raise Http404
        is_htmx = bool(request.headers.get("HX-Request"))
        if request.method == "POST":
            if form_is_ratelimited(request, group="faq.question"):
                return TemplateResponse(request, "429.html", status=429)
            form = QuestionForm(request.POST, request=request)
            if form.is_valid():
                submit_question(form, request)
                context = self.get_context(request, submitted=True)
                template = "faq/_form.html" if is_htmx else self.template
                return TemplateResponse(request, template, context)
            context = self.get_context(request, form=form)
            template = "faq/_form.html" if is_htmx else self.template
            return TemplateResponse(request, template, context, status=400 if is_htmx else 200)
        return super().serve(request, *args, **kwargs)
