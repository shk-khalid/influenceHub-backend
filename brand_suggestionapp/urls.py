from django.urls import path
from .views import TrainAndEvaluateView, SuggestBrandsView

urlpatterns = [
    path('train/', TrainAndEvaluateView.as_view(), name='Train and Evaluate'),
    path('suggest/', SuggestBrandsView.as_view(), name='Suggest Brands'),
]
