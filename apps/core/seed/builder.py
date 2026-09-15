"""Builds/updates the TZ page tree in every content language. Idempotent: re-running updates
titles/bodies in place (a new revision only when something changed) and never duplicates."""

from __future__ import annotations

import json
import logging
from typing import Any

from django.db import transaction
from wagtail.contrib.redirects.models import Redirect
from wagtail.models import Locale, Page, Site

from apps.core.models import SiteSettings
from apps.core.seed import tree
from apps.core.seed.tree import TODO, VERIFY, Node, SeedContext

logger = logging.getLogger("ertaaniqla.seed")

DEFAULT_LANGUAGES = ("uz", "ru")


def _strip_ids(data: Any) -> Any:
    """Remove StreamField block ids so two renderings of the same content compare equal."""
    if isinstance(data, dict):
        return {k: _strip_ids(v) for k, v in data.items() if k != "id"}
    if isinstance(data, list):
        return [_strip_ids(item) for item in data]
    return data


def _stream_equal(page: Any, field_name: str, new_json: list[dict[str, Any]]) -> bool:
    """Compare a page's StreamField with new JSON after normalising both through the block."""
    field = page._meta.get_field(field_name)
    current_value = getattr(page, field_name)
    current = _strip_ids(current_value.get_prep_value()) if current_value else []
    new_value = field.to_python(json.dumps(new_json))
    return bool(current == _strip_ids(new_value.get_prep_value()))


