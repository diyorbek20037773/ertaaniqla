"""One-off: the doctor's feedback of 2026-10-25 on cervical screening (D-105). Run once after the
deploy:

    python manage.py client_update_20261025

* the cervical screening pages (uz, ru) get the screening route — region and district → the
  polyclinic for the test, the Mother & Child Health Centre branch for colposcopy — above
  «Qayerda o'tish mumkin»;
* the «Qayerga murojaat» pages get the same route at the top of their intro;
* the cervical awareness pages lose cytomegalovirus from the infection risk factor and say
  instead that these infections can lower local immunity (the doctor's correction).

Pages with an unpublished draft are skipped (an editor's work is never published by this
command); a page that already has the route is left alone, so a second run changes nothing.
"""

from __future__ import annotations

import json
from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

ROUTE = "screening_route"
INFECTIONS = {
    "OIV, genital gerpes, sitomegalovirus, xlamidioz.": (
        "OIV, genital gerpes, xlamidioz. Bu infeksiyalar mahalliy immunitetni pasaytirishi mumkin."
    ),
    "ВИЧ, генитальный герпес, цитомегаловирус, хламидиоз.": (
        "ВИЧ, генитальный герпес, хламидиоз. Эти инфекции могут снижать местный иммунитет."
    ),
}
WHERE_TITLES = ("Qayerda oʻtish mumkin", "Qayerda o'tish mumkin", "Где пройти")


def _language(page: Any) -> str:
    return "ru" if page.locale.language_code == "ru" else "uz"


def _publish(page: Any) -> None:
    page.save_revision(log_action=True).publish()


class Command(BaseCommand):
    help = "Screening route on the cervical screening and directory pages; infections text (D-105)."

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        from wagtail.models import Page

        from apps.core.seed.women_figma import screening_route
        from apps.directory.models import DirectoryPage

        report: list[str] = []

        screening = Page.objects.filter(
            url_path__endswith="/ayollar/skrining/bachadon-boyni-saratoni/"
        ).first()
        for page in self._versions(screening):
            report.append(self._add_route_to_body(page, screening_route(_language(page))))

        for page in DirectoryPage.objects.live():
            report.append(self._add_route_to_intro(page, screening_route(_language(page))))

        awareness = Page.objects.filter(
            url_path__endswith="/ayollar/ogohlik/bachadon-boyni-saratoni/"
        ).first()
        for page in self._versions(awareness):
            report.append(self._fix_infections(page))

        for line in report:
            self.stdout.write(line)

    @staticmethod
    def _versions(page: Any) -> list[Any]:
        """The page and its translations, as their specific models."""
        if page is None:
            return []
        return [p.specific for p in page.get_translations(inclusive=True)]

    @staticmethod
    def _blocked(page: Any) -> str:
        if page.has_unpublished_changes:
            return f"skipped (unpublished draft): {page.url_path}"
        return ""

    def _add_route_to_body(self, page: Any, block: dict[str, Any]) -> str:
        if skip := self._blocked(page):
            return skip
        raw = list(page.body.raw_data)
        if any(item.get("type") == ROUTE for item in raw):
            return f"route already there: {page.url_path}"
        where = next(
            (
                index
                for index, item in enumerate(raw)
                if item.get("type") == "text_card"
                and str((item.get("value") or {}).get("title", "")) in WHERE_TITLES
            ),
            len(raw),
        )
        raw.insert(where, block)
        page.body = raw
        _publish(page)
        return f"route added: {page.url_path}"

    def _add_route_to_intro(self, page: Any, block: dict[str, Any]) -> str:
        if skip := self._blocked(page):
            return skip
        raw = list(page.intro.raw_data)
        if any(item.get("type") == ROUTE for item in raw):
            return f"route already there: {page.url_path}"
        page.intro = [block, *raw]
        _publish(page)
        return f"route added to the intro: {page.url_path}"

    def _fix_infections(self, page: Any) -> str:
        if skip := self._blocked(page):
            return skip
        text = json.dumps(list(page.body.raw_data), ensure_ascii=False)
        changed = text
        for old, new in INFECTIONS.items():
            changed = changed.replace(old, new)
        if changed == text:
            return f"infections text not the seeded one (kept): {page.url_path}"
        page.body = json.loads(changed)
        _publish(page)
        return f"infections text corrected: {page.url_path}"
