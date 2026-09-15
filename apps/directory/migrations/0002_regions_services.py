"""Reference data: the 14 regions of Uzbekistan (12 viloyat + Tashkent city + Karakalpakstan)
and the screening services named in the TZ. Idempotent (get_or_create by code)."""

from django.db import migrations

REGIONS = [
    ("tashkent-city", "Toshkent shahri", "город Ташкент"),
    ("tashkent", "Toshkent viloyati", "Ташкентская область"),
    ("andijan", "Andijon viloyati", "Андижанская область"),
    ("bukhara", "Buxoro viloyati", "Бухарская область"),
    ("fergana", "Fargʻona viloyati", "Ферганская область"),
    ("jizzakh", "Jizzax viloyati", "Джизакская область"),
    ("kashkadarya", "Qashqadaryo viloyati", "Кашкадарьинская область"),
    ("khorezm", "Xorazm viloyati", "Хорезмская область"),
    ("namangan", "Namangan viloyati", "Наманганская область"),
    ("navoi", "Navoiy viloyati", "Навоийская область"),
    ("samarkand", "Samarqand viloyati", "Самаркандская область"),
    ("surkhandarya", "Surxondaryo viloyati", "Сурхандарьинская область"),
    ("syrdarya", "Sirdaryo viloyati", "Сырдарьинская область"),
    ("karakalpakstan", "Qoraqalpogʻiston Respublikasi", "Республика Каракалпакстан"),
]

SERVICES = [
    ("mammography", "Mammografiya", "Маммография"),
    ("ultrasound", "UTT (ultratovush tekshiruvi)", "УЗИ"),
    ("hpv_test", "HPV-test", "ВПЧ-тест"),
    ("cytology", "Sitologik tekshiruv (PAP-test)", "Цитологическое исследование (ПАП-тест)"),
    ("consultation", "Onkolog konsultatsiyasi", "Консультация онколога"),
    ("onco_alertness", "Onkologik ogohlik xonasi", "Кабинет онконастороженности"),
    ("paediatric_oncology", "Bolalar onkologiyasi", "Детская онкология"),
    ("psychological_support", "Psixologik yordam", "Психологическая помощь"),
]


def forwards(apps, schema_editor):
    Region = apps.get_model("directory", "Region")
    Service = apps.get_model("directory", "Service")
    for order, (code, uz, ru) in enumerate(REGIONS, start=1):
        Region.objects.update_or_create(
            code=code, defaults={"name_uz": uz, "name_ru": ru, "sort_order": order}
        )
    for code, uz, ru in SERVICES:
        Service.objects.update_or_create(code=code, defaults={"name_uz": uz, "name_ru": ru})


class Migration(migrations.Migration):
    dependencies = [("directory", "0001_initial")]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
