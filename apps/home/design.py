"""Final design (D-081): the landing blocks that are edited in the CMS — direction cards, the
«Bepul skrining» panel, the «Savolingiz bormi?» panel — filled with the approved frames' wording.

Only empty fields are filled, so an editor's text is never overwritten; links point at the
pages of the same language (the uz tree is the source, its translations are used for ru).
The wording is interface copy from the approved design, not medical content.
"""

from __future__ import annotations

from typing import Any

from wagtail.models import Page

UZ: dict[str, Any] = {
    "hero_eyebrow": "Saraton kasalliklarini erta aniqlash portali",
    "directions_eyebrow": "Yoʻnalishlar",
    "directions_title": "Eng koʻp beriladigan savollar",
    "directions_text": (
        "Har bir yoʻnalishda — belgilar, skrining, davolash va qoʻllab-quvvatlash haqida."
    ),
    "screening_eyebrow": "Bepul skrining",
    "screening_title": "Skriningdan qayerda oʻtish mumkin?",
    "screening_text": (
        "Davlat dasturi doirasida ayollar uchun saraton skriningi bepul. Hududingizni tanlang — "
        "yaqin tibbiyot muassasalarini koʻrsatamiz."
    ),
    "cta_title": "Savolingiz bormi?",
    "cta_text": (
        "Mutaxassislarga murojaat yuboring yoki ishonch telefoniga qoʻngʻiroq qiling. "
        "Siz yolgʻiz emassiz."
    ),
    "cards": [
        (
            "breast",
            "Koʻkrak bezi saratoni",
            "Belgilar, xavf omillari, oʻz-oʻzini tekshirish va skrining haqida.",
            "ayollar/ogohlik/kokrak-bezi-saratoni/",
            [
                ("Belgilari", "ayollar/ogohlik/kokrak-bezi-saratoni/", "belgilari"),
                (
                    "Oʻz-oʻzini tekshirish",
                    "ayollar/ogohlik/kokrak-bezi-saratoni/",
                    "oz-ozini-tekshirish",
                ),
                ("Skrining", "ayollar/skrining/kokrak-bezi-saratoni/", ""),
            ],
        ),
        (
            "cervical",
            "Bachadon boʻyni saratoni",
            "Xavf omillari, aniqlash usullari va davolash haqida.",
            "ayollar/ogohlik/bachadon-boyni-saratoni/",
            [
                ("Xavf omillari", "ayollar/ogohlik/bachadon-boyni-saratoni/", "xavf-omillari"),
                (
                    "Aniqlash usullari",
                    "ayollar/ogohlik/bachadon-boyni-saratoni/",
                    "aniqlash-usullari",
                ),
                ("Davolash", "ayollar/davolash/bachadon-boyni-saratoni/", ""),
            ],
        ),
        (
            "children",
            "Bolalar saratoni",
            "Dastlabki alomatlar, diagnostika, parvarish va kasallikdan keyingi hayot.",
            "bolalar/",
            [
                ("Dastlabki alomatlar", "bolalar/onkologiya-haqida/", ""),
                ("Diagnostika", "bolalar/diagnostika-va-davolash/diagnostika/", ""),
                ("Oila uchun maʼlumot", "bolalar/oila-uchun/", ""),
            ],
        ),
    ],
    "steps": [
        (
            "Kimga tavsiya etiladi",
            "Yoshingiz va xavf omillaringizga qarab skrining kerakligini bilib oling.",
            "Tekshirish",
            "ayollar/skrining/kokrak-bezi-saratoni/",
        ),
        (
            "Muassasani tanlang",
            "Hududingizdagi bepul skrining oʻtkaziladigan muassasalar roʻyxati.",
            "Roʻyxatni koʻrish",
            "ayollar/qayerga-murojaat/",
        ),
        (
            "Tekshiruvdan oʻting",
            "Nima kutish kerakligi va natijani qanday olish haqida.",
            "Batafsil",
            "ayollar/skrining/",
        ),
    ],
}

