from django.urls import path
from .views import get_brand_demographics

urlpatterns = [
    path('brand/<str:brand_name>/', get_brand_demographics, name='get_brand_demographics'),
]
