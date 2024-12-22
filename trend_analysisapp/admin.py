from django.contrib import admin
from .models import Trend

@admin.register(Trend)
class TrendAdmin(admin.ModelAdmin):
    list_display = ("name", "volume", "category", "region", "growth", "last_updated")
    search_fields = ("name",)
    list_filter = ("category",)