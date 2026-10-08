"""Final design (D-081, docs/oxirigi_variant Frame-1): the question page opens with the most asked
questions, grouped by category. These are editorial entries (no visitor data): the questions come
from the frame, the answers are placeholders for the doctors — never medical text written here.

`seed_faq_questions` adds a question only when the same wording does not exist yet in that language,
so editors' answers and removals are kept (a deleted question is not re-created while another
published question of the topic remains).
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.utils import timezone

ANSWER_PLACEHOLDER = "<p>[[TODO: content — copywriter]] [[VERIFY: doctor]]</p>"

# topic → [(category, uz question, ru question, uz article path or "")]
QUESTIONS: dict[str, list[tuple[str, str, str, str]]] = {
    "breast": [
        (
            "general",
            "Koʻkrak bezi saratoni nima?",
            "Что такое рак молочной железы?",
            "ayollar/ogohlik/kokrak-bezi-saratoni/",
        ),
        (
            "screening",
            "Skrining oʻzi nima?",
            "Что такое скрининг?",
            "ayollar/skrining/kokrak-bezi-saratoni/",
        ),
        (
            "screening",
            "Koʻkrak bezi saratonini erta aniqlasa boʻladimi?",
            "Можно ли выявить рак молочной железы на ранней стадии?",
            "ayollar/skrining/kokrak-bezi-saratoni/",
        ),
        (
            "signs",
            "Koʻkrak bezi saratonining belgilari qanday?",
            "Каковы признаки рака молочной железы?",
            "ayollar/ogohlik/kokrak-bezi-saratoni/",
        ),
        (
            "signs",
            "Koʻkrak bezi saratoni sabablari nimada?",
            "Каковы причины рака молочной железы?",
            "ayollar/ogohlik/kokrak-bezi-saratoni/",
        ),
        (
            "screening",
            "Skrining kimlarga tavsiya etiladi?",
            "Кому рекомендуется скрининг?",
            "ayollar/skrining/kokrak-bezi-saratoni/",
        ),
        (
            "treatment",
            "Davolash qanday tashkil qilinadi?",
            "Как организовано лечение?",
            "ayollar/davolash/kokrak-bezi-saratoni/",
        ),
    ],
    "cervical": [
        (
            "general",
            "Bachadon boʻyni saratoni nima?",
            "Что такое рак шейки матки?",
            "ayollar/ogohlik/bachadon-boyni-saratoni/",
        ),
        (
            "screening",
            "Bachadon boʻyni saratoni skriningi qanday oʻtkaziladi?",
            "Как проводится скрининг рака шейки матки?",
            "ayollar/skrining/bachadon-boyni-saratoni/",
        ),
        (
            "screening",
            "HPV-test nima uchun kerak?",
            "Зачем нужен ВПЧ-тест?",
            "ayollar/skrining/bachadon-boyni-saratoni/",
        ),
        (
            "signs",
            "Bachadon boʻyni saratonining belgilari qanday?",
            "Каковы признаки рака шейки матки?",
            "ayollar/ogohlik/bachadon-boyni-saratoni/",
        ),
        (
            "signs",
            "Bachadon boʻyni saratoni xavfini nimalar oshiradi?",
            "Что повышает риск рака шейки матки?",
            "ayollar/ogohlik/bachadon-boyni-saratoni/",
        ),
        (
            "treatment",
            "Davolash qanday tashkil qilinadi?",
            "Как организовано лечение?",
            "ayollar/davolash/bachadon-boyni-saratoni/",
        ),
    ],
    "children": [
        (
            "general",
            "Bolalarda qanday saraton turlari koʻp uchraydi?",
            "Какие виды рака чаще встречаются у детей?",
            "bolalar/onkologiya-haqida/keng-tarqalgan-turlari/",
        ),
        (
            "signs",
            "Bolada qanday belgilarga eʼtibor berish kerak?",
            "На какие признаки у ребёнка стоит обратить внимание?",
            "bolalar/onkologiya-haqida/",
        ),
        (
            "treatment",
            "Bolalarda saraton qanday aniqlanadi va davolanadi?",
            "Как выявляют и лечат рак у детей?",
            "bolalar/diagnostika-va-davolash/",
        ),
        (
            "general",
            "Oila qanday yordam olishi mumkin?",
            "Какую помощь может получить семья?",
            "bolalar/oila-uchun/",
        ),
    ],
}

SECTION_OF_TOPIC = {"breast": "women", "cervical": "women", "children": "children"}


def _article(uz_home: Any, path: str, language: str) -> Any:
    from wagtail.models import Locale, Page

    if not path:
        return None
    page = Page.objects.filter(url_path=f"{uz_home.url_path}{path}").first()
    if page is not None and language != page.locale.language_code:
        locale = Locale.objects.filter(language_code=language).first()
        page = page.get_translation_or_none(locale) if locale else None
    return page if page is not None and page.live else None


def seed_questions(uz_home: Any, languages: tuple[str, ...] = ("uz", "ru")) -> int:
    """Create the missing design questions as published entries. Returns how many were added."""
    from apps.faq.models import Question, QuestionStatus

    added = 0
    now = timezone.now()
    for topic, rows in QUESTIONS.items():
        for order, (category, uz_text, ru_text, path) in enumerate(rows):
            for language in languages:
                text = ru_text if language == "ru" else uz_text
                exists = Question.objects.filter(language=language, topic=topic, text=text).exists()
                if exists:
                    continue
                Question.objects.create(
                    text=text,
                    topic=topic,
                    section=SECTION_OF_TOPIC[topic],
                    category=category,
                    language=language,
                    consent_to_publish=True,
                    status=QuestionStatus.PUBLISHED,
                    answer=ANSWER_PLACEHOLDER,
                    article=_article(uz_home, path, language),
                    is_featured=True,
                    published_at=now - timedelta(seconds=order),
                )
                added += 1
    return added
