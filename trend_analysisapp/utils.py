import praw
import os
from dotenv import load_dotenv 
from .models import Trend
from datetime import datetime

load_dotenv()

REDDIT_CLIENT_ID = os.getenv('REDDIT_CLIENT_ID')
REDDIT_CLIENT_SECRET = os.getenv('REDDIT_CLIENT_SECRET')
REDDIT_USER_AGENT =os.getenv('REDDIT_USER_AGENT')

CATEGORY_SUBREDDITS = {
    'tech': 'technology',
    'food': 'food',
    'fashion': 'fashion',
    'entertainment': 'movies',
    'sports': 'sports',
    'politics': 'politics',
}

def fetch_reddit_trends():
    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT,
    )
    
    trend = []
    for category, subreddit in CATEGORY_SUBREDDITS.items():
        subreddit_data = reddit.subreddit(subreddit)
        
        for post in subreddit_data.hot(limit=5):
            trend.append({
                'name': post.title,
                'category': category,
                'volume': post.score,
                'region': 'Global',
                'growth': 0.0,
            })
    return trend

def update_trends(trends):
    for trend_data in trends:
        existing_trend = Trend.objects.filter(name=trend_data['name'], category=trend_data['category']).first()
        
        if existing_trend:
            # Calculate growth if old volume exists
            old_volume = existing_trend.volume
            new_volume = trend_data['volume']
            growth = ((new_volume - old_volume) / old_volume) * 100 if old_volume else 0.0
            existing_trend.volume = new_volume
            existing_trend.growth = growth
            existing_trend.updated_at = datetime.now()
            existing_trend.save()
        else:
            # Create new trend
            Trend.objects.create(
                name=trend_data['name'],
                volume=trend_data['volume'],
                category=trend_data['category'],
                region=trend_data['region'],
                growth=trend_data['growth'],
            )
            
def fetch_and_update_trends():
    reddit_trends = fetch_reddit_trends()
    update_trends(reddit_trends)