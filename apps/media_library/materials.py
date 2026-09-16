"""Blogger kit page (spec §10, A6, TZ «материалы для распространения»): downloadable
infographics, short videos, ready captions in uz/ru and hashtags — all CMS-managed.
`/uz/materiallar/` `/ru/materialy/`."""

from __future__ import annotations

from typing import Any

from django.utils.translation import gettext_lazy as _
from wagtail import blocks
from wagtail.admin.panels import FieldPanel
from wagtail.documents.blocks import DocumentChooserBlock
from wagtail.fields import StreamField
from wagtail.images.blocks import ImageBlock
from wagtail.models import Page
from wagtail.snippets.blocks import SnippetChooserBlock

from apps.articles.blocks import IntroBlock, stream_plain_text
from apps.core.models import BasePage


class MaterialBlock(blocks.StructBlock):
    title = blocks.CharBlock(max_length=160, label=_("Title"))
    audience = blocks.ChoiceBlock(
        choices=[
            ("bloggers", _("Volunteer bloggers")),
            ("relatives", _("Husbands, children, relatives")),
            ("parents", _("Parents")),
            ("clinics", _("Clinics (print)")),
        ],
        default="bloggers",
        label=_("Audience"),
    )
    section = blocks.ChoiceBlock(
        choices=[
            ("women", _("Women's cancer")),
            ("children", _("Childhood cancer")),
            ("both", _("Both")),
        ],
        default="both",
        label=_("Section"),
    )
    description = blocks.RichTextBlock(
        required=False, features=["bold", "italic", "link"], label=_("Description")
    )
    image = ImageBlock(required=False, label=_("Infographic / story image"))
    document = DocumentChooserBlock(required=False, label=_("Document (PDF, ZIP…)"))
    video = SnippetChooserBlock("media_library.Video", required=False, label=_("Short video"))
    caption = blocks.TextBlock(
        required=False, label=_("Ready caption"), help_text=_("Text bloggers can paste as is.")
    )
    hashtags = blocks.CharBlock(
        required=False, max_length=300, label=_("Hashtags"), help_text=_("#ertaaniqla #skrining …")
    )

    class Meta:
        icon = "download"
        label = _("Material")


class MaterialsPage(BasePage):
    intro = StreamField(IntroBlock(), blank=True, verbose_name=_("intro"))
    materials = StreamField(
        [("material", MaterialBlock())], blank=True, verbose_name=_("materials")
    )

    content_panels = [*Page.content_panels, FieldPanel("intro"), FieldPanel("materials")]
    parent_page_types = ["home.HomePage"]
    subpage_types: list[str] = []
    template = "media_library/materials_page.html"

    class Meta:
        verbose_name = _("materials page (blogger kit)")

    def get_body_text(self) -> str:
        return f"{stream_plain_text(self.intro)} {stream_plain_text(self.materials)}"

    def get_context(self, request: Any, *args: Any, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context(request, *args, **kwargs)
        audience = request.GET.get("audience", "")
        items = [
            child
            for child in self.materials
            if not audience or child.value.get("audience") == audience
        ]
        context["items"] = items
        context["audience_filter"] = audience
        return context
