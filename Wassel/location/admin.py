from django.contrib import admin
from .models import City


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name_ar", "name_en", "slug", "is_active")
    search_fields = ("name_ar", "name_en", "slug")
    list_filter = ("is_active",)
    prepopulated_fields = {"slug": ("name_en",)}