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
            "category": user.get("category_name", "N/A"),
            "hashtags": [entity["hashtag"]["name"] for entity in user.get("biography_with_entities", {}).get("entities", [])
                         if entity.get("hashtag")] if user.get("biography_with_entities") else [],
            "followers": user.get("edge_followed_by", {}).get("count", 0),
            "following": user.get("edge_follow", {}).get("count", 0),
            "posts": user.get("edge_owner_to_timeline_media", {}).get("count", 0),
            "user_id": user.get("id", "N/A"),
            "verified": user.get("is_verified", False),
            "professionalAccount": user.get("is_professional_account", False)
        }
    except Exception as e:
        print(f"Exception in extract_relevant_data: {str(e)}")
        return None

def fetch_instagram_user_media(user_id: int, api_key: str, followers: int):
    try:
        if not user_id:
            return []
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
                "mediaType": media.get("media_type", 1),  # Keep as number
                "likeCount": media.get("like_count", 0),
                "commentCount": media.get("comment_count", 0),
                "commentText": comment_text,
                "viewCount": media.get("play_count", 0),
                "location": media.get("location", None),  # Extract location if available
                "userTags": [ tag.get("user", {}).get("username", "") 
                              for tag in media.get("usertags", {}).get("in", []) ]
            }
            media_details_list.append(detail)
    
        return media_details_list
    except Exception as e:
        print(f"Exception in fetch_instagram_user_media for user_id {user_id}: {str(e)}")
        return []

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
            "category": relevant_data["category"],
            "hashtag": relevant_data["hashtags"],
            "followers": relevant_data["followers"],
            "following": relevant_data["following"],
            "posts_count": relevant_data["posts"],
            "is_verified": relevant_data["verified"],
            "is_professionalAccount": relevant_data["professionalAccount"],
            "media_details": []  # This will hold the list of media items
        }
    
        if relevant_data["user_id"] != "N/A":
            media_results = fetch_instagram_user_media(int(relevant_data["user_id"]), API_KEY, relevant_data["followers"])
            if media_results:
                results["media_details"] = media_results
        return index, results
    except Exception as e:
        print(f"Error processing user at index {index}: {str(e)}")
        return index, None

def update_csv(input_file: str, output_file: str, API_KEY: str):
    try:
        # Load the existing CSV file
        df = pd.read_csv(input_file)
        # Rename 'influencerInstaID' to 'insta_id'
        df.rename(columns={"influencerInstaID": "insta_id"}, inplace=True)
        df["insta_id"] = df["insta_id"].str.replace(r"^@", "", regex=True).str.strip()
    
        # Define columns for basic user info
        basic_columns = {
            "username": "",
            "bio": "",
            "category": "",
            "hashtag": "",
            "is_verified": "",
            "is_professionalAccount": "",
            "followers": 0,
            "following": 0,
            "posts_count": 0,
        }
    
        for col, default in basic_columns.items():
            if col not in df.columns:
                df[col] = default
    
        # Add columns for post details (post1 to post12)
        for i in range(1, 13):
            col_name = f"post{i}"
            if col_name not in df.columns:
                df[col_name] = ""
    
        # Process users concurrently using ThreadPoolExecutor
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            future_to_index = {executor.submit(process_user, index, row, API_KEY): index 
                               for index, row in df.iterrows()}
            for future in concurrent.futures.as_completed(future_to_index):
                try:
                    index, result = future.result()
                    if result:
                        for key, value in result.items():
                            if key != "media_details":
                                df.at[index, key] = value
                        posts = result.get("media_details", [])
                        for i in range(12):
                            col_name = f"post{i+1}"
                            if i < len(posts):
                                df.at[index, col_name] = json.dumps(posts[i])
                            else:
                                df.at[index, col_name] = ""
                except Exception as e:
                    idx = future_to_index.get(future, "Unknown")
                    print(f"Error in future for index {idx}: {str(e)}")
    
        # Write the updated dataframe to a new CSV file
        df.to_csv(output_file, index=False)
        print(f"Updated data saved to {output_file}")
    except Exception as e:
        print(f"Exception in update_csv: {str(e)}")

if __name__ == "__main__":
    API_KEY = os.getenv("ROCKETAPI_INSTA", "your_api_key_here")
    
    # Set input and output CSV file paths
    input_file = r"C:\project\influenceHub\influencerDataRef.csv"
    output_file = r"C:\project\influenceHub\influencerDataRef.csv"
    
    update_csv(input_file, output_file, API_KEY)
