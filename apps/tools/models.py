"""Tool pages (spec A1, A2, F12): stateless helpers behind waffle flags, wording in the CMS.

- `ToolsIndexPage`   /uz/vositalar/  /ru/instrumenty/
- `ScreeningToolPage` "Am I due for screening?" — rules in `screening.py`
- `SelfCheckPage`     women's symptoms / children's warning signs — scoring in `selfcheck.py`
Every tool page shows the disclaimer; feature flags default ON in dev, OFF in prod (spec §6).
"""

from __future__ import annotations

from typing import Any

from django.db import models
from django.http import Http404
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _
from waffle import flag_is_active
from wagtail import blocks
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.fields import RichTextField, StreamField
from wagtail.models import Page

from apps.articles.blocks import IntroBlock, UrgencyChoice, stream_plain_text
from apps.core.models import BasePage, SectionKey
from apps.tools import screening, selfcheck
from apps.tools.forms import TEST_LABELS, ScreeningForm, SelfCheckForm

FLAG_SCREENING = "tools_screening"
FLAG_SELFCHECK = "tools_selfcheck"
RESULT_FEATURES = ["bold", "italic", "ol", "ul", "link"]


class ToolPageMixin:
    """Feature-flag gate shared by the tool pages."""

    flag_name = ""

    def flag_enabled(self, request: Any) -> bool:
        return bool(flag_is_active(request, self.flag_name))

    def serve(self, request: Any, *args: Any, **kwargs: Any) -> Any:
        if not self.flag_enabled(request):
            raise Http404("tool disabled")
        return super().serve(request, *args, **kwargs)  # type: ignore[misc]


