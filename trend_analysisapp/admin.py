from django.contrib import admin
from .models import Trend

@admin.register(Trend)
class TrendAdmin(admin.ModelAdmin):
    list_display = ("name", "volume", "category", "region", "growth", "sentiment", "created_at", "popularity", "subreddit")
    search_fields = ("name", "subreddit")
    list_filter = ("category", "region")
