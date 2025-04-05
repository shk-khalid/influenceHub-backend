from django.urls import path, include
from django.contrib import admin

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('authapp.urls')),
    path('campaign/', include('campaignapp.urls')),
    path('trend/', include('trend_analysisapp.urls')),
    path('insight/', include('brands_insightapp.urls')),
    path('suggestions/', include('brand_suggestionapp.urls')),
    path('chat/', include('chatapp.urls')),
]
