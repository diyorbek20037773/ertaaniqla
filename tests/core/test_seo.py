"""SEO (spec §10): JSON-LD graph per page type, per-language sitemaps, share bar, story image,
site verification tags."""

from __future__ import annotations

import json
import re

import pytest
from django.test import Client, override_settings

from apps.articles.models import ArticlePage
from apps.core.tasks import generate_og_image

pytestmark = pytest.mark.django_db


def jsonld_of(html: str) -> dict:
    match = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    assert match, "no JSON-LD"
    data = json.loads(match.group(1))
    assert data["@context"] == "https://schema.org"
    return data


def types(graph: dict) -> list:
    out = []
    for item in graph["@graph"]:
        t = item["@type"]
        out.extend(t if isinstance(t, list) else [t])
    return out


def test_article_jsonld_with_reviewer(seeded, user, client: Client) -> None:
    article = ArticlePage.objects.get(
        url_path__endswith="/ayollar/ogohlik/kokrak-bezi-saratoni/", locale__language_code="uz"
    )
    user.first_name, user.last_name, user.organisation = "Dilfuza", "A.", "RONC"
    user.save()
    article.medically_verified = True
    article.last_reviewed_by = user
    article.last_reviewed_at = article.first_published_at.date()
    article.save_revision().publish()
    graph = jsonld_of(client.get(article.url).content.decode())
    kinds = types(graph)
    assert {"Organization", "BreadcrumbList", "MedicalWebPage", "Article"} <= set(kinds)
    page_item = next(i for i in graph["@graph"] if "MedicalWebPage" in i["@type"])
    assert page_item["reviewedBy"]["name"] == "Dilfuza A."
    assert page_item["reviewedBy"]["affiliation"]["name"] == "RONC"
    assert page_item["lastReviewed"] == article.last_reviewed_at.isoformat()
    assert page_item["inLanguage"] == "uz"
    assert page_item["about"]["name"] == "Ayollar saratoni"
    crumbs = next(i for i in graph["@graph"] if i["@type"] == "BreadcrumbList")
    assert crumbs["itemListElement"][-1]["name"] == "Koʻkrak bezi saratoni"


def test_home_and_faq_and_directory_jsonld(seeded, client: Client) -> None:
    home = jsonld_of(client.get("/ru/").content.decode())
    assert "BreadcrumbList" not in types(home)
    org = next(i for i in home["@graph"] if i["@type"] == "Organization")
    assert org["url"] == "http://localhost/ru/"

    from apps.faq.models import Question

    Question.objects.create(
        section="women",
        text="Savol?",
        consent_to_publish=True,
        status="published",
        answer="<p>Javob</p>",
        public_question="Anonim savol?",
    )
    faq = jsonld_of(client.get("/uz/savol-javob/").content.decode())
    faq_item = next(i for i in faq["@graph"] if i["@type"] == "FAQPage")
    assert faq_item["mainEntity"][0]["name"] == "Anonim savol?"
    assert faq_item["mainEntity"][0]["acceptedAnswer"]["text"] == "Javob"

    from django.core.management import call_command

    call_command("import_institutions", "data/institutions.sample.csv")
    directory = jsonld_of(client.get("/uz/ayollar/qayerga-murojaat/").content.decode())
    clinics = [i for i in directory["@graph"] if i["@type"] == "MedicalClinic"]
    assert len(clinics) == 12
    assert clinics[0]["geo"]["@type"] == "GeoCoordinates"
    assert clinics[0]["address"]["addressCountry"] == "UZ"


def test_video_object_for_video_blocks(seeded, client: Client) -> None:
    from apps.media_library.models import Video

    video = Video.objects.create(
        title="Shifokor", source="youtube", external_url="https://youtu.be/dQw4w9WgXcQ", duration=90
    )
    article = ArticlePage.objects.get(
        url_path__endswith="/ayollar/ogohlik/kokrak-bezi-saratoni/", locale__language_code="uz"
    )
    article.body = json.dumps(
        [
            {
                "type": "video",
                "value": {"video": video.pk, "external_url": "", "caption": "", "transcript": ""},
            }
        ]
    )
    article.save_revision().publish()
    graph = jsonld_of(client.get(article.url).content.decode())
    video_item = next(i for i in graph["@graph"] if i["@type"] == "VideoObject")
    assert video_item["embedUrl"] == video.external_url
    assert video_item["duration"] == "PT90S"


