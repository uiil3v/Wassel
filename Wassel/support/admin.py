from django.contrib import admin
from .models import SupportTicket


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):

    list_display = (
        "ticket_number",
        "name",
        "category",
        "status",
        "handled_by",
        "created_at",
    )

    list_filter = (
        "category",
        "status",
        "created_at",
    )

    search_fields = (
        "ticket_number",
        "name",
        "email",
        "subject",
    )

    readonly_fields = (
        "ticket_number",
        "created_at",
        "updated_at",
        "resolved_at",
        "closed_at",
    )

    ordering = (
        "-created_at",
    )

    fieldsets = (
        (
            "بيانات التذكرة",
            {
                "fields": (
                    "ticket_number",
                    "category",
                    "subject",
                    "message",
                    "attachment",
                )
            }
        ),

        (
            "بيانات المرسل",
            {
                "fields": (
                    "user",
                    "name",
                    "email",
                    "phone",
                )
            }
        ),

        (
            "إدارة التذكرة",
            {
                "fields": (
                    "status",
                    "admin_response",
                    "handled_by",
                )
            }
        ),

        (
            "التواريخ",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                    "resolved_at",
                    "closed_at",
                )
            }
        ),
    )