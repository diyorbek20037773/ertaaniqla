"""Where-to-go directory (spec §4.3 `Institution`, `Region`): 14 regions, institution kinds,
services, free-under-state-programme flag, `DirectoryPage`. CSV import, map and HTMX filters: M4.
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.fields import StreamField
from wagtail.models import Page
from wagtail.search import index
from wagtail.snippets.models import register_snippet

from apps.articles.blocks import IntroBlock, stream_plain_text
from apps.core.models import BasePage, TimeStampedModel


class Region(models.Model):
    """One of the 14 regions: 12 viloyat + Tashkent city + Karakalpakstan."""

    code = models.SlugField(_("code"), max_length=16, unique=True)
    name_uz = models.CharField(_("name (uz)"), max_length=100)
    name_ru = models.CharField(_("name (ru)"), max_length=100)
    sort_order = models.PositiveSmallIntegerField(_("sort order"), default=0)

    class Meta:
        verbose_name = _("region")
        verbose_name_plural = _("regions")
        ordering = ["sort_order", "name_uz"]

    def __str__(self) -> str:
        return self.name_uz

    def name_for(self, language: str) -> str:
        return self.name_ru if language == "ru" else self.name_uz


class Service(models.Model):
    """Medical service offered by an institution (mammography, ultrasound, HPV test…)."""

    code = models.SlugField(_("code"), max_length=32, unique=True)
    name_uz = models.CharField(_("name (uz)"), max_length=120)
    name_ru = models.CharField(_("name (ru)"), max_length=120)

    class Meta:
        verbose_name = _("service")
        verbose_name_plural = _("services")
        ordering = ["name_uz"]

    def __str__(self) -> str:
        return self.name_uz

    def name_for(self, language: str) -> str:
        return self.name_ru if language == "ru" else self.name_uz


class InstitutionKind(models.TextChoices):
    SVP = "svp", _("Family doctor point (SVP)")
    POLYCLINIC = "polyclinic", _("District polyclinic")
    ONCO_ROOM = "onco_room", _("Onco-alertness room")
    MOTHER_CHILD_CENTRE = "mother_child_centre", _("Mother & Child Health Centre / branch")
    ONCOLOGY_CENTRE = "oncology_centre", _("Oncology centre (RONC / regional)")
    PAEDIATRIC_ONCOHAEMATOLOGY = "paediatric_oncohaematology", _("Paediatric onco-haematology")
    PSYCH_SUPPORT = "psych_support", _("Psychological support")
    NGO = "ngo", _("NGO / support group")


class InstitutionSections(models.TextChoices):
    WOMEN = "women", _("Women's cancer")
    CHILDREN = "children", _("Childhood cancer")
    BOTH = "both", _("Both")


@register_snippet
class Institution(index.Indexed, TimeStampedModel):
    name_uz = models.CharField(_("name (uz)"), max_length=200)
    name_ru = models.CharField(_("name (ru)"), max_length=200)
    kind = models.CharField(
        _("kind"), max_length=32, choices=InstitutionKind.choices, db_index=True
    )
    region = models.ForeignKey(
        Region, verbose_name=_("region"), on_delete=models.PROTECT, related_name="institutions"
    )
    district_uz = models.CharField(_("district (uz)"), max_length=120, blank=True)
    district_ru = models.CharField(_("district (ru)"), max_length=120, blank=True)
    address_uz = models.CharField(_("address (uz)"), max_length=300, blank=True)
    address_ru = models.CharField(_("address (ru)"), max_length=300, blank=True)
    phone = models.CharField(_("phone"), max_length=64, blank=True)
    hours_uz = models.CharField(_("opening hours (uz)"), max_length=200, blank=True)
    hours_ru = models.CharField(_("opening hours (ru)"), max_length=200, blank=True)
    website = models.URLField(_("website"), blank=True)
    lat = models.DecimalField(
        _("latitude"),
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("-90")), MaxValueValidator(Decimal("90"))],
    )
    lng = models.DecimalField(
        _("longitude"),
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("-180")), MaxValueValidator(Decimal("180"))],
    )
    free_under_state_programme = models.BooleanField(
        _("free under the state programme"), default=False, db_index=True
    )
    services = models.ManyToManyField(
        Service, verbose_name=_("services"), blank=True, related_name="institutions"
    )
    sections = models.CharField(
        _("sections"),
        max_length=16,
        choices=InstitutionSections.choices,
        default=InstitutionSections.BOTH,
        db_index=True,
    )
    verified_at = models.DateField(_("data verified on"), null=True, blank=True)
    is_published = models.BooleanField(_("published"), default=True, db_index=True)
    external_id = models.CharField(
        _("external id"),
        max_length=64,
        blank=True,
        help_text=_("Identifier in an external registry (e.g. DMED) for future synchronisation."),
    )
    external_source = models.CharField(_("external source"), max_length=32, blank=True)

    panels = [
        MultiFieldPanel([FieldPanel("name_uz"), FieldPanel("name_ru")], heading=_("Name")),
        MultiFieldPanel(
            [FieldPanel("kind"), FieldPanel("sections"), FieldPanel("free_under_state_programme")],
            heading=_("Type"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("region"),
                FieldPanel("district_uz"),
                FieldPanel("district_ru"),
                FieldPanel("address_uz"),
                FieldPanel("address_ru"),
                FieldPanel("lat"),
                FieldPanel("lng"),
            ],
            heading=_("Location"),
        ),
        MultiFieldPanel(
            [
                FieldPanel("phone"),
                FieldPanel("hours_uz"),
                FieldPanel("hours_ru"),
                FieldPanel("website"),
            ],
            heading=_("Contact"),
        ),
        FieldPanel("services"),
        MultiFieldPanel(
            [
                FieldPanel("is_published"),
                FieldPanel("verified_at"),
                FieldPanel("external_id"),
                FieldPanel("external_source"),
            ],
            heading=_("Status"),
        ),
    ]

    search_fields = [
        index.SearchField("name_uz", boost=2),
        index.SearchField("name_ru", boost=2),
        index.SearchField("address_uz"),
        index.SearchField("address_ru"),
        index.FilterField("kind"),
        index.FilterField("region_id"),
        index.FilterField("is_published"),
    ]

    class Meta:
        verbose_name = _("institution")
        verbose_name_plural = _("institutions")
        ordering = ["region__sort_order", "name_uz"]
        indexes = [models.Index(fields=["region", "kind", "is_published"])]

    def __str__(self) -> str:
        return self.name_uz

    def name_for(self, language: str) -> str:
        return self.name_ru if language == "ru" else self.name_uz

    def address_for(self, language: str) -> str:
        return self.address_ru if language == "ru" else self.address_uz

    def district_for(self, language: str) -> str:
        return self.district_ru if language == "ru" else self.district_uz

    def hours_for(self, language: str) -> str:
        return self.hours_ru if language == "ru" else self.hours_uz

    @property
    def has_coordinates(self) -> bool:
        return self.lat is not None and self.lng is not None


class DirectoryPage(BasePage):
    """«Куда обратиться» — list of institutions with region/type filters (map + HTMX in M4).

    Lives under the women's section (TZ menu item 4) and is reachable from the children's
    pages; a Wagtail redirect provides the short URL `/uz/qayerga-murojaat/` (spec §4.4).
    """

    intro = StreamField(IntroBlock(), blank=True, verbose_name=_("intro"))
    default_section = models.CharField(
        _("default section filter"),
        max_length=16,
        choices=InstitutionSections.choices,
        default=InstitutionSections.BOTH,
        help_text=_("Pre-selects the section filter; visitors can change it."),
    )

    content_panels = [*Page.content_panels, FieldPanel("intro"), FieldPanel("default_section")]

    parent_page_types = ["sections.SectionIndexPage", "home.HomePage"]
    subpage_types: list[str] = []
    template = "directory/directory_page.html"

    class Meta:
        verbose_name = _("directory page (where to go)")

    def get_body_text(self) -> str:
        return stream_plain_text(self.intro)

    def serve(self, request: Any, *args: Any, **kwargs: Any) -> Any:
        """HTMX filter requests get the results partial (list + map data)."""
        from django.template.response import TemplateResponse

        if request.headers.get("HX-Request"):
            response = TemplateResponse(
                request, "directory/_results.html", self.get_context(request, *args, **kwargs)
            )
            response["Vary"] = "HX-Request, Accept-Language, Cookie"
            return response
        return super().serve(request, *args, **kwargs)

    def get_context(self, request: Any, *args: Any, **kwargs: Any) -> dict[str, Any]:
        from django.utils.translation import get_language

        from apps.directory.services import filter_institutions, map_payload, region_list

        context = super().get_context(request, *args, **kwargs)
        region = request.GET.get("region", "")
        kind = request.GET.get("kind", "")
        section = request.GET.get("section", "") or (
            "" if self.default_section == InstitutionSections.BOTH else self.default_section
        )
        free_only = request.GET.get("free") == "1"
        institutions = list(
            filter_institutions(region=region, kind=kind, section=section, free_only=free_only)
        )
        # JSON-LD MedicalClinic entries mirror the visible (filtered) list — spec §10
        from apps.core import seo

        language = get_language() or "uz"
        context["jsonld"] = [
            *context.get("jsonld", []),
            *(seo.clinic_ld(i, language) for i in institutions[:50]),
        ]
        context.update(
            {
                "institutions": institutions,
                "map_data": json.dumps(
                    map_payload(institutions, get_language() or "uz"), ensure_ascii=False
                ).replace("</", r"<\/"),
                "regions": region_list(),
                "kinds": InstitutionKind.choices,
                "filter": {
                    "region": region,
                    "kind": kind,
                    "section": section,
                    "free": free_only,
                },
            }
        )
        return context
