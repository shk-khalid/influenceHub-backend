import requests
from .models import BrandDemographics
from django.utils.timezone import now

API_URL = ""
API_KEY = ""

def fetch_brand_data(brand_name):
    response = requests.get(
        API_URL,
        params={"brand": brand_name, "api_key": API_KEY}
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API Error: {response.status_code}, {response.text}")
    
def save_brand_data(api_data):
    brand, created = BrandDemographics.objects.update_or_create(
        brand_id = api_data["id"],
        defaults={
            "brand_name": api_data["name"],
            "logo_url": api_data.get("logo"),
            "gender_distribution": api_data["demographics"]["gender"],
            "age_distribution": api_data["demographics"]["age"],
            "location_data": api_data["demographics"]["location"],
            "social_handles": api_data.get("social_media"),
            "last_updated": now(),
        }
    )
    return brand