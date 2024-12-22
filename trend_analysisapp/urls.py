from django.urls import path
from .views import TrendAnalysisView, RefreshTrendView

urlpatterns = [
    path('trendingtopic/', TrendAnalysisView.as_view(), name='trend-analysis'),
    path('refresh-trends/', RefreshTrendView.as_view(), name='refresh-trends'),
]
