import random 
from .models import Trend

def fetch_and_update_trends():
    
    api_data = [
        {"name": "#BoycottNetflix", "volume": random.randint(10000, 500000), "category": "Entertainment", "region": "India"},
        {"name": "#TechForFuture", "volume": random.randint(5000, 100000), "category": "Tech", "region": "Global"},
        {"name": "#HealthyLiving", "volume": random.randint(2000, 30000), "category": "Health", "region": "India"},
    ]
    
    for trend_data in api_data:
        trend, created = Trend.objects.get_or_create(
            name=trend_data['name'],
            defaults={
                'volume': trend_data['volume'],
                'category': trend_data['category'],
                'region': trend_data['region'],
            }
        )
        
        if created:
            trend.growth = random.randint(1, 10)
            trend.save()