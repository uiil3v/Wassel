from django.contrib import admin
from .models import DriverProfile


@admin.register(DriverProfile)
class DriverProfileAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "vehicle_model",
        "verification_status",
        "submitted_at",
        "reviewed_at",
    )

    list_filter = (
        "verification_status",
        "submitted_at",
    )

    search_fields = (
        "user__email",
        "vehicle_model",
    )

    readonly_fields = (
        "submitted_at",
        "updated_at",
        "reviewed_at",
    )

    fieldsets = (
        ("معلومات السائق", {
            "fields": ("user", "vehicle_model", "verification_status", "rejection_reason")
        }),
        ("مستندات السائق", {
            "fields": ("id_document_image", "driving_license_image")
        }),
        ("مستندات المركبة", {
            "fields": (
                "vehicle_registration_image",
                "vehicle_insurance_image",
                "vehicle_front_image",
                "vehicle_back_image",
                "vehicle_side_image",
            )
        }),
        ("تواريخ", {
            "fields": ("submitted_at", "updated_at", "reviewed_at")
        }),
    )

    actions = ["approve_drivers", "reject_drivers"]

    def approve_drivers(self, request, queryset):
        for driver in queryset:
            driver.approve()
    approve_drivers.short_description = "✔ الموافقة على السائقين المحددين"

    def reject_drivers(self, request, queryset):
        for driver in queryset:
            driver.reject()
    reject_drivers.short_description = "✖ رفض السائقين المحددين"