# campaignapp/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.CreateCampaign.as_view(), name='create_campaign'),
    path('<int:pk>/update/', views.UpdateCampaign.as_view(), name='update_campaign'),  
    path('<int:pk>/status/', views.UpdateCampaignStatus.as_view(), name='update_campaign_status'),
]
