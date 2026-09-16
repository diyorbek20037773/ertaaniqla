"""Patient stories with explicit consent handling (spec §4.3 `PatientStoryPage`, F10).

A story can be drafted without consent, but **cannot go live** until `consent_obtained` is
ticked — and, for children's stories, `consent_guardian` too. The consent document is a
private Wagtail document (never served to the public, see media_library.wagtail_hooks).
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.fields import StreamField
from wagtail.models import Page
from wagtail.search import index

from apps.articles.blocks import ArticleBodyBlock, IntroBlock, stream_plain_text
from apps.core.models import BasePage, SectionKey


class StoryIndexPage(BasePage):
    """`/uz/hikoyalar/` `/ru/istorii/` — lists live stories, optional section filter."""

    intro = StreamField(IntroBlock(), blank=True, verbose_name=_("intro"))

    content_panels = [*Page.content_panels, FieldPanel("intro")]
    parent_page_types = ["home.HomePage"]
    subpage_types = ["stories.PatientStoryPage"]
    template = "stories/story_index_page.html"

    class Meta:
        verbose_name = _("stories index page")

    def get_body_text(self) -> str:
        return stream_plain_text(self.intro)

    def get_stories(self, section: str = "") -> list[PatientStoryPage]:
        qs = PatientStoryPage.objects.child_of(self).live().select_related("hero_image")
        if section in SectionKey.values:
            qs = qs.filter(section=section)
        return list(qs.order_by("-first_published_at"))

    def get_context(self, request: Any, *args: Any, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context(request, *args, **kwargs)
        section = request.GET.get("section", "")
        context["stories"] = self.get_stories(section)
        context["section_filter"] = section if section in SectionKey.values else ""
        return context


class PatientStoryPage(BasePage):
    person_display_name = models.CharField(
        _("displayed name"),
        max_length=120,
        help_text=_("May be a pseudonym. Never a full name without written consent."),
    )
    section = models.CharField(
        _("section"), max_length=16, choices=SectionKey.choices, db_index=True
    )
    diagnosis_short = models.CharField(
        _("diagnosis (short, plain words)"),
        max_length=200,
        blank=True,
        help_text=_("Written by the editor, e.g. 'breast cancer, stage 1'."),
    )
    summary = models.CharField(_("summary"), max_length=300)
    hero_image = models.ForeignKey(
        settings.WAGTAILIMAGES_IMAGE_MODEL,
        verbose_name=_("photo"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    body = StreamField(ArticleBodyBlock(), blank=True, verbose_name=_("story"))
    is_anonymised = models.BooleanField(
        _("anonymised"),
        default=True,
        help_text=_("Name changed and identifying details removed."),
    )
    consent_obtained = models.BooleanField(
        _("written consent obtained"),
        default=False,
        help_text=_("Required before publishing."),
    )
    consent_guardian = models.BooleanField(
        _("consent of the legal guardian (minors)"),
        default=False,
        help_text=_("Required for stories in the children's section."),
    )
    consent_document = models.ForeignKey(
        settings.WAGTAILDOCS_DOCUMENT_MODEL,
        verbose_name=_("consent document (private)"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text=_("Scanned consent form. Stored as a private document, never public."),
    )

    content_panels = [
        *Page.content_panels,
        MultiFieldPanel(
            [
                FieldPanel("person_display_name"),
                FieldPanel("section"),
                FieldPanel("diagnosis_short"),
                FieldPanel("summary"),
                FieldPanel("hero_image"),
            ],
            heading=_("Person"),
        ),
        FieldPanel("body"),
    ]
    settings_panels = [
        *BasePage.settings_panels,
        MultiFieldPanel(
            [
                FieldPanel("consent_obtained"),
                FieldPanel("consent_guardian"),
                FieldPanel("consent_document"),
                FieldPanel("is_anonymised"),
            ],
            heading=_("Consent (required to publish)"),
        ),
    ]
    search_fields = [
        *Page.search_fields,
        index.SearchField("summary", boost=2),
        index.SearchField("body"),
        index.FilterField("section"),
    ]

    parent_page_types = ["stories.StoryIndexPage"]
    subpage_types: list[str] = []
    template = "stories/patient_story_page.html"

    class Meta:
        verbose_name = _("patient story")
        verbose_name_plural = _("patient stories")

    jsonld_article = True

    def get_body_text(self) -> str:
        return f"{self.summary} {stream_plain_text(self.body)}"

    @property
    def section_key(self) -> str:
        return self.section

    def get_context(self, request: Any, *args: Any, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context(request, *args, **kwargs)
        context["section_key"] = self.section
        return context

    def consent_errors(self) -> dict[str, str]:
        errors: dict[str, str] = {}
        if not self.consent_obtained:
            errors["consent_obtained"] = str(
                _("The story cannot be published without the person's written consent.")
            )
        if self.section == SectionKey.CHILDREN and not self.consent_guardian:
            errors["consent_guardian"] = str(
                _("Stories of minors require the consent of the legal guardian.")
            )
        return errors

    def clean(self) -> None:
        super().clean()
        document = self.consent_document
        if document is not None and not document.is_private:
            document.is_private = True
            document.save(update_fields=["is_private"])
        if self.live:  # publishing (or re-saving a live story) — drafts may lack consent
            errors = self.consent_errors()
            if errors:
                raise ValidationError(errors)
