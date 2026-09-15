"""Templated email (txt + html) sent through Celery (spec §6)."""

from __future__ import annotations

import logging
from typing import Any

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger("ertaaniqla.mail")


def render_email(template: str, context: dict[str, Any]) -> tuple[str, str]:
    text = render_to_string(f"emails/{template}.txt", context)
    html = render_to_string(f"emails/{template}.html", context)
    return text, html


@shared_task(
    name="core.send_email",
    ignore_result=True,
    autoretry_for=(Exception,),
    retry_backoff=60,
    max_retries=5,
)
def send_email(subject: str, template: str, context: dict[str, Any], to: list[str]) -> int:
    """Send one templated email. Retried with backoff when the SMTP server is down."""
    if not to:
        return 0
    text, html = render_email(template, context)
    message = EmailMultiAlternatives(
        subject=subject, body=text, from_email=settings.DEFAULT_FROM_EMAIL, to=to
    )
    message.attach_alternative(html, "text/html")
    sent = int(message.send())
    logger.info("email %r sent to %d recipient(s)", template, sent)
    return sent
