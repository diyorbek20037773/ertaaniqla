"""Every StreamField block of spec §4.3 — all content blocks live here.

Each block has a template in `templates/blocks/` and a `clean()` / render test in
`tests/articles/test_blocks.py`. Visual styling is confined to `templates/components/` and
`static/src/tokens.css` (DECISIONS D-003), so the block templates only carry structure.
"""

from __future__ import annotations

import re
from typing import Any

from django.core.exceptions import ValidationError
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _
from wagtail import blocks
from wagtail.blocks.struct_block import StructBlockValidationError
from wagtail.contrib.typed_table_block.blocks import TypedTableBlock
from wagtail.documents.blocks import DocumentChooserBlock
from wagtail.images.blocks import ImageBlock
from wagtail.snippets.blocks import SnippetChooserBlock

from apps.articles.embeds import parse_embed_url

RICH_TEXT_FEATURES = [
    "h2",
    "h3",
    "bold",
    "italic",
    "ol",
    "ul",
    "link",
    "document-link",
    "image",
    "embed",
]
LIST_FEATURES = ["bold", "italic", "ol", "ul", "link"]
INLINE_FEATURES = ["bold", "italic", "link"]


# ---------------------------------------------------------------------------
# Small reusable pieces
# ---------------------------------------------------------------------------
class LinkBlock(blocks.StructBlock):
    """Internal page or external URL (at most one). Empty = no link."""

    page = blocks.PageChooserBlock(required=False, label=_("Page"))
    url = blocks.URLBlock(required=False, label=_("External URL"))

    class Meta:
        icon = "link"
        label = _("Link")

    def clean(self, value: Any) -> Any:
        cleaned = super().clean(value)
        if cleaned.get("page") and cleaned.get("url"):
            raise StructBlockValidationError(
                non_block_errors=[ValidationError(_("Choose either a page or a URL, not both."))]
            )
        return cleaned


def link_href(value: Any) -> str:
    """Resolve a LinkBlock value to a URL ('' when empty)."""
    if not value:
        return ""
    page = value.get("page")
    if page is not None:
        return str(page.url or "")
    return str(value.get("url") or "")


# ---------------------------------------------------------------------------
# Blocks of spec §4.3 (in table order)
# ---------------------------------------------------------------------------
class RichTextBlock(blocks.RichTextBlock):
    class Meta:
        icon = "doc-full"
        label = _("Text")
        template = "blocks/rich_text.html"


class CalloutKind(blocks.ChoiceBlock):
    choices = [
        ("info", _("Info")),
        ("warning", _("Warning")),
        ("danger", _("Danger — do not delay")),
        ("success", _("Success / good news")),
        ("reassurance", _("Reassurance (this sign is not always cancer)")),
    ]


class CalloutBlock(blocks.StructBlock):
    kind = CalloutKind(default="info", label=_("Kind"))
    title = blocks.CharBlock(required=False, max_length=120, label=_("Title"))
    text = blocks.RichTextBlock(features=LIST_FEATURES, label=_("Text"))

    class Meta:
        icon = "warning"
        label = _("Callout")
        template = "blocks/callout.html"


class ColumnBlock(blocks.StructBlock):
    title = blocks.CharBlock(max_length=120, label=_("Column title"))
    items = blocks.RichTextBlock(features=LIST_FEATURES, label=_("Items (list)"))

    class Meta:
        icon = "list-ul"


class ThreeColumnsBlock(blocks.StructBlock):
    columns = blocks.ListBlock(ColumnBlock(), min_num=3, max_num=3, label=_("Columns"))

    class Meta:
        icon = "table"
        label = _("Three columns")
        template = "blocks/three_columns.html"


class TwoColumnsBlock(blocks.StructBlock):
    columns = blocks.ListBlock(ColumnBlock(), min_num=2, max_num=2, label=_("Columns"))

    class Meta:
        icon = "table"
        label = _("Two columns")
        template = "blocks/two_columns.html"


class StepBlock(blocks.StructBlock):
    number = blocks.CharBlock(
        required=False,
        max_length=4,
        label=_("Number"),
        help_text=_("Leave empty to number automatically (01, 02, …)."),
    )
    title = blocks.CharBlock(max_length=160, label=_("Title"))
    text = blocks.RichTextBlock(features=LIST_FEATURES, label=_("Text"))
    deadline = blocks.CharBlock(
        required=False,
        max_length=160,
        label=_("Deadline / timing"),
        help_text=_("E.g. referral deadline per PP-402. Shown as a separate line."),
    )
    link = LinkBlock(required=False, label=_("Link"))

    class Meta:
        icon = "order"


