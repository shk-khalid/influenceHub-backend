from django.db import models
from django.conf import settings

class Campaign(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('under_review', 'Under Review'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High')
    ]

    PLATFORM_CHOICES = [
        ('instagram', 'Instagram'),
        ('youtube', 'Youtube'),
        ('facebook', 'Facebook'),
        ('discord', 'Discord'),
        ('twitter', 'Twitter')
    ]

    user = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.CASCADE,
    related_name="campaigns",
    )    
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    budget = models.DecimalField(max_digits=10, decimal_places=2)
    startDate = models.DateField()
    endDate = models.DateField()
    priority = models.CharField(max_length=15, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, default='instagram')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.title
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ('user', 'title')

class HistoricalCampaign(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="historical_campaigns"
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    budget = models.DecimalField(max_digits=10, decimal_places=2)
    startDate = models.DateField()
    endDate = models.DateField()
    priority = models.CharField(max_length=15)
    status = models.CharField(max_length=20)
    platform = models.CharField(max_length=20)
    created_at = models.DateTimeField()
    archived_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Historical: {self.title}"
    