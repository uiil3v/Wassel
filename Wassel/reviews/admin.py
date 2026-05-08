from django.contrib import admin
from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):

    list_display = (
        "reviewer",
        "reviewed_user",
        "review_type",
        "rating",
        "created_at",
    )

    list_filter = (
        "review_type",
        "rating",
        "created_at",
    )

    search_fields = (
        "reviewer__email",
        "reviewed_user__email",
        "comment",
    )

    readonly_fields = (
        "created_at",
    )

    fieldsets = (
        ("معلومات التقييم", {
            "fields": (
                "reviewer",
                "reviewed_user",
                "subscription_request",
                "review_type",
                "rating",
                "comment",
            )
        }),

        ("معلومات النظام", {
            "fields": (
                "created_at",
            )
        }),
    )