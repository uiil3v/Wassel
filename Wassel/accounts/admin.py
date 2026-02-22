from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


class CustomUserAdmin(UserAdmin):

    list_display = (
        "username",
        "email",
        "full_name",
        "phone",
        "role",
        "status",
        "is_staff",
    )

    list_filter = (
        "role",
        "status",
        "is_staff",
    )

    fieldsets = UserAdmin.fieldsets + (
        ("معلومات إضافية", {
            "fields": ("phone", "role", "status"),
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ("معلومات إضافية", {
            "fields": ("phone", "role", "status"),
        }),
    )

admin.site.register(User, CustomUserAdmin)