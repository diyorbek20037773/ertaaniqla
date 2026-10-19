"""The client's first «Foydali maʼlumotlar» item (docs/new_task_15.10.26/Янгиликлар.docx, D-087).

Client-provided medical text, used verbatim (apostrophes normalised to ʻ / ʼ). The template's
«Qisqa mazmun» is the page's lead, so the body starts after that paragraph instead of repeating
it. Subheadings become h2 / h3, the bullet lines lists. Created once by
`manage.py client_update_20261015`; editors own it afterwards.
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any

from apps.core.seed.women_figma import uz

SLUG = "kokrak-bezi-saratonida-genetik-tekshiruvlar"
TITLE = "Koʻkrak bezi saratonida genetik tekshiruvlar"
TOPIC = "breast"
DATE = datetime.date(2026, 10, 15)
COVER = Path(__file__).resolve().parent / "seed_media" / "genetic-tests-cover.jpg"

SUMMARY = uz(
    "Bugun shifokorlarning fikriga ko'ra saraton — bu hukm emas, balki o'zingiz haqingizda "
    "ko'proq bilib olish uchun imkoniyatdir. Bu yo'ldagi muhim qadamlardan biri — genetik "
    "testdir. U organizmda saratonga moyillik bor-yo'qligini aniqlashga yordam beradi va "
    "profilaktika choralarini to'g'ri tanlash imkonini beradi."
)


def _p(*lines: str) -> str:
    return "".join(f"<p>{uz(line)}</p>" for line in lines)


def _ul(*items: str) -> str:
    return "<ul>" + "".join(f"<li>{uz(item)}</li>" for item in items) + "</ul>"


def _h(level: int, text: str) -> str:
    return f"<h{level}>{uz(text)}</h{level}>"


BODY_HTML = "".join(
    [
        _h(2, "Genetik test nimani ko'rsatadi"),
        _p(
            "Har bir odamda hujayralarning “to'g'rilanishi” va ishlashini boshqaruvchi genlar bor. "
            "Ba’zan bu genlarda mutatsiya — ya’ni kichik “nosozliklar” yuz beradi. Ular ikki xil "
            "bo'ladi:"
        ),
        _ul(
            "Irsiy (germinal) — ota-onadan bolaga o'tadi va tananing barcha hujayralarida mavjud "
            "bo'ladi.",
            "Orttirilgan (somatik) — faqat o'simta hujayralarida paydo bo'ladi va nasldan-naslga "
            "o'tmaydi.",
        ),
        _p("Ko‘krak bezi saratonining taxminan 10 foizi aynan irsiy mutatsiyalar bilan bog'liq."),
        _h(2, "Ko'krak bezi saratoni xavfini oshiruvchi genlar"),
        _p(
            "Eng keng tarqalgan turlari — BRCA1 va BRCA2 genlari bo'lib, ularning nomi BReast "
            "CAncer — “Ko‘krak bezi saratoni” so'zlaridan olingan. Bu genlardagi buzilishlar "
            "hujayralarning o'zini tiklash jarayonini buzadi va natijada ayollarda sut bezi hamda "
            "tuxumdon saratoni rivojlanish ehtimoli oshadi.",
            "Ko'p hollarda bu mutatsiyalar uch karra manfiy (triple-negative) turdagi saratonga "
            "chalingan ayollarda uchraydi.",
            "BRCA genidan tashqari boshqa kamroq uchraydigan genlar ham saraton xavfi darajasini "
            "oshiradi — PALB2, CHEK2, CDH1, STK11, BRIP1, PTEN. Ularning tahlili odatda shifokor "
            "tavsiyasi bilan o'tkaziladi.",
        ),
        _h(2, "Kimlarga genetik test tavsiya etiladi"),
        _p("Quyidagi holatlarda BRCA mutatsiyalariga test topshirish muhim:"),
        _ul(
            "ko‘krak bezi saratoni 50 yoshgacha aniqlangan bo'lsa;",
            "uch karra manfiy turdagi saraton 60 yoshgacha aniqlangan bo'lsa;",
            "oilada ikkita yoki undan ko'p ko‘krak bezi saratoni holatlari bo'lsa, ulardan biri "
            "50 yoshgacha bo'lsa;",
            "erkak kishiga ko‘krak bezi saratoni tashxisi qo'yilgan bo'lsa;",
            "yaqin qarindoshlarda tuxumdon, oshqozon osti bezi yoki prostata saratoni bo'lgan "
            "bo'lsa.",
        ),
        _p(
            "Agar onangiz, opa-singlingiz yoki qizingizda shunday kasalliklar bo'lgan bo'lsa, test "
            "natijasi sizning xavf darajangizni aniqlashga yordam beradi."
        ),
        _h(2, "Genetik test qanday o'tadi"),
        _p(
            "Bu oddiy tahlil: qon namunasi yoki yonoq shilliq pardasidan surtma (bukkal epiteliy) "
            "olinadi.",
            "Eng ko'p ishlatiladigan ikki usul bor:",
        ),
        _h(3, "1. PZR (polimeraza zanjirli reaksiya)"),
        _p(
            "Bu usul BRCA genlarining eng muhim qismlarini tekshiradi — u yerda 85% mutatsiyalar "
            "uchraydi.",
            "Afzalliklari: tez, arzon va keng tarqalgan.",
            "Natija 7–10 kunda tayyor bo'ladi.",
            "Kamchiligi: kamyob mutatsiya turlari aniqlanmay qolishi mumkin.",
        ),
        _h(3, "2. NGS (Next Generation Sequencing) — yangi avlod sekvenlash usuli"),
        _p(
            "Bu tahlil genning butun ketma-ketligini o'qiydi, shuning uchun har qanday mutatsiyani "
            "aniqlash mumkin.",
            "U ancha qimmat va uzoqroq davom etadi — taxminan 1,5 oy, lekin eng to'liq natijani "
            "beradi.",
        ),
        _h(2, "Natijalar qanday talqin qilinadi"),
        _ul(
            "Mutatsiya aniqlanmadi — xavf o'rtacha darajada yoki test bu turdagi mutatsiyani "
            "aniqlamaydi.",
            "Mutatsiya aniqlangan — genning bir qismida “nosozlik” bor va u saraton rivojlanish "
            "ehtimolini oshiradi.",
        ),
        _p(
            "Bu holatda shifokor-genetik sizga xavfni baholashda va kuzatuv rejasini tuzishda "
            "yordam beradi.",
            "Buni tushunish muhimdir: mutatsiya borligi saraton albatta paydo bo'ladi degani "
            "emas. Bu faqat sog'liqqa jiddiyroq e’tibor berish kerakligi haqida signal.",
        ),
        _h(2, "Noma’lum klinik ahamiyatli holatlar"),
        _p(
            "Ba’zan test natijasida “noma’lum klinik ahamiyatli holat” deb yoziladi. Bu "
            "mutatsiyaning topilganligini, lekin hozircha ilm-fan uning saraton xavfiga ta’sirini "
            "aniqlay olmaganligini bildiradi. Bunday hollarda shifokor-genetik bu holatni o'xshash "
            "mutatsiyalar bilan solishtirib, ehtimoliy xavf darajasini baholaydi."
        ),
        _h(2, "Buni yodda saqlash muhim"),
        _ul(
            "Ko‘krak bezi saratonining 10 foizgacha holatlari irsiy mutatsiyalar bilan bog'liq.",
            "Eng muhim genlar — BRCA1 va BRCA2, lekin boshqa genlar ham mavjud.",
            "Genetik test ayniqsa oilaviy anamnezda saraton bo'lgan holatlarda yoki erta yoshda "
            "tashxis qo'yilgan ayollar uchun muhim.",
            "Tahlil oddiy, xavfsiz va kelajakdagi profilaktika yo'lini aniqlashga yordam beradi.",
        ),
        _p(
            "O'z genlaringizni bilish — bu hukm emas, balki sog'lig'ingizni himoya qilish "
            "imkoniyatidir."
        ),
    ]
)


def _cover() -> Any:
    from django.core.files.images import ImageFile
    from PIL import Image as PILImage

    from apps.media_library.models import PortalImage

    data = COVER.read_bytes()
    image = PortalImage(title=TITLE, description=TITLE)
    with COVER.open("rb") as handle:
        image.file.save(COVER.name, ImageFile(handle), save=False)
    with PILImage.open(COVER) as picture:
        image.width, image.height = picture.size
    image.file_size = len(data)
    image.save()
    return image


def create_first_news(index: Any) -> Any:
    """Publish the item under the uz «Foydali maʼlumotlar» list unless it is there already.
    Returns the new page, or None when it existed."""
    from apps.posts.models import PostPage

    if PostPage.objects.child_of(index).filter(slug=SLUG).exists():
        return None
    page = PostPage(
        title=TITLE,
        slug=SLUG,
        locale=index.locale,
        topic=TOPIC,
        date=DATE,
        summary=SUMMARY,
        image=_cover(),
        body=[{"type": "rich_text", "value": BODY_HTML}],
    )
    index.add_child(instance=page)
    page.save_revision().publish()
    return page


RU_SLUG = "geneticheskie-issledovaniya-pri-rake-molochnoy-zhelezy"


def create_russian_news(uz_page: Any) -> Any:
    """The Russian version of the item (translation dictionary, D-088) under the Russian list.
    Returns the new page, or None when it exists, a translation is missing or the Russian list
    is not there."""
    from wagtail.models import Locale

    from apps.core.seed.ru_translate import dictionary, translate

    locale = Locale.objects.filter(language_code="ru").first()
    if locale is None or uz_page.get_translation_or_none(locale) is not None:
        return None
    if uz_page.get_parent().get_translation_or_none(locale) is None:
        return None
    words = dictionary()
    missing: list[str] = []
    body = translate([{"type": "rich_text", "value": BODY_HTML}], words, missing)
    title, summary = words.get(TITLE), words.get(SUMMARY)
    if missing or not title or not summary:
        return None
    page = uz_page.copy_for_translation(locale)
    page.title = page.draft_title = title
    page.slug = RU_SLUG
    page.summary = summary
    page.body = body
    page.save_revision().publish()
    return page


# --- the client's Word news (scripts/news_docx.py → apps/posts/news/*.json), 2026-10-16 -------
NEWS_DIR = Path(__file__).resolve().parent / "news"


def news_batches() -> list[list[dict[str, Any]]]:
    import json

    return [
        json.loads(path.read_text(encoding="utf-8")) for path in sorted(NEWS_DIR.glob("*.json"))
    ]


def _image(file_name: str, title: str) -> Any:
    from django.core.files.images import ImageFile
    from PIL import Image as PILImage

    from apps.media_library.models import PortalImage

    existing = PortalImage.objects.filter(file__endswith=file_name).first()
    if existing is not None:
        return existing
    path = COVER.parent / file_name
    image = PortalImage(title=title[:255], description=title[:255])
    with path.open("rb") as handle:
        image.file.save(file_name, ImageFile(handle), save=False)
    with PILImage.open(path) as picture:
        image.width, image.height = picture.size
    image.file_size = path.stat().st_size
    image.save()
    return image


def _fill(page: Any, text: dict[str, str]) -> None:
    page.title = page.draft_title = text["title"]
    page.summary = text["summary"][:500]
    page.body = [{"type": "rich_text", "value": text["body"]}]


def publish_item(index: Any, item: dict[str, Any]) -> tuple[bool, bool]:
    """Create the item under the uz list (and its Russian version) when it is missing. A Russian
    version nobody edited (seeded, no revision by a person) takes the client's own Russian.
    Returns (uz created, ru created or updated)."""
    import datetime as dt

    from wagtail.models import Locale

    from apps.posts.models import PostPage

    uz_page = PostPage.objects.child_of(index).filter(slug=item["slug"]).first()
    created = uz_page is None
    if uz_page is None:
        uz_page = PostPage(
            slug=item["slug"],
            locale=index.locale,
            topic=item["topic"],
            date=dt.date.fromisoformat(item["date"]),
            image=_image(item["cover"], item["uz"]["title"]) if item["cover"] else None,
        )
        _fill(uz_page, item["uz"])
        index.add_child(instance=uz_page)
        uz_page.save_revision().publish()
    ru_text = item.get("ru") or {}
    locale = Locale.objects.filter(language_code="ru").first()
    if not ru_text.get("body") or locale is None:
        return created, False
    if index.get_translation_or_none(locale) is None:
        return created, False
    ru_page = uz_page.get_translation_or_none(locale)
    if ru_page is None:
        ru_page = uz_page.copy_for_translation(locale)
        ru_page.slug = item["slug_ru"] or ru_page.slug
    else:
        revision = ru_page.latest_revision
        if revision is not None and revision.user_id is not None:
            return created, False  # an editor's text is kept
        body = [block.get("value") for block in ru_page.specific.body.get_prep_value()]
        if (ru_page.title, ru_page.summary, body) == (
            ru_text["title"],
            ru_text["summary"][:500],
            [ru_text["body"]],
        ):
            return created, False  # already the client's text
    ru_page = ru_page.specific
    _fill(ru_page, ru_text)
    ru_page.save_revision().publish()
    return created, True


def publish_client_news() -> tuple[int, int]:
    """Every item of every batch, oldest batch first; inside a batch the last item first, so the
    list (newest first) shows them in the file's order."""
    from apps.posts.models import PostIndexPage, PostKind

    index = PostIndexPage.objects.filter(locale__language_code="uz", kind=PostKind.NEWS).first()
    if index is None:
        return 0, 0
    uz_count = ru_count = 0
    for batch in reversed(news_batches()):
        for item in reversed(batch):
            made, translated = publish_item(index, item)
            uz_count += made
            ru_count += translated
    return uz_count, ru_count
