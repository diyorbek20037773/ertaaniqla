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


def test_word_reader_keeps_tracked_insertions(tmp_path: Path) -> None:
    """A file sent with «Track changes» on: inserted words (`w:ins`) are the text, deleted ones
    (`w:del`) are not, and both are counted so the script can warn."""
    spec = importlib.util.spec_from_file_location("news_docx", ROOT / "scripts/news_docx.py")
    assert spec and spec.loader
    news_docx = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(news_docx)
    w = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    paragraph = (
        "<w:p><w:r><w:t xml:space='preserve'>Ko'krak </w:t></w:r>"
        "<w:ins w:id='1'><w:r><w:t xml:space='preserve'>bezi </w:t></w:r></w:ins>"
        "<w:del w:id='2'><w:r><w:delText>eski </w:delText></w:r></w:del>"
        "<w:smartTag><w:r><w:t>belgilari</w:t></w:r></w:smartTag></w:p>"
    )
    document = f"<w:document xmlns:w='{w}'><w:body>{paragraph}</w:body></w:document>"
    path = tmp_path / "news.docx"
    with zipfile.ZipFile(path, "w") as docx:
        docx.writestr("word/document.xml", document)
        docx.writestr("word/_rels/document.xml.rels", "<Relationships/>")
    [para] = news_docx.read_paragraphs(path)
    assert para.text == "Ko'krak bezi belgilari"
    assert para.revisions == 2


