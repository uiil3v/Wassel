from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


class CustomUserAdmin(UserAdmin):
    model = User

    list_display = (
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

    ordering = ("email",)  # 🔥 مهم جدًا بدل username

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("المعلومات الشخصية", {"fields": ("first_name", "last_name", "phone")}),
        ("الصلاحيات", {"fields": ("role", "status", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("تواريخ مهمة", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "first_name", "last_name", "phone", "role", "status", "password1", "password2"),
        }),
    )

    search_fields = ("email", "first_name", "last_name")
    readonly_fields = ("last_login", "date_joined")


admin.site.register(User, CustomUserAdmin)