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
from django.templatetags.static import static as static_url
from django.urls import include, path, re_path
from django.utils.functional import lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import RedirectView
from django.views.static import serve
from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls

from apps.core import views as core_views

urlpatterns = [
    path("healthz/", core_views.healthz, name="healthz"),
    path("readyz/", core_views.readyz, name="readyz"),
    path("robots.txt", core_views.robots_txt, name="robots_txt"),
    # lazy: ManifestStaticFilesStorage cannot resolve hashes at import time (before collectstatic)
    path(
        "favicon.ico",
        RedirectView.as_view(url=lazy(static_url, str)("favicon.svg"), permanent=True),
    ),
    path("sitemap.xml", core_views.sitemap_index, name="sitemap_index"),
    path("", core_views.language_redirect, name="language_redirect"),
    path("i18n/", include("django.conf.urls.i18n")),
    path(f"{settings.CMS_URL_PREFIX}/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    path("metrics", core_views.metrics, name="metrics"),
]

# Superuser-only Django admin (users, low-level data). Off on the public host when the CMS covers
# the need — DJANGO_ADMIN_ENABLED=false answers 404 (EA-24).
if settings.DJANGO_ADMIN_ENABLED:
    admin.site.site_header = admin.site.site_title = _("Erta aniqla — administration")
    admin.site.index_title = _("Administration")
    urlpatterns.append(path("django-admin/", admin.site.urls))

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    if "debug_toolbar" in settings.INSTALLED_APPS:
        from debug_toolbar.toolbar import debug_toolbar_urls

        urlpatterns += debug_toolbar_urls()
elif settings.SERVE_MEDIA:
    # Hosts without nginx (Railway demo, EA-04). Same rule as nginx: consent/private documents
    # and raw video uploads are never served from /media/.
    urlpatterns += [
        re_path(
            r"^media/(?P<path>(?!documents/|videos/source/).+)$",
            serve,
            {"document_root": settings.MEDIA_ROOT},
        )
    ]

urlpatterns += i18n_patterns(
    path("sitemap.xml", core_views.sitemap_language, name="sitemap_language"),
    # translated URL segment: uz "qidiruv/", ru "poisk/" (spec §4.4)
    path(_("qidiruv/"), include("apps.search.urls")),
    # Wagtail serves every page (sections, articles, tools pages, directory, faq, …)
    path("", include(wagtail_urls)),
    prefix_default_language=True,
)