class StepsBlock(blocks.StructBlock):
    title = blocks.CharBlock(required=False, max_length=160, label=_("Heading"))
    steps = blocks.ListBlock(StepBlock(), min_num=1, label=_("Steps"))

    class Meta:
        icon = "order"
        label = _("Steps (patient route, self-exam guide)")
        template = "blocks/steps.html"


class CardBlock(blocks.StructBlock):
    image = ImageBlock(required=False, label=_("Image"))
    icon = blocks.CharBlock(
        required=False,
        max_length=40,
        label=_("Icon name"),
        help_text=_("Optional icon identifier for the designer (e.g. 'dna', 'age')."),
    )
    title = blocks.CharBlock(max_length=160, label=_("Title"))
    text = blocks.RichTextBlock(required=False, features=LIST_FEATURES, label=_("Text"))
    link = LinkBlock(required=False, label=_("Link"))

    class Meta:
        icon = "form"


class CardsGridBlock(blocks.StructBlock):
    title = blocks.CharBlock(required=False, max_length=160, label=_("Heading"))
    cards = blocks.ListBlock(CardBlock(), min_num=1, label=_("Cards"))

    class Meta:
        icon = "grip"
        label = _("Cards grid")
        template = "blocks/cards_grid.html"


class UrgencyChoice(blocks.ChoiceBlock):
    choices = [
        ("routine", _("Routine — mention at the next visit")),
        ("soon", _("Soon — see a doctor within days")),
        ("urgent", _("Urgent — see a doctor now")),
    ]


class SymptomBlock(blocks.StructBlock):
    symptom = blocks.CharBlock(max_length=200, label=_("Symptom"))
    urgency = UrgencyChoice(default="soon", label=_("Urgency"))
    explanation = blocks.RichTextBlock(
        required=False, features=INLINE_FEATURES, label=_("Explanation")
    )

    class Meta:
        icon = "warning"


class SymptomListBlock(blocks.StructBlock):
    title = blocks.CharBlock(required=False, max_length=160, label=_("Heading"))
    symptoms = blocks.ListBlock(SymptomBlock(), min_num=1, label=_("Symptoms"))

    class Meta:
        icon = "list-ul"
        label = _("Symptom list")
        template = "blocks/symptom_list.html"


class StatBlock(blocks.StructBlock):
    value = blocks.CharBlock(
        max_length=40, label=_("Value"), help_text=_("E.g. '1 из 8' or '45–65'.")
    )
    label = blocks.CharBlock(max_length=200, label=_("Label"))
    source = blocks.CharBlock(required=False, max_length=200, label=_("Source"))
    year = blocks.IntegerBlock(required=False, min_value=1990, max_value=2100, label=_("Year"))

    class Meta:
        icon = "snippet"
        label = _("Statistic")
        template = "blocks/stat.html"


class VideoBlock(blocks.StructBlock):
    video = SnippetChooserBlock(
        "media_library.Video", required=False, label=_("Video from library")
    )
    external_url = blocks.URLBlock(
        required=False,
        label=_("External URL"),
        help_text=_("YouTube, Telegram, Instagram or TikTok link (used when no library video)."),
    )
    caption = blocks.CharBlock(required=False, max_length=300, label=_("Caption"))
    transcript = blocks.RichTextBlock(required=False, features=LIST_FEATURES, label=_("Transcript"))

    class Meta:
        icon = "media"
        label = _("Video")
        template = "blocks/video.html"

    def clean(self, value: Any) -> Any:
        cleaned = super().clean(value)
        if not cleaned.get("video") and not cleaned.get("external_url"):
            raise StructBlockValidationError(
                non_block_errors=[ValidationError(_("Choose a video or enter an external URL."))]
            )
        url = cleaned.get("external_url")
        if url and parse_embed_url(url) is None:
            raise StructBlockValidationError(
                block_errors={
                    "external_url": ValidationError(
                        _("Only YouTube, Telegram, Instagram and TikTok links are supported.")
                    )
                }
            )
        return cleaned

    def get_context(self, value: Any, parent_context: Any = None) -> dict[str, Any]:
        context: dict[str, Any] = super().get_context(value, parent_context=parent_context)
        video = value.get("video")
        url = value.get("external_url") or (
            video.external_url if video and video.is_external else ""
        )
        context["embed"] = parse_embed_url(url) if url else None
        return context


