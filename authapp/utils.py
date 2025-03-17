import os
import re
import http.client
import json
import time
import threading
from dotenv import load_dotenv
from .models import InstaStats, InstaPost
from urllib.parse import urlparse

load_dotenv()

# Rate limiter as provided
class RateLimiter:
    def __init__(self, rate, per):
        self.rate = rate
        self.per = per
        self.allowance = rate
        self.last_check = time.time()
        self.lock = threading.Lock()

    def wait(self):
        with self.lock:
            current = time.time()
            time_passed = current - self.last_check
            self.last_check = current
            self.allowance += time_passed * (self.rate / self.per)
            if self.allowance > self.rate:
                self.allowance = self.rate
            if self.allowance < 1.0:
                sleep_time = (1.0 - self.allowance) * (self.per / self.rate)
                time.sleep(sleep_time)
                self.allowance = 0
            else:
                self.allowance -= 1.0

# Global rate limiter: 8 requests per second
rate_limiter = RateLimiter(rate=8, per=1)

def extract_instagram_username(insta_url: str) -> str:
    try: 
        parsed_url = urlparse(insta_url)
        path = parsed_url.path.strip("/")
        match = re.match(r'^([\w\.]+)', path)
        if match:
            return match.group(1)
    except Exception as e:
        print(f"Error extracting instagram username: {str(e)}")
    return None

def fetch_instagram_user_data(username: str, api_key: str):
    """
    Fetch Instagram user information using the new API endpoint.
    Endpoint: https://rocketapi-for-developers.p.rapidapi.com/instagram/user/get_info
    """
    try:
        rate_limiter.wait()
        conn = http.client.HTTPSConnection("rocketapi-for-developers.p.rapidapi.com")
        headers = {
            "x-rapidapi-key": api_key,
            "x-rapidapi-host": "rocketapi-for-developers.p.rapidapi.com",
            "Content-Type": "application/json"
        }
        payload = json.dumps({"username": username})
        # Updated endpoint for user info
        conn.request("POST", "/instagram/user/get_info", body=payload, headers=headers)
        response = conn.getresponse()
        response_data = response.read().decode("utf-8")
        try:
            json_data = json.loads(response_data)
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON response for {username}: {response_data}")
            return None
        if response.status != 200:
            print(f"Error {response.status} for {username}: {json_data}")
            return None
        return json_data
    except Exception as e:
        print(f"Exception in fetch_instagram_user_data for {username}: {str(e)}")
        return None

def extract_relevant_data(user_data):
    try:
        if not user_data:
            print("Error: API response is empty or invalid")
            return None
        if "response" not in user_data or "body" not in user_data["response"]:
            print(f"Error: Unexpected response format - {json.dumps(user_data, indent=4)}")
            return None
        body = user_data["response"]["body"]
        if "data" not in body or "user" not in body["data"]:
            print(f"Error: 'user' key missing in API response - {json.dumps(body, indent=4)}")
            return None
        user = body["data"]["user"]
        return {
            "username": user.get("username", "N/A"),
            "bio": user.get("biography", "N/A"),
            "category": user.get("category_name", "N/A"),
            "hashtags": [entity["hashtag"]["name"] for entity in user.get("biography_with_entities", {}).get("entities", [])
                         if entity.get("hashtag")] if user.get("biography_with_entities") else [],
            "followers": user.get("edge_followed_by", {}).get("count", 0),
            "following": user.get("edge_follow", {}).get("count", 0),
            "posts_count": user.get("edge_owner_to_timeline_media", {}).get("count", 0),
            "user_id": user.get("id", "N/A"),
            "is_verified": user.get("is_verified", False),
            "is_professional": user.get("is_professional_account", False)
        }
    except Exception as e:
        print(f"Exception in extract_relevant_data: {str(e)}")
        return None

