import asyncio
import asyncpraw
import os
from dotenv import load_dotenv

load_dotenv()

REDDIT_CLIENT_ID = os.getenv('REDDIT_CLIENT_ID')
REDDIT_CLIENT_SECRET = os.getenv('REDDIT_CLIENT_SECRET')
REDDIT_USER_AGENT = os.getenv('REDDIT_USER_AGENT')

async def test_fetch_comments():
    reddit = asyncpraw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT,
    )
    
    # Choose a subreddit known for active discussion; you can change this as needed.
    subreddit = await reddit.subreddit("test")
    
    async for post in subreddit.hot(limit=1):
        print("Post Title:", post.title)
        try:
            # Attempt to load all comments (replace MoreComments objects)
            await post.comments.replace_more(limit=0)
            comments = post.comments.list()
            
            print("Fetched Comments:")
            for comment in comments:
                # Only print comments that have a valid body
                if hasattr(comment, 'body') and comment.body:
                    print(f"Score: {comment.score}, Comment: {comment.body}")
        except Exception as ex:
            print("Error fetching comments:", ex)
        break  # Only process the first post

    await reddit.close()

if __name__ == "__main__":
    asyncio.run(test_fetch_comments())
