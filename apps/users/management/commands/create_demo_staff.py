"""UAT / e2e accounts: one user per CMS role with a known password and TOTP secret.

DEV AND STAGING-UAT ONLY. Refuses to run unless DEBUG is on or `--allow-non-debug` is given
(staging UAT); never run it in production — the secrets are published in this file.

    python manage.py create_demo_staff
    python manage.py create_demo_staff --password '…' --totp-key <40 hex chars>

The printed otpauth:// URI can be added to any authenticator app (or use the key directly).
tests/e2e/cms_helpers.py computes codes from the same default key.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.users.roles import ADMIN, EDITOR, MEDICAL_REVIEWER

DEMO_PASSWORD = "demo-Erta-aniqla-2026"  # noqa: S105 - documented dev/UAT credential
ALLOWED_ENVIRONMENTS = ("dev", "test", "ci", "staging")
DEMO_TOTP_KEY = "3132333435363738393031323334353637383930"  # RFC 6238 test secret (hex)

DEMO_USERS: tuple[dict[str, str], ...] = (
    {
        "username": "demo-editor",
        "role": EDITOR,
        "first_name": "Demo",
        "last_name": "Muharrir",
        "organisation": "Erta aniqla",
        "job_title": "Copywriter",
    },
    {
        "username": "demo-reviewer",
        "role": MEDICAL_REVIEWER,
        "first_name": "Demo",
        "last_name": "Shifokor",
        "organisation": "RONC [[VERIFY: demo]]",
        "job_title": "Oncologist",
    },
    {
        "username": "demo-admin",
        "role": ADMIN,
        "first_name": "Demo",
        "last_name": "Admin",
        "organisation": "Erta aniqla",
        "job_title": "Content lead",
    },
)


class Command(BaseCommand):
    help = "Create demo CMS users (editor, reviewer, admin) with a known password and TOTP key."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--password", default=DEMO_PASSWORD)
        parser.add_argument("--totp-key", default=DEMO_TOTP_KEY, help="hex-encoded secret")
        parser.add_argument(
            "--allow-non-debug",
            action="store_true",
            help="allow with DEBUG=False (staging UAT only, never production)",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        from django.contrib.auth import get_user_model
        from django.contrib.auth.models import Group
        from django_otp.plugins.otp_totp.models import TOTPDevice

        from apps.users.roles import ensure_permissions_exist, ensure_roles

        if not settings.DEBUG and not options["allow_non_debug"]:
            raise CommandError("refusing to create demo staff with DEBUG=False")
        environment = getattr(settings, "ENVIRONMENT", "")
        prod_settings = str(settings.SETTINGS_MODULE).endswith(".prod")
        if environment not in ALLOWED_ENVIRONMENTS or (prod_settings and environment != "staging"):
            raise CommandError(f"refusing to create demo staff in ENVIRONMENT={environment!r}")
        key = options["totp_key"].lower()
        try:
            bytes.fromhex(key)
        except ValueError as exc:
            raise CommandError("--totp-key must be hex") from exc

        ensure_permissions_exist()
        ensure_roles()
        user_model = get_user_model()
        for spec in DEMO_USERS:
            fields = {k: v for k, v in spec.items() if k not in ("username", "role")}
            user, _created = user_model.objects.update_or_create(
                username=spec["username"],
                defaults={**fields, "email": f"{spec['username']}@example.uz", "is_active": True},
            )
            user.set_password(options["password"])
            user.save()
            user.groups.set([Group.objects.get(name=spec["role"])])
            device, _ = TOTPDevice.objects.update_or_create(
                user=user, name="demo", defaults={"key": key, "confirmed": True}
            )
            self.stdout.write(f"{spec['username']:14} {spec['role']:17} {device.config_url}")
        self.stdout.write(self.style.SUCCESS("demo staff ready"))