class Seeder:
    def __init__(self, languages: tuple[str, ...] = DEFAULT_LANGUAGES) -> None:
        self.languages = tuple(languages)
        self.ctx = SeedContext()
        self.created = 0
        self.updated = 0
        self.unchanged = 0
        self.locales: dict[str, Locale] = {}

    # --- public --------------------------------------------------------------------------------
    @transaction.atomic
    def run(self) -> dict[str, int]:
        for code in self.languages:
            self.locales[code] = Locale.objects.get_or_create(language_code=code)[0]
        homes = self.ensure_home()
        self.ensure_site(homes[self.languages[0]])
        self.ensure_site_settings()
        self.ensure_terms()
        # pass 0: resolve pages that already exist so re-runs build complete bodies at once
        for node in tree.TREE:
            self.resolve_node(node, homes)
        # pass 1: create every page (cross-links may be unresolved on a first run)
        for node in tree.TREE:
            self.build_node(node, homes)
        # pass 2: bodies again now that every key resolves (CTAs to later pages)
        for node in tree.iter_nodes():
            for lang in self.languages:
                page_id = self.ctx.page_id(node.key, lang)
                if page_id is None:
                    continue
                page = Page.objects.get(pk=page_id).specific
                self.apply_body(page, node, lang, publish=True)
        self.ensure_redirects()
        return {"created": self.created, "updated": self.updated, "unchanged": self.unchanged}

    # --- home / site -----------------------------------------------------------------------
    def ensure_home(self) -> dict[str, Any]:
        from apps.home.models import HomePage

        root = Page.get_first_root_node()
        homes: dict[str, Any] = {}
        default = self.languages[0]
        home = HomePage.objects.filter(locale=self.locales[default]).first()
        if home is None:
            home = HomePage(
                title=tree.HOME["title"][default],
                slug=tree.HOME["slug"][default],
                locale=self.locales[default],
            )
            root.add_child(instance=home)
            self.created += 1
        self._apply_home_fields(home, default)
        homes[default] = home
        for lang in self.languages[1:]:
            translated = home.get_translation_or_none(self.locales[lang])
            if translated is None:
                translated = home.copy_for_translation(self.locales[lang], copy_parents=False)
                self.created += 1
            translated = translated.specific
            self._apply_home_fields(translated, lang)
            homes[lang] = translated
        return homes

    def _apply_home_fields(self, home: Any, lang: str) -> None:
        fields = {
            "title": tree.HOME["title"][lang],
            "hero_title": tree.HOME["hero_title"][lang],
            "hero_subtitle": tree.HOME["hero_subtitle"][lang],
        }
        changed = self._set_fields(home, fields)
        stats = [
            tree.stat("—", f"{TODO} 1", VERIFY),
            tree.stat("—", f"{TODO} 2", VERIFY),
            tree.stat("—", f"{TODO} 3", VERIFY),
        ]
        if not _stream_equal(home, "stats", stats):
            home.stats = json.dumps(stats)
            changed = True
        self._publish(home, changed)

    def ensure_site(self, home: Any) -> Site:
        site = Site.objects.filter(is_default_site=True).first()
        if site is None:
            site = Site.objects.create(
                hostname="localhost", port=80, root_page=home, is_default_site=True
            )
        old_root = site.root_page
        if site.root_page_id != home.pk:
            site.root_page = home
            site.save(update_fields=["root_page"])
        # remove Wagtail's default "Welcome" page if it is still around and empty
        if (
            old_root.pk != home.pk
            and old_root.specific_class is Page
            and old_root.get_children_count() == 0
            and old_root.depth == 2
        ):
            old_root.delete()
        return site

    def ensure_site_settings(self) -> None:
        site = Site.objects.get(is_default_site=True)
        SiteSettings.objects.get_or_create(site=site)

    # --- glossary ----------------------------------------------------------------------------
    def ensure_terms(self) -> None:
        from apps.glossary.models import Term

        default = self.languages[0]
        for entry in tree.GLOSSARY_TERMS:
            term_text, synonyms = entry[default]
            term = Term.objects.filter(locale=self.locales[default], term=term_text).first()
            if term is None:
                term = Term.objects.create(
                    locale=self.locales[default],
                    term=term_text,
                    synonyms=synonyms,
                    definition=f"<p>{TODO} {VERIFY}</p>",
                )
                self.created += 1
            self.ctx.terms[default].append(term.pk)
            for lang in self.languages[1:]:
                translated = term.get_translation_or_none(self.locales[lang])
                if translated is None:
                    translated = term.copy_for_translation(self.locales[lang])
                    translated.term, translated.synonyms = entry[lang]
                    translated.definition = f"<p>{TODO} {VERIFY}</p>"
                    translated.save()
                    self.created += 1
                self.ctx.terms[lang].append(translated.pk)

    # --- pages -------------------------------------------------------------------------------
    def resolve_node(self, node: Node, parents: dict[str, Any]) -> None:
        pages: dict[str, Any] = {}
        default = self.languages[0]
        pages[default] = self.locate_page(node, default, parents.get(default), source=None)
        for lang in self.languages[1:]:
            pages[lang] = self.locate_page(node, lang, parents.get(lang), source=pages[default])
        for lang, page in pages.items():
            if page is not None:
                self.ctx.pages[(node.key, lang)] = page.pk
        for child in node.children:
            self.resolve_node(child, pages)

    def locate_page(self, node: Node, lang: str, parent: Any, source: Any | None) -> Any | None:
        """Existing page for (node, lang): translation of `source`, else by slug under parent."""
        locale = self.locales[lang]
        if source is not None:
            page = source.get_translation_or_none(locale)
            if page is not None:
                return page
        if parent is None:
            return None
        model = self.model_for(node.kind)
        return model.objects.child_of(parent).filter(slug=node.slug[lang], locale=locale).first()

    def build_node(self, node: Node, parents: dict[str, Any]) -> None:
        pages: dict[str, Any] = {}
        default = self.languages[0]
        pages[default] = self.upsert_page(node, default, parents[default], source=None)
        for lang in self.languages[1:]:
            pages[lang] = self.upsert_page(node, lang, parents[lang], source=pages[default])
        for child in node.children:
            self.build_node(child, pages)

    def model_for(self, kind: str) -> type[Page]:
        from apps.articles.models import ArticlePage
        from apps.directory.models import DirectoryPage
        from apps.sections.models import SectionIndexPage, TopicIndexPage
        from apps.stories.models import StoryIndexPage

        return {
            "section": SectionIndexPage,
            "topic": TopicIndexPage,
            "article": ArticlePage,
            "directory": DirectoryPage,
            "stories": StoryIndexPage,
        }[kind]

    def upsert_page(self, node: Node, lang: str, parent: Any, source: Any | None) -> Any:
        model = self.model_for(node.kind)
        locale = self.locales[lang]
        page = self.locate_page(node, lang, parent, source)
        is_new = page is None
        fields = self.node_fields(node, lang)
        if is_new:
            if source is not None:
                page = source.copy_for_translation(locale, copy_parents=False)
            else:
                page = model(locale=locale, **fields)
                parent.add_child(instance=page)
            self.created += 1
        assert page is not None
        page = page.specific
        changed = self._set_fields(page, fields) or is_new
        self.ctx.pages[(node.key, lang)] = page.pk
        # body in pass 1 too, so a freshly created page never publishes empty
        changed = self.apply_body(page, node, lang, publish=False) or changed
        self._publish(page, changed, count=not is_new)
        return page

    def node_fields(self, node: Node, lang: str) -> dict[str, Any]:
        fields: dict[str, Any] = {
            "title": node.title[lang],
            "slug": node.slug[lang],
            "show_in_menus": node.show_in_menus,
            "search_description": node.summary.get(lang, "")[:255],
        }
        if node.kind == "section":
            fields.update(
                {
                    "section_key": node.extra["section_key"],
                    "icon": node.extra["icon"],
                    "tagline": node.summary.get(lang, ""),
                }
            )
        elif node.kind in {"topic", "article"}:
            fields["summary"] = node.summary.get(lang, "")
        return fields

    def apply_body(self, page: Any, node: Node, lang: str, publish: bool) -> bool:
        if node.body is None:
            return False
        field_name = "body" if node.kind == "article" else "intro"
        new_body = [block for block in node.body(lang, self.ctx) if block]
        if _stream_equal(page, field_name, new_body):
            return False
        setattr(page, field_name, json.dumps(new_body))
        if publish:
            self._publish(page, True)
        return True

    # --- helpers -------------------------------------------------------------------------------
    @staticmethod
    def _set_fields(page: Any, fields: dict[str, Any]) -> bool:
        changed = False
        for name, value in fields.items():
            if getattr(page, name) != value:
                setattr(page, name, value)
                changed = True
        return changed

    def _publish(self, page: Any, changed: bool, count: bool = True) -> None:
        if not changed and page.live:
            if count:
                self.unchanged += 1
            return
        page.save_revision().publish()
        if count and changed:
            self.updated += 1

    def ensure_redirects(self) -> None:
        for key, paths in tree.REDIRECTS.items():
            for lang, old_path in paths.items():
                page_id = self.ctx.page_id(key, lang)
                if page_id is None:
                    continue
                Redirect.objects.update_or_create(
                    old_path=Redirect.normalise_path(old_path),
                    site=None,
                    defaults={"redirect_page_id": page_id, "is_permanent": True},
                )
