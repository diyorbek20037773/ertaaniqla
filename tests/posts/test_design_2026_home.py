"""Design 2026-10, «Bosh sahifa»: news / articles / videos lists, the question hub, the landing
blocks and the editable footer site map."""

from __future__ import annotations

from datetime import date

import pytest
from django.test import Client
from wagtail.models import Locale

from apps.core.models import SiteSettings
from apps.faq.models import FAQPage, Question, QuestionStatus
from apps.media_library.models import Video, VideoStatus
from apps.posts.models import PostIndexPage, PostKind, PostPage

pytestmark = pytest.mark.django_db


def _index(kind: str, lang: str = "uz") -> PostIndexPage:
    return PostIndexPage.objects.get(kind=kind, locale__language_code=lang)


def _post(index: PostIndexPage, title: str, topic: str, day: int) -> PostPage:
    post = PostPage(title=title, topic=topic, date=date(2026, 10, day), summary="Qisqa matn")
    index.add_child(instance=post)
    post.save_revision().publish()
    return post


def test_lists_exist_in_both_languages_with_empty_states(seeded, client: Client) -> None:
    for url, empty in (
        ("/uz/yangiliklar/", "Yangiliklar tez orada"),
        ("/ru/novosti/", "Новости скоро"),
        ("/uz/maqolalar/", "Maqolalar tez orada"),
        ("/ru/stati/", "Статьи скоро"),
        ("/uz/videoroliklar/", "Videoroliklar tez orada"),
        ("/ru/video/", "Видео скоро"),
    ):
        response = client.get(url)
        assert response.status_code == 200, url
        html = response.content.decode()
        assert empty in html, url
        assert 'class="topic-filter"' in html


def test_news_newest_first_lead_card_and_topic_filter(seeded, client: Client) -> None:
    index = _index(PostKind.NEWS)
    _post(index, "Eski yangilik", "breast", 1)
    _post(index, "Yangi yangilik", "cervical", 5)
    _post(index, "Bolalar yangiligi", "children", 3)
    html = client.get(index.url).content.decode()
    assert (
        html.index("Yangi yangilik") < html.index("Bolalar yangiligi") < html.index("Eski yangilik")
    )
    assert 'class="news-feature news-feature--side"' in html  # lead item on the «all» list
    filtered = client.get(f"{index.url}?topic=breast").content.decode()
    assert "Eski yangilik" in filtered and "Yangi yangilik" not in filtered
    assert 'class="news-feature' not in filtered
    assert 'aria-current="true">Koʻkrak bezi saratoni</a>' in filtered
    unknown = client.get(f"{index.url}?topic=<script>").content.decode()
    assert "Yangi yangilik" in unknown and "<script>" not in unknown


def test_article_cards_and_post_page(seeded, client: Client) -> None:
    post = _post(_index(PostKind.ARTICLES), "Bosqichlar haqida", "cervical", 2)
    html = client.get(_index(PostKind.ARTICLES).url).content.decode()
    assert 'class="article-card article-card--featured"' in html and "Maqolani oʻqish" in html
    articles = _index(PostKind.ARTICLES).url
    assert "Bosqichlar" in client.get(f"{articles}?q=bosqich").content.decode()
    assert "Bosqichlar haqida" not in client.get(f"{articles}?q=zzz").content.decode()
    page = client.get(post.url)
    assert page.status_code == 200
    assert "Bachadon boʻyni saratoni" in page.content.decode()  # topic chip


def test_videos_list_watch_page_and_topic(seeded, client: Client) -> None:
    ready = Video.objects.create(
        title="KBS diagnostikasi",
        source="youtube",
        external_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        status=VideoStatus.READY,
        topic="breast",
    )
    Video.objects.create(title="Hali tayyor emas", status=VideoStatus.PROCESSING, topic="breast")
    html = client.get("/uz/videoroliklar/").content.decode()
    assert "KBS diagnostikasi" in html and "Hali tayyor emas" not in html
    assert f'href="/uz/videoroliklar/{ready.pk}/"' in html
    assert (
        "KBS diagnostikasi" not in client.get("/uz/videoroliklar/?topic=cervical").content.decode()
    )
    watch = client.get(f"/uz/videoroliklar/{ready.pk}/")
    assert watch.status_code == 200
    assert "youtube-nocookie.com" in watch.content.decode()
    assert client.get("/uz/videoroliklar/999999/").status_code == 404


