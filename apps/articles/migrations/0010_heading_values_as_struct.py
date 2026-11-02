"""Stored section headings: plain string → {"text": …, "anchor": ""} (D-110).

`SectionHeadingBlock` reads the old string form by itself, but wagtail-localize's segment
extraction reads the raw stream data and expects the struct shape: «Translate this page» raised
AttributeError on a page with an old heading. Pages, their revisions and wagtail-localize's
translation sources are rewritten once; the reverse turns them back into strings.
"""

from __future__ import annotations

import json
from typing import Any

from django.db import migrations

PAGE_MODELS = (("articles", "ArticlePage"), ("posts", "PostPage"), ("stories", "PatientStoryPage"))


def _walk(data: Any, forward: bool) -> tuple[Any, bool]:
    """`data` with every heading block converted; JSON held in strings (revisions keep a
    StreamField as a JSON string) is converted too. Returns (data, changed)."""
    if isinstance(data, list):
        changed = False
        out = []
        for item in data:
            item, item_changed = _walk(item, forward)
            out.append(item)
            changed = changed or item_changed
        return out, changed
    if isinstance(data, dict):
        changed = False
        out_dict = {}
        for key, value in data.items():
            value, value_changed = _walk(value, forward)
            out_dict[key] = value
            changed = changed or value_changed
        if out_dict.get("type") == "heading" and "value" in out_dict:
            value = out_dict["value"]
            if forward and isinstance(value, str):
                out_dict["value"] = {"text": value, "anchor": ""}
                changed = True
            elif not forward and isinstance(value, dict) and not value.get("anchor"):
                out_dict["value"] = value.get("text", "")
                changed = True
        return out_dict, changed
    if isinstance(data, str) and data[:2] in ('[{', '{"') and '"heading"' in data:
        try:
            parsed = json.loads(data)
        except ValueError:
            return data, False
        parsed, changed = _walk(parsed, forward)
        return (json.dumps(parsed, ensure_ascii=False) if changed else data), changed
    return data, False


def _convert(apps: Any, forward: bool) -> None:
    for app_label, model_name in PAGE_MODELS:
        model = apps.get_model(app_label, model_name)
        for page in model.objects.only("pk", "body").iterator():
            raw, changed = _walk(list(page.body.raw_data), forward)
            if changed:
                page.body = raw
                page.save(update_fields=["body"])

    ContentType = apps.get_model("contenttypes", "ContentType")
    content_types = [
        content_type.pk
        for content_type in ContentType.objects.all()
        if (content_type.app_label, content_type.model)
        in {(app, name.lower()) for app, name in PAGE_MODELS}
    ]
    Revision = apps.get_model("wagtailcore", "Revision")
    for revision in Revision.objects.filter(content_type_id__in=content_types).iterator():
        content, changed = _walk(revision.content, forward)
        if changed:
            revision.content = content
            revision.save(update_fields=["content"])

    TranslationSource = apps.get_model("wagtail_localize", "TranslationSource")
    for source in TranslationSource.objects.iterator():
        content, changed = _walk(source.content_json, forward)
        if changed:
            source.content_json = content
            source.save(update_fields=["content_json"])


def forwards(apps: Any, schema_editor: Any) -> None:
    _convert(apps, forward=True)


def backwards(apps: Any, schema_editor: Any) -> None:
    _convert(apps, forward=False)


class Migration(migrations.Migration):
    dependencies = [
        ("articles", "0009_heading_anchor"),
        ("posts", "0009_heading_anchor"),
        ("stories", "0008_heading_anchor"),
        ("wagtailcore", "0094_alter_page_locale"),
        ("wagtail_localize", "0016_rename_page_revision_translationlog_revision"),
    ]

    operations = [migrations.RunPython(forwards, backwards)]
