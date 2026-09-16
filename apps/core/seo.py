"""Structured data (spec §10): JSON-LD builders for every page type.

Types: Organization (site), BreadcrumbList, MedicalWebPage / Article (with reviewedBy +
lastReviewed when a doctor verified the page), FAQPage (published Q&A), VideoObject,
MedicalClinic (directory). Pure functions returning dicts; `jsonld_script` renders them.
"""

from __future__ import annotations

import contextlib
import json
from typing import Any

from django.conf import settings
from django.utils.html import format_html, strip_tags
from django.utils.safestring import SafeString

SITE_NAME = {"uz": "Erta aniqla", "ru": "Эрта аниқла"}
ORGANIZATION_NAME = {
    "uz": "«Erta aniqla» onkologik ogohlik portali",
    "ru": "Портал онконастороженности «Эрта аниқла»",
}


def _text(value: Any, limit: int = 500) -> str:
    return " ".join(strip_tags(str(value or "")).split())[:limit]


def absolute(base: str, url: str) -> str:
    if not url:
        return base
    if url.startswith("http"):
        return url
    return f"{base}{url}"


def organization_ld(base: str, language: str, settings_obj: Any = None) -> dict[str, Any]:
    data: dict[str, Any] = {
        "@type": "Organization",
        "@id": f"{base}/#organization",
        "name": ORGANIZATION_NAME.get(language, ORGANIZATION_NAME["uz"]),
        "url": f"{base}/{language}/",
        "areaServed": "UZ",
    }
    same_as = []
    if settings_obj is not None:
        for field in ("telegram_url", "instagram_url", "facebook_url", "youtube_url", "tiktok_url"):
            value = getattr(settings_obj, field, "")
            if value:
                same_as.append(value)
        hotline = getattr(settings_obj, "hotline_phone", "")
        if hotline:
            data["contactPoint"] = {
                "@type": "ContactPoint",
                "telephone": hotline,
                "contactType": "customer support",
                "availableLanguage": ["uz", "ru"],
            }
    if same_as:
        data["sameAs"] = same_as
    return data


def breadcrumb_ld(crumbs: list[Any], base: str) -> dict[str, Any] | None:
    if len(crumbs) < 2:
        return None
    return {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": index,
                "name": str(crumb.title),
                "item": absolute(base, str(crumb.url or "")),
            }
            for index, crumb in enumerate(crumbs, start=1)
        ],
    }


def page_ld(page: Any, base: str, language: str, article: bool = False) -> dict[str, Any]:
    """MedicalWebPage (index/tool pages) or Article-flavoured MedicalWebPage (articles)."""
    data: dict[str, Any] = {
        "@type": ["MedicalWebPage", "Article"] if article else "MedicalWebPage",
        "@id": absolute(base, str(page.url or "")),
        "url": absolute(base, str(page.url or "")),
        "name": str(page.title),
        "headline": str(page.seo_title or page.title),
        "inLanguage": language,
        "isPartOf": {"@id": f"{base}/#organization"},
        "publisher": {"@id": f"{base}/#organization"},
        "audience": {"@type": "MedicalAudience", "audienceType": "Patient"},
    }
    description = _text(page.search_description or getattr(page, "summary", "") or "", 300)
    if description:
        data["description"] = description
    if page.first_published_at:
        data["datePublished"] = page.first_published_at.isoformat()
    if page.last_published_at:
        data["dateModified"] = page.last_published_at.isoformat()
    section = page.get_section() if hasattr(page, "get_section") else None
    if section is not None:
        data["about"] = {"@type": "MedicalCondition", "name": str(section.title)}
    badge = getattr(page, "verified_badge", None)
    if badge:
        reviewer: dict[str, Any] = {"@type": "Person", "name": badge["name"] or "Doctor"}
        if badge.get("organisation"):
            reviewer["affiliation"] = {"@type": "Organization", "name": badge["organisation"]}
        data["reviewedBy"] = reviewer
        if badge.get("date"):
            data["lastReviewed"] = badge["date"].isoformat()
    image = getattr(page, "og_image_generated_url", "")
    if image:
        data["image"] = absolute(base, image)
    return data


def faq_ld(questions: list[Any]) -> dict[str, Any] | None:
    if not questions:
        return None
    return {
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": _text(q.display_question, 300),
                "acceptedAnswer": {"@type": "Answer", "text": _text(q.answer, 2000)},
            }
            for q in questions[:50]
        ],
    }


def video_ld(video: Any, base: str, language: str) -> dict[str, Any] | None:
    if video is None:
        return None
    data: dict[str, Any] = {
        "@type": "VideoObject",
        "name": str(video.title),
        "description": _text(video.transcript, 300) or str(video.title),
        "inLanguage": language,
        "uploadDate": video.created_at.isoformat() if getattr(video, "created_at", None) else None,
    }
    if getattr(video, "poster", None):
        with contextlib.suppress(Exception):  # missing file on disk → no thumbnail
            data["thumbnailUrl"] = absolute(base, video.poster.get_rendition("width-960").url)
    if video.is_external:
        data["embedUrl"] = video.external_url
    else:
        content = video.rendition_url("720p") or video.rendition_url("480p")
        if content:
            data["contentUrl"] = absolute(base, content)
    if video.duration:
        data["duration"] = f"PT{int(video.duration)}S"
    return {k: v for k, v in data.items() if v is not None}


def clinic_ld(institution: Any, language: str) -> dict[str, Any]:
    data: dict[str, Any] = {
        "@type": "MedicalClinic",
        "name": institution.name_for(language),
        "address": {
            "@type": "PostalAddress",
            "addressCountry": "UZ",
            "addressRegion": institution.region.name_for(language),
            "addressLocality": institution.district_for(language) or None,
            "streetAddress": institution.address_for(language) or None,
        },
    }
    if institution.phone:
        data["telephone"] = institution.phone
    if institution.website:
        data["url"] = institution.website
    if institution.lat is not None and institution.lng is not None:
        data["geo"] = {
            "@type": "GeoCoordinates",
            "latitude": float(institution.lat),
            "longitude": float(institution.lng),
        }
    if institution.free_under_state_programme:
        data["isAcceptingNewPatients"] = True
    data["address"] = {k: v for k, v in data["address"].items() if v}
    return data


def graph(items: list[dict[str, Any] | None]) -> dict[str, Any]:
    return {"@context": "https://schema.org", "@graph": [i for i in items if i]}


def jsonld_script(data: dict[str, Any]) -> SafeString:
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return format_html('<script type="application/ld+json">{}</script>', SafeString(payload))


def site_verification_tags() -> SafeString:
    tags = []
    if settings.YANDEX_WEBMASTER_VERIFICATION:
        tags.append(
            format_html(
                '<meta name="yandex-verification" content="{}">',
                settings.YANDEX_WEBMASTER_VERIFICATION,
            )
        )
    if settings.GOOGLE_SITE_VERIFICATION:
        tags.append(
            format_html(
                '<meta name="google-site-verification" content="{}">',
                settings.GOOGLE_SITE_VERIFICATION,
            )
        )
    return SafeString("\n".join(tags))
