from __future__ import annotations

import io
from typing import Any

import pytest
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image as PILImage
from wagtail.models import Locale


@pytest.fixture
def wagtail_image(db) -> Any:
    from apps.media_library.models import PortalImage

    buffer = io.BytesIO()
    PILImage.new("RGB", (64, 40), color=(200, 30, 90)).save(buffer, format="PNG")
    return PortalImage.objects.create(
        title="Test image",
        file=SimpleUploadedFile("test.png", buffer.getvalue(), content_type="image/png"),
        width=64,
        height=40,
    )


@pytest.fixture
def wagtail_document(db) -> Any:
    from apps.media_library.models import PortalDocument

    return PortalDocument.objects.create(
        title="Guide", file=ContentFile(b"%PDF-1.4 test", name="guide.pdf")
    )


@pytest.fixture
def glossary_term(db) -> Any:
    from apps.glossary.models import Term

    return Term.objects.create(
        locale=Locale.objects.get(language_code="uz"),
        term="Biopsiya",
        definition="<p>[[TODO: content — copywriter]]</p>",
        synonyms="биопсия",
    )


@pytest.fixture
def institution(db) -> Any:
    from apps.directory.models import Institution, InstitutionKind, Region, Service

    region = Region.objects.get(code="tashkent-city")
    inst = Institution.objects.create(
        name_uz="Yunusobod tuman poliklinikasi (test)",
        name_ru="Поликлиника Юнусабадского района (тест)",
        kind=InstitutionKind.POLYCLINIC,
        region=region,
        phone="+998712001122",
        free_under_state_programme=True,
        sections="women",
    )
    inst.services.add(Service.objects.get(code="mammography"))
    return inst
