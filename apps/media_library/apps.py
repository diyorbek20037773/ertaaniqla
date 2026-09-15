from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class MediaLibraryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.media_library"
    verbose_name = _("Media library")

    def ready(self) -> None:
        from apps.media_library import signals  # noqa: F401  (registers receivers)
