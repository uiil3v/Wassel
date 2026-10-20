from django.contrib import admin
from .models import PlatformEarning


@admin.register(PlatformEarning)
class PlatformEarningAdmin(admin.ModelAdmin):

    def has_module_permission(self, request):
        # فقط Super Admin يشوف الأرباح
        return (
            request.user.is_authenticated
            and request.user.role == "admin"
            and request.user.admin_level == 1
        )
