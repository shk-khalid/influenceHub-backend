from django.db import models 
from django.utils.timezone import now

class BrandDemographics(models.Model):
    brand_id = models.CharField(max_length=255, primary_key=True)
    brand_name = models.CharField(max_length=255)
    logo_url = models.URLField(null=True, blank=True)
    gender_distribution = models.JSONField(null=True, blank=True)
    age_distribution = models.JSONField(null=True, blank=True)
    location_data =  models.JSONField(null=True, blank=True)
    social_handles =  models.JSONField(null=True, blank=True)
    last_updated =  models.DateTimeField(default=now)
    
    def __str__(self):
        return self.brand_name
    