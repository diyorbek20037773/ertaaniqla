"""Custom Wagtail image and document models (must exist before the first migration).

Video snippets, galleries and transcoding arrive in M3; the image/document models are created
now so `WAGTAILIMAGES_IMAGE_MODEL` / `WAGTAILDOCS_DOCUMENT_MODEL` never have to change.
"""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.documents.models import AbstractDocument, Document
from wagtail.images.models import AbstractImage, AbstractRendition, Image


class PortalImage(AbstractImage):
    # alt text is required for accessibility (spec §9); Wagtail 7 keeps `description` for that
    credit = models.CharField(_("credit / source"), max_length=255, blank=True)
    is_decorative = models.BooleanField(
        _("decorative (no alt text needed)"),
        default=False,
        help_text=_("Only for purely decorative images. Content images must describe themselves."),
    )

    admin_form_fields = (*Image.admin_form_fields, "credit", "is_decorative")

    class Meta(AbstractImage.Meta):
        verbose_name = _("image")
        verbose_name_plural = _("images")

    @property
    def alt_text(self) -> str:
        if self.is_decorative:
            return ""
        return str(self.description or self.title)


class PortalRendition(AbstractRendition):
    image = models.ForeignKey(PortalImage, on_delete=models.CASCADE, related_name="renditions")

    class Meta(AbstractRendition.Meta):
        unique_together = (("image", "filter_spec", "focal_point_key"),)


class PortalDocument(AbstractDocument):
    is_private = models.BooleanField(
        _("private (consent forms etc.)"),
        default=False,
        help_text=_("Private documents are served only to logged-in CMS users."),
    )
    description = models.TextField(_("description"), blank=True)

    admin_form_fields = (*Document.admin_form_fields, "description", "is_private")

    class Meta(AbstractDocument.Meta):
        verbose_name = _("document")
        verbose_name_plural = _("documents")
