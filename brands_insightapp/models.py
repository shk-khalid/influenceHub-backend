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
    market_share = models.DecimalField(max_digits=5, decimal_places=2)
    growth_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    recent_valuation = models.DecimalField(max_digits=12, decimal_places=2, null=True)

    def __str__(self):
        return self.name


class PerformanceMetric(models.Model):
    brand = models.OneToOneField(Brand, related_name='performance_metrics', on_delete=models.CASCADE)
    market_share = models.DecimalField(max_digits=5, decimal_places=2)
    growth_rate = models.DecimalField(max_digits=5, decimal_places=2)

    def __str__(self):
        return "Performance Metrics for {}".format(self.brand.name)


class Competitor(models.Model):
    brand = models.ForeignKey(Brand, related_name='competitors', on_delete=models.CASCADE)
    competitor_name = models.CharField(max_length=255)
    sector = models.CharField(choices=SECTOR_CHOICES, max_length=50)
    market_share = models.DecimalField(max_digits=5, decimal_places=2)

    def __str__(self):
        return "Competitor: {}".format(self.competitor_name)


class GenderDemographic(models.Model):
    brand = models.OneToOneField(Brand, related_name='gender_demographics', on_delete=models.CASCADE)
    male_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    female_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    other_percentage = models.DecimalField(max_digits=5, decimal_places=2)

    def __str__(self):
        return "Gender Demographics for {self.brand.name}".format(self.brand.name)


class ValuationHistory(models.Model):
    brand = models.ForeignKey(Brand, related_name='valuation_history', on_delete=models.CASCADE)
    year = models.IntegerField()
    valuation = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        unique_together = ('brand', 'year')

    def __str__(self):
        return "Valuation for {self.brand.name} in {self.year}".format(self.brand.name, self.year)
    


class BrandSentiment(models.Model):
    brand = models.OneToOneField(Brand, related_name='sentiment', on_delete=models.CASCADE)
    comments = models.JSONField()
    key_mentions = models.TextField()

    def __str__(self):
        return "Sentiment for {}".format(self.brand.name)
