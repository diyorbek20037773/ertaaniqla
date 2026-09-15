from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class SectionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.sections"
    verbose_name = _("Sections")