def test_landing_blocks(seeded, client: Client) -> None:
    _post(_index(PostKind.NEWS), "Bosh sahifadagi yangilik", "breast", 4)
    html = client.get("/uz/").content.decode()
    assert "Eng koʻp beriladigan savollar" in html
    for topic in ("breast", "cervical", "children"):
        assert f'href="/uz/savol-javob/?topic={topic}"' in html
    assert "Bosh sahifadagi yangilik" in html
    assert 'href="/uz/videoroliklar/"' in html and 'href="/uz/maqolalar/"' in html


def test_question_hub_topic_featured_info_cards_and_search(seeded, client: Client) -> None:
    faq = FAQPage.objects.get(locale__language_code="uz")
    common = {
        "status": QuestionStatus.PUBLISHED,
        "consent_to_publish": True,
        "answer": "<p>Javob</p>",
    }
    Question.objects.create(
        text="KBS nima?", section="women", topic="breast", category="general", **common
    )
    Question.objects.create(
        text="KBS belgilari?", section="women", topic="breast", category="signs", **common
    )
    Question.objects.create(text="BBS nima?", section="women", topic="cervical", **common)
    html = client.get(f"{faq.url}?topic=breast").content.decode()
    assert "Koʻkrak bezi saratoni haqida <em>bilib oling</em>" in html
    assert "KBS nima?" in html and "BBS nima?" not in html
    assert 'class="qa-item" id="q-' in html
    # «Mavzular» side list: counts per category, ?category= narrows the list
    assert '<span>Belgilar va sabablar</span><span class="faq-topics__count">1</span>' in html
    signs = client.get(f"{faq.url}?topic=breast&category=signs").content.decode()
    assert "KBS belgilari?" in signs and "KBS nima?" not in signs
    searched = client.get(f"{faq.url}?q=BBS").content.decode()
    assert "BBS nima?" in searched and "KBS nima?" not in searched


def test_one_line_question_form_derives_section_from_topic(seeded, client: Client) -> None:
    faq = FAQPage.objects.get(locale__language_code="uz")
    data = {
        "text": "Bolamda isitma uzoq davom etyapti, nima qilay?",
        "topic": "children",
        "consent_privacy": "on",
        "website": "",
    }
    response = client.post(faq.url, data, HTTP_HX_REQUEST="true")
    assert response.status_code == 200, response.content.decode()[:500]
    question = Question.objects.get()
    assert (question.topic, question.section) == ("children", "children")


def test_footer_site_map_is_seeded_and_editable(seeded, client: Client) -> None:
    settings = SiteSettings.objects.get()
    assert len(settings.footer_columns_uz) == 4 and len(settings.footer_columns_ru) == 4
    html = client.get("/ru/").content.decode()
    assert "Рак молочной железы" in html
    assert 'href="/ru/zhenskiy/osvedomlennost/rak-molochnoy-zhelezy/#bosqichlari"' in html
    # an editor's change is never overwritten by the seed
    settings.footer_columns_uz = []
    settings.save()
    from apps.core.seed.builder import Seeder

    Seeder().run()
    settings.refresh_from_db()
    assert len(settings.footer_columns_uz) == 4  # empty again → refilled
    first = settings.footer_columns_uz[0].value
    first["title"] = "Tahrirlangan"
    settings.save()
    Seeder().run()
    settings.refresh_from_db()
    assert settings.footer_columns_uz[0].value["title"] == "Tahrirlangan"
    assert Locale.objects.filter(language_code="ru").exists()
