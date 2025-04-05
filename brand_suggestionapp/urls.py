from django.urls import path
from .views import SuggestBrandsView, RespondBrandSuggestionView, SuggestionHistoryView

urlpatterns = [
    path('', SuggestBrandsView.as_view(), name='Suggest Brands'),
    path('<int:brand_id>/respond/', RespondBrandSuggestionView.as_view(), name='Record Decision'),
    path('history/', SuggestionHistoryView.as_view(), name="Suggestion History"),
]
