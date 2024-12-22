from django.urls import path
from .views import TrendAnalysisView

urlpatterns = [
    path('trendingtopic/', TrendAnalysisView.as_view(), name='trend-analysis'),
]
