from rest_framework import serializers
from authapp.models import BrandSuggestion
from brands_insightapp.serializers import BrandDetailSerializer

class SuggestionHistorySerializer(serializers.ModelSerializer):
    brand = BrandDetailSerializer(read_only=True)

    class Meta:
        model = BrandSuggestion
        fields = [
            'brand',
            'status',
            'suggested_at',
        ]