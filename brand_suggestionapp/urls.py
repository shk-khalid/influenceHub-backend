from django.urls import path
from .views import train_and_evaluate, suggest_brands

urlpatterns = [
    path('train/', train_and_evaluate, name='train_and_evaluate'),
    path('suggest_brands/', suggest_brands, name='suggest_brands'),
]
