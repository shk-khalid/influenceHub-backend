from rest_framework import serializers
from .models import Campaign

class CampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = Campaign
        fields = '__all__'
        read_only_fields = ('user',)

        def create(self, validated_data):
            user = self.context['request'].user
            return Campaign.objects.create(user=user, **validated_data)