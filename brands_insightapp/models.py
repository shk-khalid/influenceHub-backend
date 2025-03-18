import uuid
from django.db import models

# Sector Choices
SECTOR_CHOICES = [
    ('electronics', 'Electronics'),
    ('cosmetics', 'Cosmetics'),
    ('automobile', 'Automobile'),
    ('fashion', 'Fashion'),
]

class Brand(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    sector = models.CharField(choices=SECTOR_CHOICES, max_length=50)
    location = models.CharField(max_length=255)
    overall_rating = models.DecimalField(max_digits=3, decimal_places=2)
    market_share = models.DecimalField(max_digits=15, decimal_places=2)
    growth_percentage = models.DecimalField(max_digits=15, decimal_places=2)
    recent_valuation = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    instagram_handle = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.name


class PerformanceMetric(models.Model):
    brand = models.OneToOneField(Brand, related_name='performance_metrics', on_delete=models.CASCADE)
    market_share = models.DecimalField(max_digits=15, decimal_places=2)
    growth_rate = models.DecimalField(max_digits=15, decimal_places=2)

    def __str__(self):
        return f"Performance Metrics for {self.brand.name}"


class Competitor(models.Model):
    brand = models.ForeignKey(Brand, related_name='competitor_for', on_delete=models.CASCADE)
    competitor = models.ForeignKey(Brand, related_name='competitors', on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        unique_together = ('brand', 'competitor')  # Prevent duplicate competitor entries

    def __str__(self):
        return f"{self.brand.name} competes with {self.competitor.name}"


class GenderDemographic(models.Model):
    brand = models.OneToOneField(Brand, related_name='gender_demographics', on_delete=models.CASCADE)
    male_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    female_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    other_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"Gender Demographics for {self.brand.name}"


class ValuationHistory(models.Model):
    brand = models.ForeignKey(Brand, related_name='valuation_history', on_delete=models.CASCADE)
    year = models.IntegerField()
    valuation = models.DecimalField(max_digits=15, decimal_places=2)

    class Meta:
        unique_together = ('brand', 'year')

    def __str__(self):
        return f"Valuation for {self.brand.name} in {self.year}"


class BrandsSocialStats(models.Model):
    brand = models.OneToOneField(Brand, related_name="social_stats", on_delete=models.CASCADE)
    username = models.CharField(max_length=255)
    bio = models.TextField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    followers = models.PositiveIntegerField()
    followings = models.PositiveIntegerField()
    post_count = models.PositiveIntegerField()
    follower_ratio = models.DecimalField(max_digits=15, decimal_places=2)
    engagement_score = models.DecimalField(max_digits=15, decimal_places=2)
    engagement_per_follower = models.DecimalField(max_digits=15, decimal_places=2)
    estimated_reach = models.DecimalField(max_digits=15, decimal_places=2)
    estimated_impression = models.DecimalField(max_digits=15, decimal_places=2)
    reach_ratio = models.DecimalField(max_digits=15, decimal_places=2)
    avg_likes_computed = models.DecimalField(max_digits=10, decimal_places=2)
    avg_comments_computed = models.DecimalField(max_digits=10, decimal_places=2)
    avg_views = models.DecimalField(max_digits=10, decimal_places=2)
    highest_post = models.JSONField(blank=True, null=True)

    def __str__(self):
        return f"Social Stats for {self.brand.name}"
    

class BrandPost(models.Model):
    insta_stats = models.ForeignKey(BrandsSocialStats, on_delete=models.CASCADE, related_name="brand_posts")
    post_number = models.PositiveIntegerField()  # value from 1 to 12
    post_detail = models.JSONField()

    def __str__(self):
        return f"Post {self.post_number} of {self.insta_stats.username}"


def create_insta_posts(socialStats, posts_data):
    """
    Creates 12 posts for the provided BrandsSocialStats instance using data from posts_data.
    """
    for i in range(1, 13):
        post_detail = posts_data[i - 1] if i - 1 < len(posts_data) else {}
        BrandPost.objects.create(insta_stats=socialStats, post_number=i, post_detail=post_detail)