"""One-off: the doctor's patient route for cervical screening and the client's wording (D-113,
docs/new_edits/ of 2026-11-16). Run once after the deploy:

    python manage.py client_update_20261116

* every screening-route block (cervical screening pages, the directory pages' intro) gets the
  doctor's 8 steps — where each takes place, the branches after a result, «what CIN means» —
  under the title «Tekshiruv qadamlari» / «Этапы обследования»;
* no «murojaat»: the directory page is «Tekshiruv yoʻlagi va tibbiyot muassasalari» /
  «Медицинские учреждения и путь проверки», its callout «Tibbiyot muassasalari», the footer link
  carries the page's new name and the closing «Murojaat qilish» / «Обратиться» pills say
  «Sizning tekshiruv yoʻlagingiz» / «Ваш путь к проверке» (the header button and the other
  labels are translations, shipped with the code).

Pages with an unpublished draft are skipped (an editor's work is never published by this
command); a second run changes nothing.
"""

from __future__ import annotations

import json
from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction
from wagtail.blocks import StreamValue

ROUTE = "screening_route"
DIRECTORY_TITLES = {
    "uz": "Tekshiruv yoʻlagi va tibbiyot muassasalari",
    "ru": "Медицинские учреждения и путь проверки",
}
OLD_DIRECTORY_TITLES = {"Qayerga murojaat qilish", "Куда обратиться"}
CALLOUT_TITLES = {
    "Qayerga murojaat qilish": "Tibbiyot muassasalari",
    "Куда обратиться": "Медицинские учреждения",
}
# «Sizning tekshiruv yoʻlagi»: the first wording, live for a day (grammar fix, 2026-11-16)
OLD_PILLS = {"Murojaat qilish", "Обратиться", "Sizning tekshiruv yoʻlagi"}
OLD_LINKS = {"Murojaat qilish", "Куда обратиться", *OLD_DIRECTORY_TITLES}


def _language(page: Any) -> str:
    return "ru" if page.locale.language_code == "ru" else "uz"


def _walk(data: Any, change: Any) -> bool:
    """Apply `change(block)` to every stream block in `data`, nested ones included; True when
    anything changed."""
    changed = False
    if isinstance(data, list):
        for item in data:
            changed = _walk(item, change) or changed
    elif isinstance(data, dict):
        if "type" in data and "value" in data:
            changed = change(data) or changed
        for value in data.values():
            changed = _walk(value, change) or changed
    return changed


class Command(BaseCommand):
    help = "The doctor's screening route and the client's wording without «murojaat» (D-113)."

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        from wagtail.models import Page

        from apps.directory.models import DirectoryPage

        report: list[str] = []
        directory_ids = set(DirectoryPage.objects.values_list("pk", flat=True))
        for page in Page.objects.live().specific().order_by("path"):
            fields = [
                name
                for name in ("body", "intro")
                if isinstance(getattr(page, name, None), StreamValue)
            ]
            if not fields:
                continue
            language = _language(page)
            rename = page.pk in directory_ids and page.title in OLD_DIRECTORY_TITLES
            raws = {
                name: json.loads(json.dumps(list(getattr(page, name).raw_data))) for name in fields
            }
            changed = [
                name for name in fields if _walk(raws[name], self._fix(language, directory_ids))
            ]
            if not changed and not rename:
                continue
            if page.has_unpublished_changes:
                report.append(f"skipped (unpublished draft): {page.url_path}")
                continue
            for name in changed:
                setattr(page, name, raws[name])
            if rename:
                page.title = page.draft_title = DIRECTORY_TITLES[language]
            page.save_revision(log_action=True).publish()
            what = ", ".join(changed + (["title"] if rename else []))
            report.append(f"updated ({what}): {page.url_path}")
        report.append(self._footer())
        for line in report:
            self.stdout.write(line)

    @staticmethod
    def _fix(language: str, directory_ids: set[int]) -> Any:
        from apps.core.seed.women_figma import APPEAL_LABEL, route_value

        new_route = route_value(language)
        pill = APPEAL_LABEL[1] if language == "ru" else APPEAL_LABEL[0]

        def change(block: dict[str, Any]) -> bool:
            value = block["value"]
            if block["type"] == ROUTE and isinstance(value, dict):
                # the doctor's route is in once its title and note are (stored list items carry
                # ids, so the steps never compare equal to the seed's)
                if (
                    value.get("title") == new_route["title"]
                    and value.get("note") == new_route["note"]
                ):
                    return False
                block["value"] = {**new_route}
                return True
            if (
                block["type"] == "callout"
                and isinstance(value, dict)
                and value.get("title") in CALLOUT_TITLES
            ):
                value["title"] = CALLOUT_TITLES[value["title"]]
                return True
            if block["type"] == "cta" and isinstance(value, dict):
                link = value.get("link") or {}
                if value.get("button_label") in OLD_PILLS and link.get("page") in directory_ids:
                    value["button_label"] = pill
                    return True
            return False

        return change

    @staticmethod
    def _footer() -> str:
        """The footer link to the directory carries the page's new name."""
        from wagtail.models import Site

        from apps.core.models import SiteSettings
        from apps.directory.models import DirectoryPage

        site = Site.objects.filter(is_default_site=True).first()
        if site is None:
            return "footer: no default site"
        settings = SiteSettings.for_site(site)
        directory_ids = set(DirectoryPage.objects.values_list("pk", flat=True))
        moved = 0
        for field, language in (("footer_columns_uz", "uz"), ("footer_columns_ru", "ru")):
            raw = json.loads(json.dumps(list(getattr(settings, field).raw_data)))
            changed = False
            for column in raw:
                for link in column.get("value", {}).get("links", []):
                    value = link.get("value", link)
                    if value.get("page") in directory_ids and value.get("label") in OLD_LINKS:
                        value["label"] = DIRECTORY_TITLES[language]
                        changed = True
                        moved += 1
            if changed:
                setattr(settings, field, raw)
        if moved:
            settings.save()
        return f"footer links renamed: {moved}"