def test_jsonld_on_non_page_view(seeded, client: Client) -> None:
    graph = jsonld_of(client.get("/uz/qidiruv/?q=x").content.decode())
    assert types(graph) == ["Organization"]


def test_sitemaps_are_per_language_and_skip_noindex(seeded, client: Client) -> None:
    uz = client.get("/uz/sitemap.xml").content.decode()
    ru = client.get("/ru/sitemap.xml").content.decode()
    assert "/uz/ayollar/" in uz and "/ru/zhenskiy/" not in uz
    assert "/ru/zhenskiy/" in ru and "/uz/ayollar/" not in ru
    article = ArticlePage.objects.get(
        url_path__endswith="/ayollar/ogohlik/kokrak-bezi-saratoni/", locale__language_code="uz"
    )
    assert article.url in uz
    article.noindex = True
    article.save_revision().publish()
    assert article.url not in client.get("/uz/sitemap.xml").content.decode()


@override_settings(WAFFLE_FLAG_DEFAULT=False)
def test_sitemap_skips_disabled_tools(seeded, client: Client) -> None:
    from waffle.models import Flag

    Flag.objects.update_or_create(name="tools_screening", defaults={"everyone": False})
    assert "/uz/vositalar/skrining/" not in client.get("/uz/sitemap.xml").content.decode()


def test_share_bar_and_story_image(seeded, client: Client) -> None:
    article = ArticlePage.objects.get(
        url_path__endswith="/ayollar/ogohlik/kokrak-bezi-saratoni/", locale__language_code="uz"
    )
    generate_og_image(article.pk)
    article.refresh_from_db()
    assert article.story_image_generated_url.startswith("/media/story/")
    html = client.get(article.url).content.decode()
    assert "https://t.me/share/url?url=http%3A%2F%2Flocalhost%2Fuz%2Fayollar" in html
    assert "share__link--telegram" in html and "wa.me" in html and "facebook.com/sharer" in html
    assert 'class="share__link share__link--story"' in html
    assert article.story_image_generated_url in html


def test_story_image_dimensions() -> None:
    import io

    from PIL import Image

    from apps.core.og import render_story_image

    png = render_story_image("Sarlavha", "Qisqacha", "children", "uz")
    assert Image.open(io.BytesIO(png)).size == (1080, 1920)


@override_settings(YANDEX_WEBMASTER_VERIFICATION="ya-token", GOOGLE_SITE_VERIFICATION="g-token")
def test_site_verification_meta(seeded, client: Client) -> None:
    html = client.get("/uz/").content.decode()
    assert '<meta name="yandex-verification" content="ya-token">' in html
    assert '<meta name="google-site-verification" content="g-token">' in html


def test_picture_tag_serves_webp(seeded, client: Client, tmp_path) -> None:
    import io

    from django.core.files.uploadedfile import SimpleUploadedFile
    from PIL import Image

    from apps.media_library.models import PortalImage

    buffer = io.BytesIO()
    Image.new("RGB", (900, 600), (200, 30, 90)).save(buffer, format="JPEG")
    image = PortalImage(title="Hero")
    image.file = SimpleUploadedFile("hero.jpg", buffer.getvalue(), content_type="image/jpeg")
    image.width, image.height = 900, 600
    image.save()
    # a plain article: the Figma-designed women's pages show the section banner instead
    article = ArticlePage.objects.get(
        url_path__endswith="/bolalar/onkologiya-haqida/keng-tarqalgan-turlari/",
        locale__language_code="uz",
    )
    article.hero_image = image
    article.save_revision().publish()
    html = client.get(article.url).content.decode()
    assert "<picture>" in html and 'type="image/webp"' in html
    assert "400w" in html and "800w" in html