class GalleryImageBlock(blocks.StructBlock):
    image = ImageBlock(label=_("Image"))
    caption = blocks.CharBlock(required=False, max_length=300, label=_("Caption"))

    class Meta:
        icon = "image"


class ImageGalleryBlock(blocks.StructBlock):
    title = blocks.CharBlock(required=False, max_length=160, label=_("Heading"))
    images = blocks.ListBlock(GalleryImageBlock(), min_num=1, label=_("Images"))
    downloadable = blocks.BooleanBlock(
        required=False, default=False, label=_("Allow download (infographics)")
    )

    class Meta:
        icon = "image"
        label = _("Image gallery / infographics")
        template = "blocks/image_gallery.html"


class DocumentDownloadBlock(blocks.StructBlock):
    document = DocumentChooserBlock(label=_("Document"))
    description = blocks.CharBlock(required=False, max_length=300, label=_("Description"))

    class Meta:
        icon = "doc-full-inverse"
        label = _("Document download")
        template = "blocks/document_download.html"


class FAQItemBlock(blocks.StructBlock):
    question = blocks.CharBlock(max_length=300, label=_("Question"))
    answer = blocks.RichTextBlock(features=LIST_FEATURES, label=_("Answer"))

    class Meta:
        icon = "help"


class FAQAccordionBlock(blocks.StructBlock):
    title = blocks.CharBlock(required=False, max_length=160, label=_("Heading"))
    items = blocks.ListBlock(FAQItemBlock(), min_num=1, label=_("Questions"))

    class Meta:
        icon = "help"
        label = _("FAQ accordion / questions to ask the doctor")
        template = "blocks/faq_accordion.html"


class GlossaryTermsBlock(blocks.StructBlock):
    title = blocks.CharBlock(required=False, max_length=160, label=_("Heading"))
    terms = blocks.ListBlock(SnippetChooserBlock("glossary.Term"), min_num=1, label=_("Terms"))

    class Meta:
        icon = "openquote"
        label = _("Glossary terms")
        template = "blocks/glossary_terms.html"


def region_choices() -> list[tuple[str, Any]]:
    from apps.directory.models import Region

    return [
        ("", _("All regions")),
        *((r.code, f"{r.name_uz} / {r.name_ru}") for r in Region.objects.all()),
    ]


def institution_kind_choices() -> list[tuple[str, Any]]:
    from apps.directory.models import InstitutionKind

    return [("", _("All types")), *InstitutionKind.choices]


class InstitutionListBlock(blocks.StructBlock):
    title = blocks.CharBlock(required=False, max_length=160, label=_("Heading"))
    region = blocks.ChoiceBlock(choices=region_choices, required=False, label=_("Region"))
    kind = blocks.ChoiceBlock(choices=institution_kind_choices, required=False, label=_("Type"))
    free_only = blocks.BooleanBlock(
        required=False, default=False, label=_("Only free under the state programme")
    )
    limit = blocks.IntegerBlock(default=20, min_value=1, max_value=200, label=_("Max items"))

    class Meta:
        icon = "site"
        label = _("Institution list")
        template = "blocks/institution_list.html"

    def get_context(self, value: Any, parent_context: Any = None) -> dict[str, Any]:
        from apps.directory.services import institutions_for_block

        context: dict[str, Any] = super().get_context(value, parent_context=parent_context)
        context["institutions"] = institutions_for_block(value)
        return context


class CTABlock(blocks.StructBlock):
    text = blocks.RichTextBlock(required=False, features=INLINE_FEATURES, label=_("Text"))
    button_label = blocks.CharBlock(max_length=80, label=_("Button label"))
    link = LinkBlock(label=_("Link"))
    style = blocks.ChoiceBlock(
        choices=[("primary", _("Primary (section colour)")), ("secondary", _("Secondary"))],
        default="primary",
        label=_("Style"),
    )

    class Meta:
        icon = "link-external"
        label = _("Call to action")
        template = "blocks/cta.html"

    def clean(self, value: Any) -> Any:
        cleaned = super().clean(value)
        if not link_href(cleaned.get("link")):
            raise StructBlockValidationError(
                block_errors={"link": ValidationError(_("A page or a URL is required."))}
            )
        return cleaned


