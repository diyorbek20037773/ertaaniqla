"""Celery application. Imported by config/__init__.py so tasks autodiscover on Django start."""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("ertaaniqla")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
