import http.client
import json
import time
import os
import pandas as pd
import concurrent.futures
import threading

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

def get_media_type(media_type):
    media_mapping = {1: "Photo", 2: "Video", 3: "Carousel"}
    return media_mapping.get(media_type, "Unknown")

def fetch_instagram_user_data(username: str, api_key: str):
    try:
        rate_limiter.wait()
        conn = http.client.HTTPSConnection("rocketapi-for-instagram.p.rapidapi.com")
        headers = {
            "x-rapidapi-key": api_key,
            "x-rapidapi-host": "rocketapi-for-instagram.p.rapidapi.com",
            "Content-Type": "application/json"
        }
        payload = json.dumps({"username": username})
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
            "hashtags": [entity["hashtag"]["name"] for entity in user.get("biography_with_entities", {}).get("entities", []) if entity.get("hashtag")] if user.get("biography_with_entities") else [],
            "followers": user.get("edge_followed_by", {}).get("count", 0),
            "following": user.get("edge_follow", {}).get("count", 0),
            "posts": user.get("edge_owner_to_timeline_media", {}).get("count", 0),
            "user_id": user.get("id", "N/A"),
            "verified": user.get("is_verified", False)
        }
    except Exception as e:
        print(f"Exception in extract_relevant_data: {str(e)}")
        return None

def fetch_instagram_user_media(user_id: int, api_key: str, followers: int):
    try:
        if not user_id:
            return None, 0, 0, 0, None, 0, 0, 0

        rate_limiter.wait()
        conn = http.client.HTTPSConnection("rocketapi-for-instagram.p.rapidapi.com")
        headers = {
            "x-rapidapi-key": api_key,
            "x-rapidapi-host": "rocketapi-for-instagram.p.rapidapi.com",
            "Content-Type": "application/json"
        }
        payload = json.dumps({"id": user_id, "count": 50})
        conn.request("POST", "/instagram/user/get_media", body=payload, headers=headers)
        response = conn.getresponse()
        response_data = response.read().decode("utf-8")
    
        try:
            json_data = json.loads(response_data)
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON response for user_id {user_id}: {response_data}")
            return None
    
        if response.status != 200:
            print(f"Error {response.status} for user_id {user_id}: {json_data}")
            return None

        media_data = json_data.get("response", {}).get("body", {}).get("items", [])
    
        highest_post = None
        highest_likes = 0
        highest_comments = 0

        total_likes = 0
        total_comments = 0
        total_views = 0
        video_posts = 0
        total_posts = len(media_data)
    
        engagement_rate = 0 
        estimated_reach = 0
        estimated_impressions = 0
    
        total_collaborated = 0
        collaborated_engagement = 0
        total_non_collaborated = 0
        non_collaborated_engagement = 0
    
        for media in media_data:
            media_type = get_media_type(media.get("media_type", 1))
            like_count = media.get("like_count", 0)
            comment_count = media.get("comment_count", 0)
            play_count = media.get("play_count", 0)  # For videos
            caption = media.get("caption", "N/A")
            tags = media.get("usertags", [])
            is_collaborated = media.get("is_collaborated", False)
        
            estimated_reach = (like_count * 1.5) + (comment_count * 2.5) + (play_count * 0.75)
            estimated_impressions = play_count if play_count > 0 else estimated_reach * 1.8 + (like_count * 1.2)
            engagement_rate = round(((like_count + comment_count) / max(1, followers)) * 100, 4)

            if like_count > highest_likes and comment_count > highest_comments:
                highest_likes = like_count
                highest_comments = comment_count
                highest_post = {
                    "post_url": f"https://www.instagram.com/p/{media.get('code', '')}/",
                    "like_count": like_count,
                    "comment_count": comment_count,
                    "media_type": media_type,
                    "caption": caption,
                    "tags": ", ".join(tags) if tags else "None"
                }
            
            total_likes += like_count
            total_comments += comment_count
            if media_type == "Video":
                total_views += play_count
                video_posts += 1
            
            if is_collaborated:
                total_collaborated += 1
                collaborated_engagement += engagement_rate
            else:
                total_non_collaborated += 1
                non_collaborated_engagement += engagement_rate

        avg_likes = round(total_likes / max(1, total_posts), 2)
        avg_comments = round(total_comments / max(1, total_posts), 2)
        avg_views = round(total_views / max(1, video_posts), 2) if video_posts > 0 else 0

        avg_collaborated_engagement = round(collaborated_engagement / max(1, total_collaborated), 4)
        avg_non_collaborated_engagement = round(non_collaborated_engagement / max(1, total_non_collaborated), 4) if total_non_collaborated > 0 else None

        if avg_non_collaborated_engagement is not None:
            success_ratio = round(avg_collaborated_engagement / max(0.0001, avg_non_collaborated_engagement), 4)
        else:
            success_ratio = None

        return highest_post, avg_likes, avg_comments, avg_views, success_ratio, engagement_rate, estimated_reach, estimated_impressions
    except Exception as e:
        print(f"Exception in fetch_instagram_user_media for user_id {user_id}: {str(e)}")
        return None

