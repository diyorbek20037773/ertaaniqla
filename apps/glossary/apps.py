from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class GlossaryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.glossary"
    verbose_name = _("Glossary")