class QuoteBlock(blocks.StructBlock):
    text = blocks.TextBlock(label=_("Quote"))
    author = blocks.CharBlock(required=False, max_length=120, label=_("Author"))
    role = blocks.CharBlock(required=False, max_length=160, label=_("Role / organisation"))

    class Meta:
        icon = "openquote"
        label = _("Quote")
        template = "blocks/quote.html"


class TableBlock(TypedTableBlock):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            [
                ("text", blocks.CharBlock(label=_("Text"))),
                ("numeric", blocks.FloatBlock(label=_("Number"))),
                ("rich_text", blocks.RichTextBlock(features=INLINE_FEATURES, label=_("Rich text"))),
            ],
            **kwargs,
        )

    class Meta:
        icon = "table"
        label = _("Table")
        template = "blocks/table.html"


class EmbedBlock(blocks.StructBlock):
    url = blocks.URLBlock(
        label=_("URL"),
        help_text=_("YouTube, Telegram post, Instagram post/reel or TikTok video."),
    )
    caption = blocks.CharBlock(required=False, max_length=300, label=_("Caption"))

    class Meta:
        icon = "media"
        label = _("Embed (YouTube / Telegram / Instagram / TikTok)")
        template = "blocks/embed.html"

    def clean(self, value: Any) -> Any:
        cleaned = super().clean(value)
        if parse_embed_url(cleaned["url"]) is None:
            raise StructBlockValidationError(
                block_errors={
                    "url": ValidationError(
                        _("Only YouTube, Telegram, Instagram and TikTok links are supported.")
                    )
                }
            )
        return cleaned

    def get_context(self, value: Any, parent_context: Any = None) -> dict[str, Any]:
        context: dict[str, Any] = super().get_context(value, parent_context=parent_context)
        context["embed"] = parse_embed_url(value["url"])
        return context


# ---------------------------------------------------------------------------
# Stream definitions
# ---------------------------------------------------------------------------
class ArticleBodyBlock(blocks.StreamBlock):
    rich_text = RichTextBlock(features=RICH_TEXT_FEATURES)
    callout = CalloutBlock()
    three_columns = ThreeColumnsBlock()
    two_columns = TwoColumnsBlock()
    steps = StepsBlock()
    cards_grid = CardsGridBlock()
    symptom_list = SymptomListBlock()
    stat = StatBlock()
    video = VideoBlock()
    image_gallery = ImageGalleryBlock()
    document_download = DocumentDownloadBlock()
    faq_accordion = FAQAccordionBlock()
    glossary_terms = GlossaryTermsBlock()
    institution_list = InstitutionListBlock()
    cta = CTABlock()
    quote = QuoteBlock()
    table = TableBlock()
    embed = EmbedBlock()


class IntroBlock(blocks.StreamBlock):
    """Lighter stream for index pages (section / topic intros, home)."""

    rich_text = RichTextBlock(features=RICH_TEXT_FEATURES)
    callout = CalloutBlock()
    cards_grid = CardsGridBlock()
    stat = StatBlock()
    cta = CTABlock()
    video = VideoBlock()


# ---------------------------------------------------------------------------
# Plain text extraction (reading time, search)
# ---------------------------------------------------------------------------
_SKIP_KEYS = frozenset(
    {
        "url",
        "external_url",
        "page",
        "image",
        "document",
        "video",
        "icon",
        "kind",
        "urgency",
        "style",
        "region",
        "number",
        "limit",
        "free_only",
        "downloadable",
        "terms",
    }
)


def _collect_strings(data: Any, out: list[str]) -> None:
    if isinstance(data, str):
        out.append(data)
    elif isinstance(data, dict):
        for key, item in data.items():
            if key in _SKIP_KEYS:
                continue
            _collect_strings(item, out)
    elif isinstance(data, list | tuple):
        for item in data:
            _collect_strings(item, out)


def stream_plain_text(stream_value: Any) -> str:
    """Approximate plain text of a StreamValue (HTML stripped, ids and URLs skipped)."""
    if not stream_value:
        return ""
    parts: list[str] = []
    _collect_strings(stream_value.get_prep_value(), parts)
    text = " ".join(strip_tags(p) for p in parts)
    return re.sub(r"\s+", " ", text).strip()
