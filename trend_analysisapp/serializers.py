from rest_framework import serializers
from .models import Trend

class TrendSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trend
        fields = [
            'id', 'name', 'volume', 'category',
            'region', 'growth', 'sentiment',
            'created_at', 'popularity', 'num_comments',
            'image_url', 'subreddit',
        ]
