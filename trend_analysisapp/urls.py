from django.urls import path
from .views import TrendAnalysisView, RefreshTrendView

urlpatterns = [
    path('trending/', TrendAnalysisView.as_view(), name='Trend Analysis'),
    path('trending/refresh/', RefreshTrendView.as_view(), name='Refresh Trends'),
]
