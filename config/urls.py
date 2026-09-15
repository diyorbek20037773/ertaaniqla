"""URL configuration (spec §4.4).

/                       → language redirect (Accept-Language aware, cookie remembers)
/uz/… /ru/…             → i18n_patterns: wagtail pages, app views
/cms/                   → Wagtail admin (2FA)
/django-admin/          → superusers only
/healthz/ /readyz/      → no auth, no cache
/sitemap.xml /robots.txt
"""

from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.utils.translation import gettext_lazy as _
from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls

from apps.core import views as core_views

urlpatterns = [
    path("healthz/", core_views.healthz, name="healthz"),
    path("readyz/", core_views.readyz, name="readyz"),
    path("robots.txt", core_views.robots_txt, name="robots_txt"),
    path("sitemap.xml", core_views.sitemap_index, name="sitemap_index"),
    path("", core_views.language_redirect, name="language_redirect"),
    path("i18n/", include("django.conf.urls.i18n")),
    path("django-admin/", admin.site.urls),
    path(f"{settings.CMS_URL_PREFIX}/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    path("metrics", core_views.metrics, name="metrics"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    if "debug_toolbar" in settings.INSTALLED_APPS:
        from debug_toolbar.toolbar import debug_toolbar_urls

        urlpatterns += debug_toolbar_urls()

urlpatterns += i18n_patterns(
    path("sitemap.xml", core_views.sitemap_language, name="sitemap_language"),
    # translated URL segment: uz "qidiruv/", ru "poisk/" (spec §4.4)
    path(_("qidiruv/"), include("apps.search.urls")),
    # Wagtail serves every page (sections, articles, tools pages, directory, faq, …)
    path("", include(wagtail_urls)),
    prefix_default_language=True,
)
