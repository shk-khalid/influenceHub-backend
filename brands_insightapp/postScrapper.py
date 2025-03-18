import http.client
import json
import time
import os
import pandas as pd
import concurrent.futures
import threading
from dotenv import load_dotenv

load_dotenv()

# A simple thread-safe rate limiter
class RateLimiter:
    def __init__(self, rate, per):
        self.rate = rate      # e.g. 8 requests
        self.per = per        # per this many seconds (e.g. 1 second)
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

GET_INFO_URL = "/instagram/user/get_info"
GET_MEDIA_URL = "/instagram/user/get_media"
API_HOST = "rocketapi-for-instagram.p.rapidapi.com"
HEADERS = {
    "x-rapidapi-key": "",  # set dynamically
    "x-rapidapi-host": API_HOST,
    "Content-Type": "application/json"
}

def fetch_user_id(username: str, api_key: str):
    """Fetches the user ID using the get_info endpoint with robust response validation."""
    try:
        rate_limiter.wait()
        conn = http.client.HTTPSConnection(API_HOST)
        HEADERS["x-rapidapi-key"] = api_key
        payload = json.dumps({"username": username})
        conn.request("POST", GET_INFO_URL, body=payload, headers=HEADERS)
        response = conn.getresponse()
        data = json.loads(response.read().decode("utf-8"))

        # Validate the API response
        if not data:
            print("Error: API response is empty or invalid")
            return None

        if "response" not in data or "body" not in data["response"]:
            print(f"Error: Unexpected response format - {json.dumps(data, indent=4)}")
            return None

        body = data["response"]["body"]

        if "data" not in body or "user" not in body["data"]:
            print(f"Error: 'user' key missing in API response - {json.dumps(body, indent=4)}")
            return None

        user = body["data"]["user"]

        # Return the user ID; if missing, default to "N/A"
        return user.get("id", "N/A")
    except Exception as e:
        print(f"Exception fetching user id for {username}: {e}")
        return None

def fetch_media_posts(user_id: int, api_key: str):
    """Fetches media posts using the get_media endpoint."""
    try:
        rate_limiter.wait()
        conn = http.client.HTTPSConnection(API_HOST)
        HEADERS["x-rapidapi-key"] = api_key
        # Cast user_id to int to satisfy API requirements
        payload = json.dumps({"id": int(user_id), "count": 50})
        conn.request("POST", GET_MEDIA_URL, body=payload, headers=HEADERS)
        response = conn.getresponse()
        data = json.loads(response.read().decode("utf-8"))
        if response.status != 200:
            print(f"Error {response.status} for user_id {user_id}: {data}")
            return []
        media_items = data.get("response", {}).get("body", {}).get("items", [])
        # If items is a dict with numeric keys, sort and convert to list.
        if isinstance(media_items, dict):
            sorted_items = sorted(media_items.items(), key=lambda x: int(x[0]))
            posts = [item for _, item in sorted_items]
        elif isinstance(media_items, list):
            posts = media_items
        else:
            posts = []
        return posts
    except Exception as e:
        print(f"Exception fetching media posts for user_id {user_id}: {e}")
        return []

def process_posts(posts):
    """Extracts the required fields from up to 20 posts."""
    processed = []
    for post in posts[:20]:
        media_type = post.get("media_type", 1)
        like_count = post.get("like_count", 0)
        comment_count = post.get("comment_count", 0)
        caption = post.get("caption", "")
        # isCollaborated: True if usertags exist and non-empty
        is_collaborated = bool(post.get("usertags"))
        post_obj = {
            "mediaType": media_type,
            "likeCount": like_count,
            "commentCount": comment_count,
            "caption": caption,
            "isCollaborated": is_collaborated
        }
        if media_type == 2:  # if video, include viewCount
            post_obj["viewCount"] = post.get("play_count", 0)
        processed.append(post_obj)
    return processed

def process_user(index, row, api_key):
    """
    For a given user record, fetch the user id and media posts,
    then extract only the needed post-level data.
    Returns a dictionary with keys "post1" ... "post20".
    """
    try:
        username = row["insta_id"]
        if pd.isna(username) or username.strip() == "":
            return index, None
        print(f"Processing {username}...")
        user_id = fetch_user_id(username, api_key)
        if not user_id:
            print(f"User ID not found for {username}")
            return index, None
        posts = fetch_media_posts(user_id, api_key)
        processed_posts = process_posts(posts)
        posts_dict = {}
        for i in range(20):
            if i < len(processed_posts):
                posts_dict[f"post{i+1}"] = json.dumps(processed_posts[i])
            else:
                posts_dict[f"post{i+1}"] = ""
        print(f"Fetched {len(processed_posts)} posts for {username}")
        return index, posts_dict
    except Exception as e:
        print(f"Error processing {username}: {e}")
        return index, None

def update_csv(input_file_path, output_file_path, api_key):
    try:
        df = pd.read_csv(input_file_path)
        # The column is already named 'insta_id'; just clean it.
        df["insta_id"] = df["insta_id"].str.replace(r"^@", "", regex=True).str.strip()
        # Add new columns for posts (post1 to post20)
        for i in range(1, 21):
            df[f"post{i}"] = ""
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            future_to_index = {executor.submit(process_user, index, row, api_key): index for index, row in df.iterrows()}
            for future in concurrent.futures.as_completed(future_to_index):
                index, posts_dict = future.result()
                if posts_dict:
                    for key, value in posts_dict.items():
                        df.at[index, key] = value
        df.to_csv(output_file_path, index=False)
        print(f"CSV updated and saved to {output_file_path}")
    except Exception as e:
        print(f"Error updating CSV: {e}")

if __name__ == "__main__":
    API_KEY = os.getenv("ROCKETAPI_INSTA")
    if not API_KEY:
        print("API key not set in environment variable 'ROCKETAPI_INSTA'")
    else:
        input_file_path = r"C:\project\influenceHub\BrandData.csv"
        output_file_path = r"C:\project\influenceHub\BrandData_with_Posts.csv"
        update_csv(input_file_path, output_file_path, API_KEY)
