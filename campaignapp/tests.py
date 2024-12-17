from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Campaign

class CampaignTestCase(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(email="test@example.com", password="password123")
        self.campaign = Campaign.objects.create(
            title="Test Campaign",
            brand=self.user,
            budget=1000,
            start_date="2024-12-20",
            end_date="2025-01-10",
            priority="High",
            status="pending"
        )

    def test_campaign_creation(self):
        self.assertEqual(self.campaign.title, "Test Campaign")
        self.assertEqual(self.campaign.status, "pending")

    def test_update_campaign_status(self):
        self.campaign.status = "completed"
        self.campaign.save()
        self.assertEqual(self.campaign.status, "completed")