class ToolsIndexPage(BasePage):
    intro = StreamField(IntroBlock(), blank=True, verbose_name=_("intro"))
    disclaimer = RichTextField(
        _("disclaimer"), blank=True, editor="minimal", help_text=_("Empty = site setting.")
    )

    content_panels = [*Page.content_panels, FieldPanel("intro"), FieldPanel("disclaimer")]
    parent_page_types = ["home.HomePage"]
    subpage_types = ["tools.ScreeningToolPage", "tools.SelfCheckPage"]
    template = "tools/tools_index_page.html"

    class Meta:
        verbose_name = _("tools index page")

    def get_body_text(self) -> str:
        return stream_plain_text(self.intro)

    def get_tools(self, request: Any) -> list[Page]:
        tools = []
        for child in self.get_children().live().specific():
            if child.flag_enabled(request):
                tools.append(child)
        return tools

    def get_context(self, request: Any, *args: Any, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context(request, *args, **kwargs)
        context["tools"] = self.get_tools(request)
        return context


class ScreeningToolPage(ToolPageMixin, BasePage):
    flag_name = FLAG_SCREENING

    summary = models.CharField(_("summary"), max_length=300)
    intro = StreamField(IntroBlock(), blank=True, verbose_name=_("intro"))
    disclaimer = RichTextField(_("disclaimer"), blank=True, editor="minimal")
    text_due = RichTextField(
        _("text when a test is due"), editor="minimal", features=RESULT_FEATURES
    )
    text_ok = RichTextField(
        _("text when tests are up to date"), editor="minimal", features=RESULT_FEATURES
    )
    text_not_applicable = RichTextField(
        _("text when no test applies at this age"), editor="minimal", features=RESULT_FEATURES
    )
    text_hpv_interval = RichTextField(
        _("HPV test interval note"),
        editor="minimal",
        features=RESULT_FEATURES,
        help_text=_("The TZ gives no interval for the HPV test — the doctor decides."),
    )
    where_page = models.ForeignKey(
        "wagtailcore.Page",
        verbose_name=_("'where to go' page"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    content_panels = [
        *Page.content_panels,
        FieldPanel("summary"),
        FieldPanel("intro"),
        MultiFieldPanel(
            [
                FieldPanel("text_due"),
                FieldPanel("text_ok"),
                FieldPanel("text_not_applicable"),
                FieldPanel("text_hpv_interval"),
            ],
            heading=_("Result texts"),
        ),
        FieldPanel("where_page"),
        FieldPanel("disclaimer"),
    ]
    parent_page_types = ["tools.ToolsIndexPage"]
    subpage_types: list[str] = []
    template = "tools/screening_tool_page.html"

    class Meta:
        verbose_name = _("screening helper page")

    def get_body_text(self) -> str:
        return f"{self.summary} {stream_plain_text(self.intro)}"

    @property
    def section_key(self) -> str:
        return SectionKey.WOMEN

    def get_context(self, request: Any, *args: Any, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context(request, *args, **kwargs)
        context["section_key"] = self.section_key
        form = ScreeningForm(request.POST if request.method == "POST" else None)
        context["form"] = form
        context["test_labels"] = TEST_LABELS
        if request.method == "POST" and form.is_valid():
            results = screening.evaluate(form.cleaned_data["age"], form.last_tests())
            context["results"] = results
            context["any_due"] = screening.any_due(results)
            context["any_applies"] = any(r.applies for r in results)
        return context

    def serve(self, request: Any, *args: Any, **kwargs: Any) -> Any:
        if not self.flag_enabled(request):
            raise Http404("tool disabled")
        if request.method == "POST" and request.headers.get("HX-Request"):
            return TemplateResponse(
                request, "tools/_screening_result.html", self.get_context(request)
            )
        return Page.serve(self, request, *args, **kwargs)


class SelfCheckItemBlock(blocks.StructBlock):
    text = blocks.CharBlock(max_length=300, label=_("Sign / symptom"))
    urgency = UrgencyChoice(default="soon", label=_("Urgency if ticked"))

    class Meta:
        icon = "tick"


class SelfCheckKind(models.TextChoices):
    WOMEN = SectionKey.WOMEN.value, _("Women's symptom self-check")
    CHILDREN = SectionKey.CHILDREN.value, _("Warning signs in children (for parents)")


class SelfCheckPage(ToolPageMixin, BasePage):
    flag_name = FLAG_SELFCHECK

    kind = models.CharField(_("checklist"), max_length=16, choices=SelfCheckKind.choices)
    summary = models.CharField(_("summary"), max_length=300)
    intro = StreamField(IntroBlock(), blank=True, verbose_name=_("intro"))
    items = StreamField(
        [("item", SelfCheckItemBlock())], blank=True, verbose_name=_("checklist items")
    )
    result_none = RichTextField(
        _("result: nothing ticked"), editor="minimal", features=RESULT_FEATURES
    )
    result_routine = RichTextField(_("result: routine"), editor="minimal", features=RESULT_FEATURES)
    result_soon = RichTextField(_("result: soon"), editor="minimal", features=RESULT_FEATURES)
    result_urgent = RichTextField(_("result: urgent"), editor="minimal", features=RESULT_FEATURES)
    disclaimer = RichTextField(_("disclaimer"), blank=True, editor="minimal")
    where_page = models.ForeignKey(
        "wagtailcore.Page",
        verbose_name=_("'where to go' page"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    content_panels = [
        *Page.content_panels,
        FieldPanel("kind"),
        FieldPanel("summary"),
        FieldPanel("intro"),
        FieldPanel("items"),
        MultiFieldPanel(
            [
                FieldPanel("result_none"),
                FieldPanel("result_routine"),
                FieldPanel("result_soon"),
                FieldPanel("result_urgent"),
            ],
            heading=_("Result texts"),
        ),
        FieldPanel("where_page"),
        FieldPanel("disclaimer"),
    ]
    parent_page_types = ["tools.ToolsIndexPage"]
    subpage_types: list[str] = []
    template = "tools/self_check_page.html"

    class Meta:
        verbose_name = _("self-check page")

    def get_body_text(self) -> str:
        return f"{self.summary} {stream_plain_text(self.intro)} {stream_plain_text(self.items)}"

    @property
    def section_key(self) -> str:
        return self.kind

    def item_choices(self) -> list[tuple[str, str]]:
        return [(str(child.id), str(child.value["text"])) for child in self.items]

    def scoring_items(self) -> list[selfcheck.Item]:
        return [selfcheck.Item(str(child.id), str(child.value["urgency"])) for child in self.items]

    def result_text(self, level: str) -> str:
        return str(getattr(self, f"result_{level}", "") or "")

    def get_context(self, request: Any, *args: Any, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context(request, *args, **kwargs)
        context["section_key"] = self.section_key
        form = SelfCheckForm(
            self.item_choices(), request.POST if request.method == "POST" else None
        )
        context["form"] = form
        if request.method == "POST" and form.is_valid():
            result = selfcheck.score(self.scoring_items(), list(form.cleaned_data["items"]))
            context["result"] = result
            context["result_text"] = self.result_text(result.level)
        return context

    def serve(self, request: Any, *args: Any, **kwargs: Any) -> Any:
        if not self.flag_enabled(request):
            raise Http404("tool disabled")
        if request.method == "POST" and request.headers.get("HX-Request"):
            return TemplateResponse(
                request, "tools/_self_check_result.html", self.get_context(request)
            )
        return Page.serve(self, request, *args, **kwargs)
