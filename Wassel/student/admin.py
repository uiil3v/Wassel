from django.contrib import admin
from .models import StudentProfile


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "university_name",
        "neighborhood",
        "gender",
        "created_at",
    )

    list_filter = (
        "gender",
        "university_name",
        "neighborhood",
    )

    search_fields = (
        "user__email",
        "user__first_name",
        "user__last_name",
        "university_name",
    )

    readonly_fields = ("created_at",)

    fieldsets = (
        ("بيانات الحساب", {
            "fields": ("user",)
        }),

        ("بيانات الطالب", {
            "fields": (
                "university_name",
                "neighborhood",
                "gender",
                "location_url",
            )
        }),

        ("معلومات النظام", {
            "fields": ("created_at",)
        }),
    )