from rest_framework import serializers
from .models import Brand, PerformanceMetric, Competitor, GenderDemographic, ValuationHistory, BrandSentiment


class CompetitorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Competitor
        fields = ['competitor_name']


class ValuationHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ValuationHistory
        fields = ['year', 'valuation']


class GenderDemographicSerializer(serializers.ModelSerializer):
    class Meta:
        model = GenderDemographic
        fields = ['male_percentage', 'female_percentage']

class PerformanceMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = PerformanceMetric
        fields = ['market_share', 'growth_rate']


class BrandSentimentSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrandSentiment
        fields = ['comments', 'key_mentions']


class BrandListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ['id', 'name', 'sector', 'location', 'overall_rating', 'market_share', 'growth_percentage']


class BrandDetailSerializer(serializers.ModelSerializer):
    performance_metrics = PerformanceMetricSerializer(read_only=True)
    competitors = CompetitorSerializer(many=True, read_only=True)
    gender_demographics = GenderDemographicSerializer(read_only=True)
    valuation_history = ValuationHistorySerializer(many=True, read_only=True)
    sentiment = BrandSentimentSerializer(read_only=True)

    class Meta:
        model = Brand
        fields = [
            'id', 'name', 'sector', 'location', 'overall_rating', 'market_share', 'growth_percentage',
            'recent_valuation', 'performance_metrics', 'competitors', 'gender_demographics', 
            'valuation_history', 'sentiment'
        ]
