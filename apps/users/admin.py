from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin[User]):
    fieldsets = (
        *DjangoUserAdmin.fieldsets,  # type: ignore[misc]
        ("Erta aniqla", {"fields": ("organisation", "job_title")}),
    )
    list_display = ("username", "email", "first_name", "last_name", "organisation", "is_staff")