def _reader() -> object:
    spec = importlib.util.spec_from_file_location("news_docx", ROOT / "scripts/news_docx.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _raw_docx(path: Path, paragraphs: str, rels: str = "") -> None:
    w = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    r = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    document = f"<w:document xmlns:w='{w}' xmlns:r='{r}'><w:body>{paragraphs}</w:body></w:document>"
    with zipfile.ZipFile(path, "w") as docx:
        docx.writestr("word/document.xml", document)
        docx.writestr("word/_rels/document.xml.rels", f"<Relationships>{rels}</Relationships>")


def test_word_reader_drops_a_deleted_link(tmp_path: Path) -> None:
    """The client replaced the cover link with «Track changes» on: the deleted link is not read
    (its cover would be downloaded instead of the new one)."""
    news_docx = _reader()
    rels = (  # double quotes, as Word writes them
        '<Relationship Id="rOld" Target="https://drive.google.com/file/d/OLD/view"/>'
        '<Relationship Id="rNew" Target="https://drive.google.com/file/d/NEW/view"/>'
    )
    paragraph = (
        "<w:p><w:hyperlink r:id='rOld'><w:del w:id='1'><w:r><w:delText>old</w:delText></w:r>"
        "</w:del></w:hyperlink><w:ins w:id='2'><w:hyperlink r:id='rNew'><w:r><w:t>new</w:t>"
        "</w:r></w:hyperlink></w:ins></w:p>"
    )
    path = tmp_path / "news.docx"
    _raw_docx(path, paragraph, rels)
    [para] = news_docx.read_paragraphs(path)  # type: ignore[attr-defined]
    assert para.links == ["https://drive.google.com/file/d/NEW/view"]
    assert para.text == "new" and para.revisions == 2


def test_word_reader_joins_paragraphs_whose_mark_was_deleted(tmp_path: Path) -> None:
    """Two paragraphs joined with «Track changes» on (Word marks only the first paragraph's
    mark as deleted): one paragraph, as after «Accept all changes», not a false subheading."""
    news_docx = _reader()
    paragraphs = (
        "<w:p><w:pPr><w:rPr><w:del w:id='1'/></w:rPr></w:pPr>"
        "<w:r><w:t xml:space='preserve'>Mammografiya har ikki yilda </w:t></w:r></w:p>"
        "<w:p><w:r><w:t>bir marta tavsiya etiladi.</w:t></w:r></w:p>"
        "<w:p><w:pPr><w:rPr><w:ins w:id='2'/></w:rPr></w:pPr><w:r><w:t>Yangi.</w:t></w:r></w:p>"
    )
    path = tmp_path / "news.docx"
    _raw_docx(path, paragraphs)
    joined, split = news_docx.read_paragraphs(path)  # type: ignore[attr-defined]
    assert joined.text == "Mammografiya har ikki yilda bir marta tavsiya etiladi."
    assert joined.revisions == 1 and split.revisions == 1  # both counted for the warning


@pytest.mark.django_db
def test_a_corrected_russian_body_reaches_an_unedited_page(seeded) -> None:
    """The Word reader used to glue the lines of a Shift+Enter break («…росту.HER2-статус…»): a
    second run puts the corrected body on a Russian page nobody edited."""
    call_command("publish_client_news")
    page = PostPage.objects.get(locale__language_code="ru", body__icontains="HER2-статус")
    old = page.body.get_prep_value()[0]["value"].replace(
        "росту.</p><p>HER2-статус", "росту.HER2-статус"
    )
    page.body = [{"type": "rich_text", "value": old}]
    page.save_revision().publish()  # no user: the import's own revision
    call_command("publish_client_news")
    page.refresh_from_db()
    assert "росту.</p><p>HER2-статус оценивается" in page.body.get_prep_value()[0]["value"]


def test_word_reader_ends_a_line_at_a_soft_break(tmp_path: Path) -> None:
    news_docx = _reader()
    paragraph = (
        "<w:p><w:r><w:t>к опухолевому росту.</w:t><w:br/><w:t>HER2-статус оценивается"
        "</w:t><w:tab/><w:t>двумя методами:</w:t><w:br/></w:r></w:p>"
    )
    path = tmp_path / "news.docx"
    _raw_docx(path, paragraph)
    [para] = news_docx.read_paragraphs(path)  # type: ignore[attr-defined]
    lines = para.split_lines()
    assert [line.text for line in lines] == [
        "к опухолевому росту.",
        "HER2-статус оценивается двумя методами:",
    ]
    listed = paragraph.replace(
        "<w:p>", "<w:p><w:pPr><w:numPr><w:ilvl w:val='0'/></w:numPr></w:pPr>"
    )
    _raw_docx(path, listed)
    [item] = news_docx.read_paragraphs(path)[0].split_lines()  # type: ignore[attr-defined]
    assert item.is_list and "<br" not in item.inline_html(False)  # one bullet, lines joined
    assert item.text == "к опухолевому росту. HER2-статус оценивается двумя методами:"


def test_a_soft_break_in_the_title_is_a_space(tmp_path: Path) -> None:
    """Only the body splits at a soft line break; a title typed on two lines stays whole."""
    news_docx = _reader()

    def p(text: str, bold: bool = False) -> str:
        props = "<w:rPr><w:b/></w:rPr>" if bold else ""
        return f"<w:p><w:r>{props}<w:t xml:space='preserve'>{text}</w:t></w:r></w:p>"

    paragraphs = (
        p("Сарлавҳа", True)
        + "<w:p><w:r><w:t>Ko'krak bezi</w:t><w:br/><w:t>belgilari</w:t></w:r></w:p>"
        + p("Қисқа мазмун", True)
        + p("Qisqa matn.")
        + p("Асосий матн", True)
        + "<w:p><w:r><w:t>Birinchi gap.</w:t><w:br/><w:t>Ikkinchi gap.</w:t></w:r></w:p>"
        + p("Мавзу", True)
        + p("Кўкрак бези саратони")
        + p("Сана", True)
        + p("16/10/2026")
    )
    path = tmp_path / "news.docx"
    _raw_docx(path, paragraphs)
    [item] = news_docx.convert(path, "breast")  # type: ignore[attr-defined]
    assert item["uz"]["title"] == "Koʻkrak bezi belgilari"
    assert item["uz"]["body"] == "<p>Birinchi gap.</p><p>Ikkinchi gap.</p>"
