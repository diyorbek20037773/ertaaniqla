"""Client requests of 2026-10-16 (D-090): the topic's videos under «Foydali maʼlumotlar», the
strip above the footer, the Word news template → published uz + ru news."""

from __future__ import annotations

import importlib.util
import io
import json
import zipfile
from pathlib import Path

import pytest
from django.core.management import call_command
from django.test import Client
from wagtail.models import Site

from apps.core.models import SiteSettings
from apps.media_library.models import Video, VideoSource, VideoStatus
from apps.posts.client_news import news_batches
from apps.posts.models import PostPage

ROOT = Path(__file__).resolve().parents[2]


def _video(title: str, topic: str) -> Video:
    return Video.objects.create(
        title=title,
        topic=topic,
        source=VideoSource.YOUTUBE,
        external_url=f"https://www.youtube.com/watch?v={title[:11]:_<11}",
        status=VideoStatus.READY,
    )


@pytest.mark.django_db
def test_news_list_shows_the_topics_videos(seeded, client: Client) -> None:
    _video("Mammografiya haqida", "breast")
    _video("HPV va skrining", "cervical")
    html = client.get("/uz/yangiliklar/?topic=breast").content.decode()
    videos = html.split('id="videolar"', 1)[1]
    assert "Mammografiya haqida" in videos and "HPV va skrining" not in videos
    assert 'href="/uz/videoroliklar/?topic=breast"' in videos  # «Barcha videolar»
    assert "/uz/videoroliklar/" in videos.split('class="video-card__link"', 1)[1][:80]
    assert 'id="videolar"' not in client.get("/uz/maqolalar/").content.decode()  # news only


@pytest.mark.django_db
def test_strip_above_the_footer_in_every_language(seeded, client: Client) -> None:
    uz = client.get("/uz/").content.decode()
    strip = uz.split('class="site-notice"', 1)[1].split("</div>", 2)[0]
    assert "mulohazalaringiz boʻlsa" in strip
    assert '<a href="mailto:n.akhatov@asr.gov.uz">n.akhatov@asr.gov.uz</a>' in strip
    assert uz.index('class="site-notice"') < uz.index('class="site-footer"')
    oz = client.get("/oz/", follow=True).content.decode()
    assert "мулоҳазаларингиз бўлса" in oz and "mailto:n.akhatov@asr.gov.uz" in oz
    assert "Если имеются предложения" in client.get("/ru/").content.decode()
    settings_obj = SiteSettings.for_site(Site.objects.get(is_default_site=True))
    settings_obj.notice_uz = ""
    settings_obj.save()
    assert 'class="site-notice"' not in client.get("/uz/haqimizda/").content.decode()


def test_news_batches_are_complete() -> None:
    items = [item for batch in news_batches() for item in batch]
    assert len(items) == 10
    assert {item["topic"] for item in items} == {"breast", "cervical"}
    for item in items:
        for lang in ("uz", "ru"):
            text = item[lang]
            assert text["title"] and text["summary"] and "<h2>" in text["body"], item["slug"]
            assert len(text["summary"]) <= 500
        assert "ʻ" in item["uz"]["body"] or "ʼ" in item["uz"]["body"]  # normalised apostrophes
        assert "'" not in item["uz"]["title"]
        cover = item["cover"]
        assert not cover or (ROOT / "apps/posts/seed_media" / cover).exists(), cover


@pytest.mark.django_db
def test_publish_client_news_once_with_russian_versions(
    seeded, client: Client, django_user_model
) -> None:
    call_command("client_update_20261015")  # the item of 2026-10-15
    call_command("apply_ru_translations")  # its machine-made Russian version
    call_command("publish_client_news")
    uz = PostPage.objects.filter(locale__language_code="uz")
    assert uz.count() == 10 and uz.filter(topic="cervical").count() == 5
    ru = PostPage.objects.filter(locale__language_code="ru")
    assert ru.count() == 10
    genetic = ru.get(slug="geneticheskie-issledovaniya-pri-rake-molochnoy-zhelezy")
    assert genetic.summary.startswith("Сегодня врачи всё чаще говорят")  # the client's Russian
    stages = uz.get(slug="bachadon-boyni-saratoni-bosqichlari")
    assert stages.get_translation(ru.first().locale).title == "Стадии рака шейки матки"
    html = client.get(stages.url).content.decode()
    assert "<h3>IA1 — 3 mm gacha</h3>" in html and "15 oktabr 2026" in html
    # an editor's Russian text is kept, and nothing is created twice
    edited = ru.get(slug=genetic.slug)
    edited.summary = "Текст редактора"
    editor = django_user_model.objects.create_user(username="redaktor", password="x" * 16)
    edited.save_revision(user=editor).publish()
    call_command("publish_client_news")
    assert PostPage.objects.filter(locale__language_code="uz").count() == 10
    edited.refresh_from_db()
    assert edited.summary == "Текст редактора"


def _docx(paragraphs: list[tuple[str, bool, bool]]) -> bytes:
    """A minimal Word file: (text, bold, list item) per paragraph."""
    w = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    body = []
    for text, bold, listed in paragraphs:
        props = "<w:pPr><w:numPr><w:ilvl w:val='0'/></w:numPr></w:pPr>" if listed else ""
        run_props = "<w:rPr><w:b/></w:rPr>" if bold else ""
        body.append(
            f"<w:p>{props}<w:r>{run_props}<w:t xml:space='preserve'>{text}</w:t></w:r></w:p>"
        )
    document = f"<w:document xmlns:w='{w}'><w:body>{''.join(body)}</w:body></w:document>"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as docx:
        docx.writestr("word/document.xml", document)
        docx.writestr("word/_rels/document.xml.rels", "<Relationships/>")
    return buffer.getvalue()


def test_word_template_reader(tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location("news_docx", ROOT / "scripts/news_docx.py")
    assert spec and spec.loader
    news_docx = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(news_docx)
    path = tmp_path / "news.docx"
    path.write_bytes(
        _docx(
            [
                ("Сарлавҳа", True, False),
                ("Ko'krak bezi belgilari", False, False),
                ("Симптомы рака груди", False, False),
                ("Қисқа мазмун", True, False),
                ("Qisqa matn bo'ladi.", False, False),
                ("Краткий текст.", False, False),
                ("Асосий матн", True, False),
                ("Краткий текст.", False, False),  # Russian first, as in the cervical file
                ("Изменения кожи", True, False),
                ("покраснение;", False, True),
                ("Qisqa matn bo'ladi.", False, False),
                ("Teri o'zgarishlari", True, False),
                ("qizarish;", False, True),
                ("Muhim:", True, False),
                ("IA1 — 3 mm gacha", False, False),
                ("Мавзу", True, False),
                ("Кўкрак бези саратони", False, False),
                ("Сана", True, False),
                ("16/10/2026", False, False),
            ]
        )
    )
    [item] = news_docx.convert(path, "breast")
    assert item["slug"] == "kokrak-bezi-belgilari" and item["date"] == "2026-10-16"
    assert item["uz"]["title"] == "Koʻkrak bezi belgilari"
    assert item["uz"]["body"] == (
        "<h2>Teri oʻzgarishlari</h2><ul><li>qizarish;</li></ul>"
        "<p><b>Muhim:</b></p><h3>IA1 — 3 mm gacha</h3>"
    )
    assert item["ru"]["body"] == "<h2>Изменения кожи</h2><ul><li>покраснение;</li></ul>"
    assert item["cover"] == ""
    json.dumps(item, ensure_ascii=False)  # the batch file format
