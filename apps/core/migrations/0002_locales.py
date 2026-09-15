"""Create a Wagtail `Locale` for every content language (uz default, ru) so translations
work from the first migrate — no manual step in the CMS (ADR-0003)."""

from django.conf import settings
from django.db import migrations


def create_locales(apps, schema_editor):
    Locale = apps.get_model("wagtailcore", "Locale")
    for code, _name in settings.WAGTAIL_CONTENT_LANGUAGES:
        Locale.objects.get_or_create(language_code=code)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_search_config"),
        ("wagtailcore", "0094_alter_page_locale"),
    ]
    operations = [migrations.RunPython(create_locales, migrations.RunPython.noop)]