def fetch_instagram_user_media(user_id: int, api_key: str, followers: int):
    """
    Fetch Instagram user media using the new API endpoint.
    Endpoint: https://rocketapi-for-developers.p.rapidapi.com/instagram/user/get_media
    """
    try:
        if not user_id:
            return []
        rate_limiter.wait()
        conn = http.client.HTTPSConnection("rocketapi-for-developers.p.rapidapi.com")
        headers = {
            "x-rapidapi-key": api_key,
            "x-rapidapi-host": "rocketapi-for-developers.p.rapidapi.com",
            "Content-Type": "application/json"
        }
        # Updated payload: count set to 12 and max_id set to None as per sample
        payload = json.dumps({"id": user_id, "count": 12, "max_id": None})
        conn.request("POST", "/instagram/user/get_media", body=payload, headers=headers)
        response = conn.getresponse()
        response_data = response.read().decode("utf-8")
        try:
            json_data = json.loads(response_data)
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON response for user_id {user_id}: {response_data}")
            return []
        if response.status != 200:
            print(f"Error {response.status} for user_id {user_id}: {json_data}")
            return []
        media_data = json_data.get("response", {}).get("body", {}).get("items", [])
        media_details_list = []
        for media in media_data:
            caption = media.get("caption", None)
            if caption and isinstance(caption, dict):
                comment_text = caption.get("text", "N/A")
            elif isinstance(caption, str):
                comment_text = caption
            else:
                comment_text = "N/A"
            detail = {
                "mediaType": media.get("media_type", 1),
                "likeCount": media.get("like_count", 0),
                "commentCount": media.get("comment_count", 0),
                "commentText": comment_text,
                "viewCount": media.get("play_count", 0),
                "location": media.get("location", None),
                "userTags": [ tag.get("user", {}).get("username", "") 
                              for tag in media.get("usertags", {}).get("in", []) ]
            }
            media_details_list.append(detail)
        return media_details_list
    except Exception as e:
        print(f"Exception in fetch_instagram_user_media for user_id {user_id}: {str(e)}")
        return []

def update_insta_stats_for_username(insta_username: str):
    """
    Fetches Instagram stats for the provided username and updates the database.
    """
    api_key = os.getenv("ROCKETAPI_INSTA", "your_api_key_here")
    # Fetch user data
    user_data = fetch_instagram_user_data(insta_username, api_key)
    if not user_data:
        return {"error": "Unable to fetch data from Instagram API."}
    # Extract relevant info
    relevant_data = extract_relevant_data(user_data)
    if not relevant_data:
        return {"error": "Unable to extract relevant data from the API response."}
    # Fetch media details if user_id is valid
    if relevant_data.get("user_id") != "N/A":
        media_results = fetch_instagram_user_media(int(relevant_data["user_id"]), api_key, relevant_data["followers"])
        relevant_data["media_details"] = media_results if media_results else []
    else:
        relevant_data["media_details"] = []
    # Save or update the InstaStats record using the user_id as insta_id
    insta_id = str(relevant_data.get("user_id"))
    defaults = {
        "userName": relevant_data.get("username"),
        "bio": relevant_data.get("bio"),
        "category": relevant_data.get("category"),
        "is_verified": relevant_data.get("is_verified"),
        "is_professional": relevant_data.get("is_professional"),
        "followers": relevant_data.get("followers"),
        "following": relevant_data.get("following"),
        "posts_count": relevant_data.get("posts_count")
    }
    insta_stats, _ = InstaStats.objects.update_or_create(insta_id=insta_id, defaults=defaults)
    # Remove any existing posts for this InstaStats instance
    insta_stats.posts.all().delete()
    # Create up to 12 InstaPost records
    media_details = relevant_data.get("media_details", [])
    for i in range(1, 13):
        post_detail = media_details[i-1] if i-1 < len(media_details) else {}
        InstaPost.objects.create(
            insta_stats=insta_stats,
            post_number=i,
            post_detail=post_detail
        )
    return {"insta_stats": insta_stats, "media_count": len(media_details)}
