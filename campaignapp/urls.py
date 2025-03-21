# campaignapp/urls.py
from django.urls import path
from .views import CreateCampaign, UpdateCampaign, UpdateCampaignStatus

urlpatterns = [
    path('create/', CreateCampaign.as_view(), name='Create Campaign'),
    path('<int:pk>/update/', UpdateCampaign.as_view(), name='Update Campaign'),  
    path('<int:pk>/status/', UpdateCampaignStatus.as_view(), name='Update Campaign Status'),
]
