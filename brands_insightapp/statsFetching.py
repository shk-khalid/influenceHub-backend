import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# Load Instagram profile stats
def get_instagram_stats(instagram_id):
    if "@" in instagram_id:
        instagram_id = instagram_id.replace("@", "")
        
    url = f"https://www.instagram.com/{instagram_id}/"
    
    # Setup Selenium WebDriver
    options = Options()
    options.add_argument("--headless")  # Run in headless mode
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(url)
    time.sleep(8)  # Wait for page to load

    try:
        stats = driver.find_elements(By.CSS_SELECTOR, "meta[property='og:description']")[0].get_attribute("content")
        stats_parts = stats.split(" ")
        
        followers = stats_parts[0]  # Followers count
        following = stats_parts[2]  # Following count
        posts = stats_parts[4]      # Posts count
    except Exception as e:
        print(f"Error fetching data for {instagram_id}: {e}")
        followers, following, posts = "N/A", "N/A", "N/A"
    
    driver.quit()
    return followers, following, posts

# Load CSV file
file_path = r"C:\project\influenceHub\BrandData.csv"
df = pd.read_csv(file_path)

# Rename the column to a consistent name
df.rename(columns={"Social media handle (INSTA)": "Instagram_ID"}, inplace=True)

# Check if 'Instagram_ID' column exists
if "Instagram_ID" in df.columns:
    df["Followers"] = ""
    df["Following"] = ""
    df["Posts"] = ""

    for index, row in df.iterrows():
        insta_id = row["Instagram_ID"]
        if pd.notna(insta_id):  # Ensure ID is not empty
            followers, following, posts = get_instagram_stats(insta_id)
            df.at[index, "Followers"] = followers
            df.at[index, "Following"] = following
            df.at[index, "Posts"] = posts
            print(f"Fetched {insta_id}: {followers} Followers, {following} Following, {posts} Posts")

    # Save updated data
    output_file = r'C:\project\influenceHub\Updated_BrandData.xlsx'
    df.to_excel(output_file, index=False)
    print(f"Updated file saved at {output_file}")

else:
    print("Instagram_ID column not found in CSV.")
