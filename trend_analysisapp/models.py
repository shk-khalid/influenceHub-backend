from django.db import models

class Trend(models.Model):
    CATEGORY_CHOICES = [
        ('tech', 'Tech'),
        ('food', 'Food'),
        ('fashion', 'Fashion'),
        ('entertainment', 'Entertainment'),
        ('sports', 'Sports'),
        ('politics', 'Politics'),
    ]
    
    REGION_CHOICES = [
        ('global', 'Global'),
        ('india', 'India'),
    ]
    
    SENTIMENT_CHOICES = [
        ('positive', 'Positive'),
        ('negative', 'Negative'),
        ('neutral', 'Neutral'),
    ]
    
    name = models.CharField(max_length=255, unique=True)
    volume = models.PositiveIntegerField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    region = models.CharField(max_length=50, choices=REGION_CHOICES)
    growth = models.FloatField(default=0.0)
    sentiment = models.CharField(max_length=50, choices=SENTIMENT_CHOICES, default='neutral')
    comments = models.JSONField(default=list, blank=True, null=True)
    last_updated = models.DateTimeField(auto_now=True)
        
    def __str__(self):
        return f"{self.name} ({self.region})"
    
    