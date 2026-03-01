from django.contrib import admin
from django.db.models import Count
from .models import Subscription, SubscriptionRequest, SubscriptionRequestSchedule


# ==========================================
# Schedule Inline
# ==========================================

class SubscriptionRequestScheduleInline(admin.TabularInline):
    model = SubscriptionRequestSchedule
    extra = 0
    fields = ("day_of_week", "pickup_time", "return_time", "is_off_day")
    show_change_link = True


# ==========================================
# SubscriptionRequest Admin
# ==========================================

@admin.register(SubscriptionRequest)
class SubscriptionRequestAdmin(admin.ModelAdmin):

    list_display = (
        "student",
        "subscription",
        "status",
        "request_date",
        "decision_date",
    )

    list_filter = ("status", "subscription")
    search_fields = ("student__user__email", "subscription__neighborhood")
    inlines = [SubscriptionRequestScheduleInline]

    readonly_fields = ("request_date", "decision_date", "price_snapshot")

    actions = ["approve_requests", "reject_requests", "cancel_requests"]

    # -------------------------
    # Admin Actions
    # -------------------------

    def approve_requests(self, request, queryset):
        for obj in queryset:
            try:
                obj.approve()
            except Exception as e:
                self.message_user(request, f"Error approving: {e}", level="error")

    approve_requests.short_description = "Approve selected requests"

    def reject_requests(self, request, queryset):
        for obj in queryset:
            try:
                obj.reject()
            except Exception as e:
                self.message_user(request, f"Error rejecting: {e}", level="error")

    reject_requests.short_description = "Reject selected requests"

    def cancel_requests(self, request, queryset):
        for obj in queryset:
            try:
                obj.cancel()
            except Exception as e:
                self.message_user(request, f"Error cancelling: {e}", level="error")

    cancel_requests.short_description = "Cancel selected requests"


# ==========================================
# Subscription Inline (Requests under Subscription)
# ==========================================

class SubscriptionRequestInline(admin.TabularInline):
    model = SubscriptionRequest
    extra = 0
    fields = ("student", "status", "request_date")
    readonly_fields = ("request_date",)
    show_change_link = True


# ==========================================
# Subscription Admin
# ==========================================

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):

    list_display = (
        "neighborhood",
        "driver",
        "status",
        "seats",
        "available_seats",
        "duration",
        "start_date",
        "end_date",
        "requests_count",
    )

    list_filter = ("status", "duration", "driver")
    search_fields = ("neighborhood", "driver__user__email")

    inlines = [SubscriptionRequestInline]

    readonly_fields = ("created_at",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_requests_count=Count("requests"))

    def requests_count(self, obj):
        return obj.requests.count()

    requests_count.short_description = "عدد الطلبات"


# ==========================================
# Schedule Admin (اختياري مستقل)
# ==========================================

@admin.register(SubscriptionRequestSchedule)
class SubscriptionRequestScheduleAdmin(admin.ModelAdmin):

    list_display = (
        "request",
        "day_of_week",
        "pickup_time",
        "return_time",
        "is_off_day",
    )

    list_filter = ("day_of_week", "is_off_day")