def process_user(index, row, API_KEY):
    try:
        username = row["insta_id"]
        if pd.isna(username) or username == "":
            return index, None
        print(f"Fetching data for: {username}")
    
        user_data = fetch_instagram_user_data(username, API_KEY)
        if not user_data:
            return index, None
    
        relevant_data = extract_relevant_data(user_data)
        if not relevant_data:
            return index, None
    
        results = {
            "username": relevant_data["username"],
            "bio": relevant_data["bio"],
            "hashtag": relevant_data["hashtags"],
            "followers": relevant_data["followers"],
            "following": relevant_data["following"],
            "posts_count": relevant_data["posts"],
            "is_verified": relevant_data["verified"],
            "highest_post_url": "",
            "highest_post_likes": 0,
            "highest_post_comments": 0,
            "highest_post_media_type": "",
            "highest_post_caption": "",
            "highest_post_tags": "",
            "avg_likes": 0.0,
            "avg_comments": 0.0,
            "avg_views": 0.0,
            "success_ratio": 0.0,
            "engagement_rate": 0.0,
            "estimated_reach": 0.0,
            "estimated_impression": 0.0
        }
    
        if relevant_data["user_id"] != "N/A":
            media_results = fetch_instagram_user_media(int(relevant_data["user_id"]), API_KEY, relevant_data["followers"])
            if media_results:
                (highest_post, avg_likes, avg_comments, avg_views, success_ratio,
                 engagement_rate, estimated_reach, estimated_impressions) = media_results
                if highest_post:
                    results["highest_post_url"] = highest_post["post_url"]
                    results["highest_post_likes"] = highest_post["like_count"]
                    results["highest_post_comments"] = highest_post["comment_count"]
                    results["highest_post_media_type"] = highest_post["media_type"]
                    results["highest_post_caption"] = highest_post["caption"]
                    results["highest_post_tags"] = highest_post["tags"]
                results["avg_likes"] = avg_likes
                results["avg_comments"] = avg_comments
                results["avg_views"] = avg_views
                results["success_ratio"] = success_ratio
                results["engagement_rate"] = engagement_rate
                results["estimated_reach"] = estimated_reach
                results["estimated_impression"] = estimated_impressions
        return index, results
    except Exception as e:
        print(f"Error processing user at index {index}: {str(e)}")
        return index, None

def update_excel(file_path, API_KEY):
    try:
        # Load the existing CSV file
        df = pd.read_csv(file_path)
        df.rename(columns={"Social media handle (INSTA)": "insta_id"}, inplace=True)
        df["insta_id"] = df["insta_id"].str.replace(r"^@", "", regex=True).str.strip()
    
        # Add new columns with default values
        columns_to_add = {
            "username": "",
            "bio": "",
            "hashtag": "",
            "is_verified": "",
            "followers": 0,
            "following": 0,
            "posts_count": 0,
            "engagement_rate": 0.0,
            "estimated_reach": 0.0,
            "estimated_impression": 0.0,
            "highest_post_url": "",
            "highest_post_likes": 0,
            "highest_post_comments": 0,
            "highest_post_media_type": "",
            "highest_post_caption": "",
            "highest_post_tags": "",
            "avg_likes": 0.0,
            "avg_comments": 0.0,
            "avg_views": 0.0,
            "success_ratio": 0.0
        }
        for col, default in columns_to_add.items():
            df[col] = default
    
        # Use ThreadPoolExecutor to process users concurrently.
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            future_to_index = {executor.submit(process_user, index, row, API_KEY): index for index, row in df.iterrows()}
            for future in concurrent.futures.as_completed(future_to_index):
                try:
                    index, result = future.result()
                    if result:
                        for key, value in result.items():
                            df.at[index, key] = value
                except Exception as e:
                    idx = future_to_index.get(future, "Unknown")
                    print(f"Error in future for index {idx}: {str(e)}")
    
        df.to_csv(file_path, index=False)
        print(f"Updated data saved to {file_path}")
    except Exception as e:
        print(f"Exception in update_excel: {str(e)}")

if __name__ == "__main__":
    API_KEY = os.getenv("ROCKETAPI_INSTA")
    file_path = r"C:\project\influenceHub\BrandData.csv"   
    update_excel(file_path, API_KEY)
