from django.urls import path
from .views import BrandListView, BrandDetailListView

urlpatterns = [
    path('brands/', BrandListView.as_view(), name="brand-list"),
    path('brands/<uuid:pk>/', BrandDetailListView.as_view(), name="brand-details")
]
