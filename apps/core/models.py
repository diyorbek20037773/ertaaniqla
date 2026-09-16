"""Abstract base models shared by every app (spec §4.3 `BasePage`) and site settings."""

from __future__ import annotations

import math
import re
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.db import models
from django.utils.html import strip_tags
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.contrib.settings.models import BaseSiteSetting, register_setting
from wagtail.fields import RichTextField
from wagtail.models import Page

if TYPE_CHECKING:
    from apps.sections.models import SectionIndexPage

WORDS_PER_MINUTE = 180  # slow, plain-language reading (anxious / low-literacy audience)


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(_("created at"), auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class SectionKey(models.TextChoices):
    WOMEN = "women", _("Women's cancer")
    CHILDREN = "children", _("Childhood cancer")


class BasePage(Page):
    """Every content page. Adds SEO extras, medical review metadata and section lookup."""

    og_image = models.ForeignKey(
        settings.WAGTAILIMAGES_IMAGE_MODEL,
        verbose_name=_("social sharing image"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text=_(
            "Shown when the page is shared in Telegram/Facebook. Generated automatically if empty."
        ),
    )
    og_image_generated = models.ImageField(
        _("generated sharing image"),
        upload_to="og/",
        blank=True,
        editable=False,
        help_text=_("Rendered automatically on publish when no sharing image is chosen."),
    )
    story_image_generated = models.ImageField(
        _("generated story image (1080×1920)"),
        upload_to="story/",
        blank=True,
        editable=False,
        help_text=_("Vertical image for Instagram/TikTok stories, rendered on publish."),
    )
    noindex = models.BooleanField(
        _("hide from search engines"),
        default=False,
        help_text=_("Adds a noindex meta tag. Use for drafts-in-public and utility pages."),
    )
    last_reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("medically reviewed by"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    last_reviewed_at = models.DateField(_("reviewed on"), null=True, blank=True)
    medically_verified = models.BooleanField(
        _("medically verified"),
        default=False,
        help_text=_("Shows the 'Verified by a doctor' badge. Set by the medical reviewer."),
    )

    review_panels = [
        MultiFieldPanel(
            [
                FieldPanel("medically_verified"),
                FieldPanel("last_reviewed_by"),
                FieldPanel("last_reviewed_at"),
            ],
            heading=_("Medical review"),
        ),
    ]
    seo_extra_panels = [FieldPanel("og_image"), FieldPanel("noindex")]

    promote_panels = [*Page.promote_panels, *seo_extra_panels]
    settings_panels = [*Page.settings_panels, *review_panels]

    class Meta:
        abstract = True

    # --- section / theming ------------------------------------------------------------------
    def get_section(self) -> SectionIndexPage | None:
        """Nearest `SectionIndexPage` ancestor (or self), None outside the two sections."""
        from apps.sections.models import SectionIndexPage

        page = self.get_ancestors(inclusive=True).type(SectionIndexPage).order_by("-depth").first()
        return page.specific if page else None

    @property
    def section_key(self) -> str:
        section = self.get_section()
        return section.section_key if section else ""

    # --- reading time ---------------------------------------------------------------------------
    def get_body_text(self) -> str:
        """Plain text used for reading time and search. Subclasses with a StreamField override."""
        return ""

    @property
    def word_count(self) -> int:
        text = strip_tags(self.get_body_text())
        return len(re.findall(r"\w+", text))

    @property
    def reading_time(self) -> int:
        """Minutes, minimum 1."""
        return max(1, math.ceil(self.word_count / WORDS_PER_MINUTE))

    # --- verification badge ---------------------------------------------------------------------
    @property
    def verified_badge(self) -> dict[str, Any] | None:
        if not self.medically_verified:
            return None
        reviewer = self.last_reviewed_by
        return {
            "name": reviewer.display_name if reviewer else "",
            "organisation": getattr(reviewer, "organisation", "") if reviewer else "",
            "date": self.last_reviewed_at,
        }

    @property
    def og_image_generated_url(self) -> str:
        """URL of the auto-generated OG image (base.html falls back to it when no og_image)."""
        if self.og_image_generated:
            try:
                return str(self.og_image_generated.url)
            except ValueError:  # pragma: no cover - file missing on disk
                return ""
        return ""

    @property
    def story_image_generated_url(self) -> str:
        if self.story_image_generated:
            try:
                return str(self.story_image_generated.url)
            except ValueError:  # pragma: no cover - file missing on disk
                return ""
        return ""

    # --- structured data (spec §10) ------------------------------------------------------------
    jsonld_article = False  # subclasses that are articles set True

    def get_jsonld(self, request: Any) -> list[dict[str, Any]]:
        """JSON-LD graph items for this page; subclasses extend."""
        from apps.core import seo
        from apps.core.templatetags.core_tags import site_root_url

        base = site_root_url(request)
        language = str(self.locale.language_code)
        settings_obj = None
        try:
            settings_obj = SiteSettings.for_request(request)
        except Exception:  # pragma: no cover - no Site configured
            settings_obj = None
        crumbs = list(self.get_ancestors(inclusive=True).live().filter(depth__gte=2).specific())
        items = [
            seo.organization_ld(base, language, settings_obj),
            seo.breadcrumb_ld(crumbs, base),
            seo.page_ld(self, base, language, article=self.jsonld_article),
        ]
        return [item for item in items if item]

    def get_context(self, request: Any, *args: Any, **kwargs: Any) -> dict[str, Any]:
        context: dict[str, Any] = super().get_context(request, *args, **kwargs)
        context["section"] = self.get_section()
        context["section_key"] = self.section_key
        context["jsonld"] = self.get_jsonld(request)
        return context


@register_setting(icon="cog")
class SiteSettings(BaseSiteSetting):
    """Editor-controlled global values (spec §4.3 'Site settings')."""

    hotline_phone = models.CharField(
        _("hotline phone"), max_length=32, blank=True, help_text=_("Format: +998 XX XXX-XX-XX")
    )
    hotline_phone_secondary = models.CharField(_("second hotline phone"), max_length=32, blank=True)
    telegram_url = models.URLField(_("Telegram channel"), blank=True)
    instagram_url = models.URLField(_("Instagram"), blank=True)
    facebook_url = models.URLField(_("Facebook"), blank=True)
    youtube_url = models.URLField(_("YouTube"), blank=True)
    tiktok_url = models.URLField(_("TikTok"), blank=True)
    footer_text_uz = models.TextField(_("footer text (uz)"), blank=True)
    footer_text_ru = models.TextField(_("footer text (ru)"), blank=True)
    disclaimer_uz = models.TextField(
        _("medical disclaimer (uz)"),
        default=(
            "Sayt tashxis qoʻymaydi; shifokorga murojaat qiling. [[TODO: content — copywriter]]"
        ),
    )
    disclaimer_ru = models.TextField(
        _("medical disclaimer (ru)"),
        default="Сайт не ставит диагноз; обратитесь к врачу. [[TODO: content — copywriter]]",
    )
    emergency_banner_enabled = models.BooleanField(_("show emergency banner"), default=False)
    emergency_banner_uz = models.CharField(_("emergency banner (uz)"), max_length=300, blank=True)
    emergency_banner_ru = models.CharField(_("emergency banner (ru)"), max_length=300, blank=True)
    emergency_banner_link = models.URLField(_("emergency banner link"), blank=True)
    metrika_id = models.CharField(_("Yandex.Metrika counter id"), max_length=32, blank=True)
    privacy_page = models.ForeignKey(
        "wagtailcore.Page",
        verbose_name=_("privacy policy page"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text=_("Linked from the consent banner and every form."),
    )
    legal_text_uz = RichTextField(_("legal / privacy text (uz)"), blank=True, editor="default")
    legal_text_ru = RichTextField(_("legal / privacy text (ru)"), blank=True, editor="default")
    partner_agency_logo = models.ForeignKey(
        settings.WAGTAILIMAGES_IMAGE_MODEL,
        verbose_name=_("Agency logo"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    partner_yandex_logo = models.ForeignKey(
        settings.WAGTAILIMAGES_IMAGE_MODEL,
        verbose_name=_("Yandex logo"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    partner_hamroh_logo = models.ForeignKey(
        settings.WAGTAILIMAGES_IMAGE_MODEL,
        verbose_name=_("Hamroh logo"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    panels = [
        MultiFieldPanel(
            [FieldPanel("hotline_phone"), FieldPanel("hotline_phone_secondary")],
            heading=_("Hotline"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("telegram_url"),
                FieldPanel("instagram_url"),
                FieldPanel("facebook_url"),
                FieldPanel("youtube_url"),
                FieldPanel("tiktok_url"),
            ],
            heading=_("Social networks"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("disclaimer_uz"),
                FieldPanel("disclaimer_ru"),
                FieldPanel("footer_text_uz"),
                FieldPanel("footer_text_ru"),
                FieldPanel("legal_text_uz"),
                FieldPanel("legal_text_ru"),
            ],
            heading=_("Footer & legal"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("emergency_banner_enabled"),
                FieldPanel("emergency_banner_uz"),
                FieldPanel("emergency_banner_ru"),
                FieldPanel("emergency_banner_link"),
            ],
            heading=_("Emergency banner (e.g. screening month)"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("partner_agency_logo"),
                FieldPanel("partner_yandex_logo"),
                FieldPanel("partner_hamroh_logo"),
            ],
            heading=_("Partner logos"),
        ),
        FieldPanel("metrika_id"),
        FieldPanel("privacy_page"),
    ]

    class Meta:
        verbose_name = _("site settings")

    def localized(self, field: str, language: str) -> str:
        """Return `<field>_<lang>` falling back to uz."""
        value = getattr(self, f"{field}_{language}", "")
        return str(value or getattr(self, f"{field}_uz", ""))
