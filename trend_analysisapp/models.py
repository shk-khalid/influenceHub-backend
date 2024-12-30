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
    
    name = models.TextField(unique=True)
    volume = models.PositiveIntegerField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    region = models.CharField(max_length=50, choices=REGION_CHOICES)
    growth = models.FloatField(default=0.0)
    sentiment = models.FloatField(default=0.0)
    last_updated = models.DateTimeField(auto_now=True)
        
    def __str__(self):
        return "{} ({})".format(self.name, self.region)
