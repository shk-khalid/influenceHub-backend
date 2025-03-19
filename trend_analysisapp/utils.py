import asyncpraw
import os
import asyncio
from datetime import datetime, timedelta, timezone as dt_timezone
from textblob import TextBlob
from dotenv import load_dotenv
from asyncprawcore.exceptions import RequestException

from django.utils import timezone
from .models import Trend

load_dotenv()

REDDIT_CLIENT_ID = os.getenv('REDDIT_CLIENT_ID')
REDDIT_CLIENT_SECRET = os.getenv('REDDIT_CLIENT_SECRET')
REDDIT_USER_AGENT = os.getenv('REDDIT_USER_AGENT')

# Each category now maps to a list of subreddits.
CATEGORY_SUBREDDITS = {
    'technology': ['technology', 'gadgets', 'programming'],
    'fashion': ['fashion', 'femalefashionadvice', 'malefashionadvice'],
    'fitness': ['fitness', 'bodyweightfitness', 'xxfitness'],
    'travel': ['travel', 'solotravel', 'travelblog'],
    'food': ['food', 'cooking', 'recipes'],
    'gaming': ['gaming', 'pcgaming', 'console'],
}

def create_reddit_instance():
    return asyncpraw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT,
    )

def calculate_growth_from_upvote_ratio(current_ratio, benchmark_ratio=0.90):
    return ((current_ratio - benchmark_ratio) / benchmark_ratio) * 100

async def fetch_subreddit_trend(reddit, category, subreddit_name):
    """
    Fetch trends from a subreddit.
    """
    subreddit_data = await reddit.subreddit(subreddit_name)
    trends = []
    async for post in subreddit_data.hot(limit=5):
        upvote_ratio = post.upvote_ratio
        growth = calculate_growth_from_upvote_ratio(upvote_ratio, benchmark_ratio=0.90)
        
        # Create a timezone-aware datetime using Python's built-in timezone (UTC).
        created_at_dt = datetime.fromtimestamp(post.created_utc, tz=dt_timezone.utc)
        # Calculate time since creation in minutes using Django's timezone.now() for current time.
        time_since_creation = (timezone.now() - created_at_dt).total_seconds() / 60
        
        title_sentiment = TextBlob(post.title).sentiment.polarity
        popularity = post.score / (time_since_creation + 1)
        
        # Check if the post is an image.
        image_url = post.url if hasattr(post, 'post_hint') and post.post_hint == 'image' else None
        
        trends.append({
            'name': post.title,
            'category': category,
            'volume': post.score,
            'region': 'Global',
            'growth': growth,
            'created_at': created_at_dt,
            'sentiment': title_sentiment,
            'num_comments': post.num_comments,
            'popularity': popularity,
            'subreddit': subreddit_name,
            'image_url': image_url,
        })
    return trends

async def safe_fetch_subreddit_trend(reddit, category, subreddit_name, retries=3, delay=2):
    """
    Retry wrapper for fetching subreddit trends.
    """
    for attempt in range(retries):
        try:
            return await fetch_subreddit_trend(reddit, category, subreddit_name)
        except RequestException as e:
            if attempt < retries - 1:
                await asyncio.sleep(delay)
                delay *= 2  # Exponential backoff
            else:
                raise e

async def fetch_reddit_trend():
    """
    Iterate through all subreddits in each category and aggregate the trends.
    """
    reddit = create_reddit_instance()
    try:
        tasks = []
        for category, subreddits in CATEGORY_SUBREDDITS.items():
            for subreddit_name in subreddits:
                tasks.append(safe_fetch_subreddit_trend(reddit, category, subreddit_name))
        all_trends = await asyncio.gather(*tasks)
        # Flatten the list of trends (each task returns a list of posts).
        return [trend for trends in all_trends for trend in trends]
    finally:
        await reddit.close()

def fetch_and_update_trends():
    """
    Fetch trends from Reddit and update or create Trend records in the database.
    """
    # Run the async function to fetch trends.
    trends_data = asyncio.run(fetch_reddit_trend())
    
    for trend in trends_data:
        # Update or create the Trend record, using 'name' as a unique identifier.
        Trend.objects.update_or_create(
            name=trend['name'],
            defaults={
                'volume': trend['volume'],
                'category': trend['category'],
                'region': trend['region'],
                'growth': trend['growth'],
                'sentiment': trend['sentiment'],
                'created_at': trend['created_at'],
                'popularity': trend['popularity'],
                'num_comments': trend['num_comments'],
                'image_url': trend['image_url'],
                'subreddit': trend['subreddit'],
            }
        )

def remove_outdated_trends():
    """
    Remove Trend records older than a certain threshold (e.g., 1 day).
    """
    threshold_date = timezone.now() - timedelta(days=1)
    outdated_trends = Trend.objects.filter(created_at__lt=threshold_date)
    deleted_count, _ = outdated_trends.delete()
    return deleted_count
