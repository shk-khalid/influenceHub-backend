from rest_framework import serializers
from .models import Brand, PerformanceMetric, Competitor, GenderDemographic, ValuationHistory, BrandPost, BrandsSocialStats


class CompetitorSerializer(serializers.ModelSerializer):
    competitor_id = serializers.UUIDField(source="competitor.id", read_only=True)
    competitor_name = serializers.CharField(source="competitor.name", read_only=True)

    class Meta:
        model = Competitor
        fields = ['competitor_id', 'competitor_name']


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

class BrandListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ['id', 'name', 'sector', 'location', 'overall_rating', 'market_share', 'growth_percentage']

class BrandPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrandPost
        fields = ['post_number', 'post_detail']

class BrandsSocialStatsSerializer(serializers.ModelSerializer):
    # Nesting the posts serializer to include social posts details
    brand_posts = BrandPostSerializer(many=True, read_only=True)
    
    class Meta:
        model = BrandsSocialStats
        fields = [
            'brand', 'username', 'bio', 'is_verified', 'followers', 'followings', 
            'post_count', 'follower_ratio', 'engagement_score',
            'engagement_per_follower', 'estimated_reach', 'estimated_impression', 
            'reach_ratio', 'avg_likes_computed', 'avg_comments_computed', 
            'avg_views','brand_posts', 'highest_post'
        ]

class BrandDetailSerializer(serializers.ModelSerializer):
    performance_metrics = PerformanceMetricSerializer(read_only=True)
    competitors = CompetitorSerializer(many=True, source="competitor_for", read_only=True)
    gender_demographics = GenderDemographicSerializer(read_only=True)
    valuation_history = ValuationHistorySerializer(many=True, read_only=True)
    social_stats = BrandsSocialStatsSerializer(read_only=True)

    class Meta:
        model = Brand
        fields = [
            'id', 'name', 'sector', 'location', 'overall_rating', 'market_share', 
            'growth_percentage', 'recent_valuation', 'performance_metrics', 
            'competitors', 'gender_demographics', 'valuation_history', 'social_stats'
        ]
