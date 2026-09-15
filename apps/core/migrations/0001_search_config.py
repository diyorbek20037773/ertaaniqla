"""Create the `unaccent` extension and the `ertaaniqla` full-text search configuration
(spec §7): `simple` dictionary + unaccent so uz (Latin, with oʻ/gʻ) and ru text share one config.
"""

from django.contrib.postgres.operations import UnaccentExtension
from django.db import migrations

CREATE_CONFIG = """
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_ts_config WHERE cfgname = 'ertaaniqla') THEN
        CREATE TEXT SEARCH CONFIGURATION ertaaniqla (COPY = simple);
        ALTER TEXT SEARCH CONFIGURATION ertaaniqla
            ALTER MAPPING FOR hword, hword_part, word, asciiword, asciihword, hword_asciipart
            WITH unaccent, simple;
    END IF;
END
$$;
"""

DROP_CONFIG = "DROP TEXT SEARCH CONFIGURATION IF EXISTS ertaaniqla;"


class Migration(migrations.Migration):
    initial = True
    dependencies: list[tuple[str, str]] = []
    operations = [
        UnaccentExtension(),
        migrations.RunSQL(CREATE_CONFIG, reverse_sql=DROP_CONFIG),
    ]
