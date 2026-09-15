"""Project configuration package (settings, urls, wsgi/asgi, celery)."""

from config.celery import app as celery_app

__all__ = ["celery_app"]
