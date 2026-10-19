"""Videos the client sent on 2026-10-19 (D-097): interviews on the Anhor.uz channel, not on the
portal's own channel, so the YouTube sync (D-085) never brings them.

`add_client_videos()` creates the missing ones with their YouTube cover (a cover YouTube does not
give now comes with a later sync run, like a synced video's) and on a video that already exists
fills only empty fields: an editor's change stays. Titles are YouTube's; the Russian titles of the
first and fourth video and all descriptions are the client's text (typing slips fixed), the other
Russian titles are ours. Run by `manage.py client_update_20261019`; a second run changes nothing.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.core.cache import cache


@dataclass(frozen=True)
class ClientVideo:
    video_id: str
    title: str
    title_ru: str
    description: str
    description_ru: str
    topic: str = ""


# the client's order; the first one ends up on top of the «Videoroliklar» list
VIDEOS = (
    ClientVideo(
        "l8M_ZRs8Qe4",
        "KOʻKRAK BEZI SARATONINING DAVOSI BORMI?",
        "Возможно ли вылечиться от рака молочной железы?",
        "Taniqli radio boshlovchi, jurnalist Nazira Inoyatova malakali onkolog, mammolog, "
        "Respublika ixtisoslashtirilgan onkologiya va radiologiya ilmiy-amaliy tibbiyot markazi "
        "Toshkent shahar filiali shifokori Dilfuza Aliyeva bilan ayni mavzuda suhbatlashdi.",
        "Известная радиоведущая и журналистка Назира Иноятова побеседовала на эту тему с "
        "квалифицированным онкологом-маммологом, врачом Ташкентского городского филиала "
        "Республиканского специализированного научно-практического медицинского центра онкологии и "
        "радиологии Дильфузой Алиевой.",
        "breast",
    ),
    ClientVideo(
        "x_KwUXL_bcc",
        "PSIXOLOGGA FAQAT JINNILAR BORADIMI?",
        "К психологу ходят только сумасшедшие?",
        "Taniqli radio boshlovchi, jurnalist Nazira Inoyatova «Insight» psixologiya va trening "
        "markazi asoschisi Sayyora Azlarova bilan ayni mavzuda suhbatlashdi. Oktabr oyi butun "
        "dunyoda anʼanaviy ravishda koʻkrak bezi saratoniga qarshi kurashga bagʻishlanadi.",
        "Известная радиоведущая и журналистка Назира Иноятова побеседовала на эту тему с Сайёрой "
        "Азларовой, основательницей центра психологии и тренингов Insight. Во всем мире октябрь "
        "традиционно посвящен борьбе с раком молочной железы.",
        "breast",
    ),
    ClientVideo(
        "PPH7M2UX1nM",
        "HAMMA GINEKOLOG ANIQ TASHXIS QOʻYADI DEB OʻYLAYSIZMI?",
        "Думаете, любой гинеколог поставит точный диагноз?",
        "Shifokor-ginekolog, «Oila va nikoh» ilmiy-maslahat poliklinikasi mudiri Dilfuza Aliyeva "
        "bilan hech qanday ogʻriq bezovta qilmasa ham tibbiy koʻrikdan oʻtish nima uchun muhimligi "
        "hamda aynan «alomatlarning sezilmasligi» qanday qilib koʻpincha shifokorga kech murojaat "
        "qilishga sabab boʻlishi haqida suhbat.",
        "Беседа с врачом-гинекологом, заведующей Научно-консультативной поликлиникой «Семья и "
        "брак» Дильфузой Алиевой о том, почему обследования важны даже при отсутствии боли и как "
        "именно «тишина симптомов» часто становится причиной позднего обращения.",
    ),
    ClientVideo(
        "f_uZTcThqGk",
        "SARATONDAN QOʻRQISH OʻLIMGA OLIB KELISHI MUMKIN",
        "Страх перед раком может привести к смерти",
        "Malakali akusher-ginekolog, Respublika ixtisoslashtirilgan ona va bola ilmiy-amaliy "
        "tibbiyot markazining «Oila va nikoh» maslahat poliklinikasi ginekologiya boʻlimi yetakchi "
        "mutaxassisi Gulmiraxon Irisbekova bilan ayni mavzuda suhbat.",
        "Беседа на эту тему с квалифицированным акушером-гинекологом, ведущим специалистом "
        "отделения гинекологии Консультативной поликлиники «Семья и брак» при Республиканском "
        "специализированном научно-практическом медицинском центре здоровья матери и ребенка "
        "Гульмирахон Ирисбековой.",
    ),
    ClientVideo(
        "-Aas08NdhVM",
        "RAK (SARATON) BILAN KASALLANGAN INSONGA UNING DARDI AYTILMAYDI",
        "Человеку, заболевшему раком, не говорят о его болезни",
        "Respublika ixtisoslashtirilgan onkologiya va radiologiya ilmiy-amaliy tibbiyot "
        "markazining palliativ davolash boʻlimi mudiri, onkolog Yahyo Ziyoyev ishtirokidagi sonda "
        "bemorlarni xabardor qilish odobi hamda insonning oʻz tashxisini bilish huquqi muhokama "
        "qilinadi.",
        "В выпуске с онкологом Яхьё Зияевым, руководителем отделения паллиативного лечения "
        "Республиканского специализированного научно-практического медицинского центра онкологии "
        "и радиологии, обсуждаются этика информирования пациентов и право человека знать свой "
        "диагноз.",
    ),
    ClientVideo(
        "62LrAEjPWqM",
        "ANONIM INTERVYU: «ERIMSIZ UDDALAY OLMASDIM»",
        "Анонимное интервью: «Без мужа я бы не справилась»",
        "Ushbu son bir ayolning hikoyasi, uning boshidan kechirganlari hamda tashxis qoʻyilishi va "
        "davolanish jarayonlaridan oʻtgan bemor nigohida tizim qanday koʻrinishi haqida soʻzlaydi.",
        "Этот выпуск строится вокруг истории женщины и ее опыта и того, как система выглядит "
        "глазами пациентки, прошедшей через диагноз и лечение.",
    ),
)
FILLED = ("title_ru", "description", "description_ru", "topic")


def add_client_videos() -> tuple[list[str], list[str]]:
    """Returns the ids of the videos created and of those whose empty fields were filled."""
    from apps.media_library import youtube
    from apps.media_library.models import Video, VideoKind, VideoSource, VideoStatus

    created: list[str] = []
    filled: list[str] = []
    for item in reversed(VIDEOS):  # the list is newest first: the client's first video last
        video = Video.objects.filter(external_url__contains=item.video_id).first()
        if video is None:
            poster = youtube._poster(item.video_id, item.title)
            Video.objects.create(
                title=item.title,
                title_ru=item.title_ru,
                description=item.description,
                description_ru=item.description_ru,
                topic=item.topic,
                kind=VideoKind.LONG,
                source=VideoSource.YOUTUBE,
                external_url=f"https://www.youtube.com/watch?v={item.video_id}",
                poster=poster,
                status=VideoStatus.READY,
            )
            if poster is None:  # the sync's cover repair fetches it later
                key = youtube.COVER_PENDING_KEY.format(item.video_id)
                cache.set(key, 1, youtube.COVER_PENDING_SECONDS)
            created.append(item.video_id)
            continue
        empty = [name for name in FILLED if not getattr(video, name) and getattr(item, name)]
        if empty:
            for name in empty:
                setattr(video, name, getattr(item, name))
            video.save(update_fields=empty)
            filled.append(item.video_id)
    if created or filled:
        from apps.core.cache import bump_page_cache

        bump_page_cache()
    return created, filled
