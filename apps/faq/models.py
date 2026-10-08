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
from wagtail import blocks
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.fields import RichTextField, StreamField
from wagtail.models import Page
from wagtail.search import index
from wagtail.snippets.models import register_snippet

from apps.articles.blocks import IntroBlock, stream_plain_text
from apps.core.antispam import form_is_ratelimited, retry_initial
from apps.core.fields import EncryptedCharField
from apps.core.models import BasePage, SectionKey, TimeStampedModel, Topic, topic_from_request


class QuestionSection(models.TextChoices):
    WOMEN = SectionKey.WOMEN.value, SectionKey.WOMEN.label
    CHILDREN = SectionKey.CHILDREN.value, SectionKey.CHILDREN.label
    OTHER = "other", _("Other")


class QuestionCategory(models.TextChoices):
    """The «Mavzular» side list of the question page (final design, D-081)."""

    GENERAL = "general", _("General information")
    SIGNS = "signs", _("Signs and causes")
    SCREENING = "screening", _("Screening")
    TREATMENT = "treatment", _("Treatment")


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
    topic = models.CharField(
        _("topic"),
        max_length=16,
        choices=Topic.choices,
        blank=True,
        db_index=True,
        help_text=_("Which disease page shows the published question."),
    )
    category = models.CharField(
        _("category"),
        max_length=16,
        choices=QuestionCategory.choices,
        blank=True,
        db_index=True,
        help_text=_("Groups published questions in the side list of the question page."),
    )
    article = models.ForeignKey(
        "wagtailcore.Page",
        verbose_name=_("full article"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text=_("Optional «Full article» link under the answer."),
    )
    is_featured = models.BooleanField(
        _("most asked"),
        default=False,
        help_text=_("Shown as a card under «Most asked questions» (published questions only)."),
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
                FieldPanel("topic"),
                FieldPanel("category"),
                FieldPanel("is_featured"),
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
            [
                FieldPanel("public_question"),
                FieldPanel("answer"),
                FieldPanel("answered_by"),
                FieldPanel("article"),
            ],
            heading=_("Answer"),
        ),
    ]
    search_fields = [
        index.SearchField("text"),
        index.SearchField("answer"),
        index.FilterField("status"),
        index.FilterField("section"),
        index.FilterField("topic"),
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


class InfoCardBlock(blocks.StructBlock):
    topic = blocks.ChoiceBlock(
        choices=[("", _("All topics")), *Topic.choices],
        required=False,
        label=_("Topic"),
    )
    title = blocks.CharBlock(max_length=80, label=_("Title"))
    page = blocks.PageChooserBlock(required=False, label=_("Page"))
    anchor = blocks.CharBlock(
        required=False, max_length=80, label=_("Anchor on the page"), help_text=_("Without #.")
    )
    url = blocks.URLBlock(required=False, label=_("or external URL"))

    class Meta:
        icon = "doc-full"
        label = _("Information card")


class FAQPage(BasePage):
    """`/uz/savol-javob/` `/ru/voprosy-otvety/` — form + published questions."""

    intro = StreamField(IntroBlock(), blank=True, verbose_name=_("intro"))
    form_intro = RichTextField(_("text above the form"), blank=True, editor="minimal")
    thanks_text = RichTextField(
        _("thank-you text"),
        editor="minimal",
        default="<p>[[TODO: content — copywriter]]</p>",
    )
    info_cards = StreamField(
        [("card", InfoCardBlock())],
        blank=True,
        verbose_name=_("«Information you should know» cards"),
        help_text=_("Short links to pages, shown next to the most asked questions."),
    )

    content_panels = [
        *Page.content_panels,
        FieldPanel("intro"),
        FieldPanel("form_intro"),
        FieldPanel("thanks_text"),
        FieldPanel("info_cards"),
    ]
    parent_page_types = ["home.HomePage"]
    subpage_types: list[str] = []
    template = "faq/faq_page.html"

    class Meta:
        verbose_name = _("questions & answers page")

    def get_body_text(self) -> str:
        return stream_plain_text(self.intro)

    def published_questions(
        self, section: str = "", topic: str = "", query: str = ""
    ) -> list[Question]:
        qs = Question.objects.filter(status=QuestionStatus.PUBLISHED).select_related(
            "answered_by", "article"
        )
        if section in QuestionSection.values:
            qs = qs.filter(section=section)
        if topic in Topic.values:
            qs = qs.filter(topic=topic)
        if query:
            qs = qs.filter(
                models.Q(public_question__icontains=query)
                | models.Q(text__icontains=query)
                | models.Q(answer__icontains=query)
            )
        return list(qs.order_by("-published_at")[:200])

    def info_cards_for(self, topic: str) -> list[Any]:
        """«Siz bilishingiz lozim bo'lgan ma'lumotlar» cards of the topic (all when none)."""
        return [
            block.value
            for block in self.info_cards
            if not topic or block.value.get("topic") in ("", topic)
        ]

    def get_context(self, request: Any, *args: Any, **kwargs: Any) -> dict[str, Any]:
        from apps.faq.forms import QuestionForm

        context = super().get_context(request, *args, **kwargs)
        section = request.GET.get("section", "")
        topic = topic_from_request(request)
        query = " ".join(request.GET.get("q", "").split())[:100]
        context["section_filter"] = section if section in QuestionSection.values else ""
        context["topic"] = topic
        context["topic_label"] = Topic(topic).label if topic else ""
        context["topics"] = Topic.choices
        context["query"] = query
        questions = self.published_questions(context["section_filter"], topic, query)
        # «Mavzular» side list (final design, D-081): counts per category, ?category= filters
        category = request.GET.get("category", "")
        category = category if category in QuestionCategory.values else ""
        counts = dict.fromkeys(QuestionCategory.values, 0)
        for question in questions:
            if question.category in counts:
                counts[question.category] += 1
        context["category"] = category
        context["categories"] = [
            (value, label, counts[value]) for value, label in QuestionCategory.choices
        ]
        context["all_count"] = len(questions)
        context["questions"] = (
            [q for q in questions if q.category == category] if category else questions
        )
        context["featured_questions"] = [q for q in context["questions"] if q.is_featured][:6]
        context["info_cards"] = self.info_cards_for(topic)
        # final design (D-081): the landing's «Yo'nalishlar» cards repeat under the questions
        home = self.get_parent().specific
        context["direction_cards"] = getattr(home, "directions", None)
        context["home_page"] = home
        context["faq_page"] = self
        # FAQPage JSON-LD mirrors the visible (filtered) Q&A list — spec §10
        from apps.core import seo

        faq = seo.faq_ld(context["questions"])
        if faq:
            context["jsonld"] = [*context.get("jsonld", []), faq]
        context["form"] = kwargs.get("form") or QuestionForm(
            request=request, initial={"topic": topic}
        )
        context["submitted"] = kwargs.get("submitted", False)
        context["rate_limited"] = kwargs.get("rate_limited", False)
        return context

    def serve(self, request: Any, *args: Any, **kwargs: Any) -> Any:
        from apps.faq.forms import QuestionForm
        from apps.faq.services import submit_question

        if not self.live:
            raise Http404
        is_htmx = bool(request.headers.get("HX-Request"))
        if request.method == "POST":
            if form_is_ratelimited(request, group="faq.question"):
                if is_htmx:  # EA-03: say why inside the form and keep the visitor's text
                    form = QuestionForm(initial=retry_initial(request), request=request)
                    context = self.get_context(request, form=form, rate_limited=True)
                    return TemplateResponse(request, "faq/_form.html", context, status=429)
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
