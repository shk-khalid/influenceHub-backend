from django.urls import path
from .views import BrandListView, BrandDetailListView

urlpatterns = [
    path('brands/', BrandListView.as_view(), name="Brand-List"),
    path('brands/<uuid:pk>/', BrandDetailListView.as_view(), name="Brand-Details")
]
