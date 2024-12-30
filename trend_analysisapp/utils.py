import asyncpraw
import os
import asyncio
from textblob import TextBlob
from dotenv import load_dotenv
from .models import Trend
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

load_dotenv()

REDDIT_CLIENT_ID = os.getenv('REDDIT_CLIENT_ID')
REDDIT_CLIENT_SECRET = os.getenv('REDDIT_CLIENT_SECRET')
REDDIT_USER_AGENT = os.getenv('REDDIT_USER_AGENT')

CATEGORY_SUBREDDITS = {
    'technology': 'technology',
    'fashion': 'fashion',
    'fitness': 'fitness',
    'travel': 'travel',
    'food': 'food',
    'gaming': 'gaming',
}

def create_reddit_instance():
    return asyncpraw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT,
    )
    
async def fetch_subreddit_trend(reddit, category, subreddit_name):
    subreddit_data = reddit.subreddit(subreddit_name)
    trends = []
    for post in subreddit_data.hot(limit=5):
        trends.append({
            'name': post.title,
            'category': category,
            'volume': post.score,
            'region': 'Global',
            'growth': 0.0
        })
    return trends

async def fetch_reddit_trend():
    reddit = create_reddit_instance()
    tasks = []
    
    for category, subreddit_name in CATEGORY_SUBREDDITS.items():
        tasks.append(fetch_subreddit_trend(reddit, category, subreddit_name))
        
    all_trends = await asyncio.gather(*tasks)
    return [trend for trends in all_trends for trend in trends]

def calculate_sentiment(text):
    # Calculate the sentiment score for a given text
    blob = TextBlob(text)
    sentiment = blob.sentiment.polarity  # Polarity ranges from -1 to 1
    return sentiment


def update_trends(trends):
    with ThreadPoolExecutor() as executor:
        for trends_data in trends:
            executor.submit(update_or_create_trend, trends_data)
            
def update_or_create_trend(trend_data):   
    # Get the sentiment score for the trend
    sentiment_score = calculate_sentiment(trend_data['name'])
    
    # Check if the trend already exists in the database
    existing_trend = Trend.objects.filter(name=trend_data['name'], category=trend_data['category']).first()

    if existing_trend:
        # If it exists, update the trend's volume, growth, and sentiment
        old_volume = existing_trend.volume
        new_volume = trend_data['volume']
        growth = ((new_volume - old_volume) / old_volume) * 100 if old_volume else 0.0

        existing_trend.volume = new_volume
        existing_trend.growth = growth
        existing_trend.sentiment = sentiment_score
        existing_trend.last_updated = datetime.now()
        existing_trend.save()
    else:
        # If the trend does not exist, create a new entry
        Trend.objects.create(
            name=trend_data['name'],
            volume=trend_data['volume'],
            category=trend_data['category'],
            region=trend_data['region'],
            growth=trend_data['growth'],
            sentiment=sentiment_score,
        )


def fetch_and_update_trends():
    # Fetch Reddit trends and update the database with new or existing trends
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    reddit_trends = loop.run_until_complete(fetch_reddit_trend())
    update_trends(reddit_trends)
