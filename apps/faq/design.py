"""The question page (/uz/savol-javob/) opens with the client's questions and answers (D-084,
`docs/FAQ.docx`, the same entries as the women's «Savol-javob» tab — `apps.core.seed.women_faq`).
Editorial entries, no visitor data; Uzbek only until the translator delivers Russian.

`seed_faq_questions` adds an entry only when the same wording does not exist yet, so editors'
answers and removals are kept, and drops the placeholder entries an earlier version created
(answer still exactly the placeholder, nobody answered them).
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.utils import timezone

# the placeholder entries of the first version (2026-10-08) — removed, never re-created
ANSWER_PLACEHOLDER = "<p>[[TODO: content — copywriter]] [[VERIFY: doctor]]</p>"

SECTION_OF_TOPIC = {"breast": "women", "cervical": "women", "children": "children"}
ARTICLE_PATHS = {
    "women.awareness.breast": "ayollar/ogohlik/kokrak-bezi-saratoni/",
    "women.awareness.cervical": "ayollar/ogohlik/bachadon-boyni-saratoni/",
    "women.screening.breast": "ayollar/skrining/kokrak-bezi-saratoni/",
    "women.screening.cervical": "ayollar/skrining/bachadon-boyni-saratoni/",
    "women.treatment.breast": "ayollar/davolash/kokrak-bezi-saratoni/",
    "women.treatment.cervical": "ayollar/davolash/bachadon-boyni-saratoni/",
}


def _article(uz_home: Any, key: str) -> Any:
    from wagtail.models import Page

    path = ARTICLE_PATHS.get(key)
    if not path:
        return None
    page = Page.objects.filter(url_path=f"{uz_home.url_path}{path}").first()
    return page if page is not None and page.live else None


def seed_questions(uz_home: Any) -> int:
    """Create the client's entries that are missing. Returns how many were added."""
    from apps.core.seed.women_faq import entries
    from apps.faq.models import Question, QuestionStatus

    Question.objects.filter(
        status=QuestionStatus.PUBLISHED, answer=ANSWER_PLACEHOLDER, answered_by=None
    ).delete()
    added = 0
    now = timezone.now()
    for order, (topic, category, question, answer, key) in enumerate(entries()):
        if Question.objects.filter(language="uz", topic=topic, text=question).exists():
            continue
        Question.objects.create(
            text=question,
            topic=topic,
            section=SECTION_OF_TOPIC[topic],
            category=category,
            language="uz",
            consent_to_publish=True,
            status=QuestionStatus.PUBLISHED,
            answer="".join(f"<p>{paragraph}</p>" for paragraph in answer),
            article=_article(uz_home, key),
            is_featured=True,
            published_at=now - timedelta(seconds=order),  # the client's order, newest first
        )
        added += 1
    return added
