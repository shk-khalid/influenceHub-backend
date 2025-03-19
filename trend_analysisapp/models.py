from django.db import models
from django.utils.timezone import now

class Trend(models.Model):
    CATEGORY_CHOICES = [
        ('technology', 'Technology'),
        ('food', 'Food'),
        ('fashion', 'Fashion'),
        ('fitness', 'Fitness'),
        ('travel', 'Travel'),
        ('gaming', 'Gaming'),
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
    
    # New fields for additional insights:
    created_at = models.DateTimeField(default=now)  # Post creation time
    popularity = models.FloatField(default=0.0)  # Calculated popularity (score per time unit)
    num_comments = models.PositiveIntegerField(default=0)  # Total number of comments
    image_url = models.URLField(null=True, blank=True)  # URL of the image if available
    subreddit = models.CharField(max_length=50)  # The subreddit the post came from

    def __str__(self):
        return "{} ({})".format(self.name, self.region)