RU: dict[str, Any] = {
    "hero_eyebrow": "Портал раннего выявления онкологических заболеваний",
    "directions_eyebrow": "Направления",
    "directions_title": "Часто задаваемые вопросы",
    "directions_text": "В каждом направлении — о признаках, скрининге, лечении и поддержке.",
    "screening_eyebrow": "Бесплатный скрининг",
    "screening_title": "Где пройти скрининг?",
    "screening_text": (
        "В рамках государственной программы скрининг рака для женщин бесплатный. Выберите "
        "регион — покажем ближайшие медицинские учреждения."
    ),
    "cta_title": "Остались вопросы?",
    "cta_text": ("Отправьте обращение специалистам или позвоните на горячую линию. Вы не одни."),
    "cards": [
        (
            "Рак молочной железы",
            "О признаках, факторах риска, самообследовании и скрининге.",
            ["Признаки", "Самообследование", "Скрининг"],
        ),
        (
            "Рак шейки матки",
            "О факторах риска, методах выявления и лечении.",
            ["Факторы риска", "Методы выявления", "Лечение"],
        ),
        (
            "Детский рак",
            "Первые признаки, диагностика, уход и жизнь после болезни.",
            ["Первые признаки", "Диагностика", "Информация для семьи"],
        ),
    ],
    "steps": [
        (
            "Кому рекомендуется",
            "Узнайте, нужен ли вам скрининг, с учётом возраста и факторов риска.",
            "Проверить",
        ),
        (
            "Выберите учреждение",
            "Учреждения вашего региона, где проводят бесплатный скрининг.",
            "Смотреть список",
        ),
        ("Пройдите обследование", "Чего ожидать и как получить результат.", "Подробнее"),
    ],
}

TEXT_FIELDS = (
    "hero_eyebrow",
    "directions_eyebrow",
    "directions_title",
    "directions_text",
    "screening_eyebrow",
    "screening_title",
    "screening_text",
    "cta_title",
    "cta_text",
)


def _page(uz_home: Page, path: str, home: Page) -> Page | None:
    """The page at `<uz home>/<path>` in the language of `home` (None when missing)."""
    page = Page.objects.filter(url_path=f"{uz_home.url_path}{path}").first()
    if page is None:
        return None
    if page.locale_id != home.locale_id:
        page = page.get_translation_or_none(home.locale)
    return page if page is not None and page.live else None


def design_values(home: Page, uz_home: Page) -> dict[str, Any]:
    """Field values of the approved design for `home` (uz or ru)."""
    ru = home.locale.language_code == "ru"
    words = RU if ru else UZ
    values: dict[str, Any] = {field: words[field] for field in TEXT_FIELDS}
    cards = []
    for index, (topic, title, text, page_path, links) in enumerate(UZ["cards"]):
        if ru:
            title, text, labels = RU["cards"][index]
        else:
            labels = [label for label, _path, _anchor in links]
        card_page = _page(uz_home, page_path, home)
        card_links = []
        for label, (_uz_label, path, anchor) in zip(labels, links, strict=True):
            target = _page(uz_home, path, home)
            if target is not None:
                card_links.append({"label": label, "page": target.pk, "anchor": anchor, "url": ""})
        cards.append(
            {
                "type": "card",
                "value": {
                    "topic": topic,
                    "title": title,
                    "text": text,
                    "page": card_page.pk if card_page else None,
                    "links": card_links,
                },
            }
        )
    values["directions"] = cards
    steps = []
    for index, (title, text, link_label, path) in enumerate(UZ["steps"]):
        if ru:
            title, text, link_label = RU["steps"][index]
        target = _page(uz_home, path, home)
        steps.append(
            {
                "type": "step",
                "value": {
                    "title": title,
                    "text": text,
                    "link_label": link_label if target else "",
                    "page": target.pk if target else None,
                    "anchor": "",
                    "url": "",
                },
            }
        )
    values["screening_steps"] = steps
    return values


def fill_home_design(home: Any, uz_home: Page, *, user: Any = None) -> list[str]:
    """Fill the empty final-design fields of `home`; publish a revision when something changed.
    Returns the names of the fields that were filled."""
    values = design_values(home, uz_home)
    changed = []
    for field, value in values.items():
        current = getattr(home, field)
        empty = not current if field in TEXT_FIELDS else not len(current)
        if empty:
            setattr(home, field, value)
            changed.append(field)
    if changed:
        revision = home.save_revision(user=user, log_action=True)
        if home.live:
            revision.publish(user=user)
    return changed
