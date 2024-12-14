from django.http import JsonResponse
from .utils import fetch_brand_data, save_brand_data
from .models import BrandDemographics
from django.utils.timezone import now
from datetime import timedelta

def get_brand_demographics(request, brand_name):
    try:
        brand = BrandDemographics.objects.filter(brand_name__iexact=brand_name).first()
        if brand and brand.last_updated > now() - timedelta(days=7):
            return JsonResponse({
                "status": "success",
                "data": {
                    "brand_name": brand.brand_name,
                    "logo_url": brand.logo_url,
                    "gender_distribution": brand.gender_distribution,
                    "age_distribution": brand.age_distribution,
                    "location_data": brand.location_data,
                    "social_handles": brand.social_handles,
                }
            })
            
        api_data = fetch_brand_data(brand_name)
        brand = save_brand_data(api_data)
        return JsonResponse({
            "status": "success",
            "data": {
                "brand_name": brand.brand_name,
                "logo_url": brand.logo_url,
                "gender_distribution": brand.gender_distribution,
                "age_distribution": brand.age_distribution,
                "location_data": brand.location_data,
                "social_handles": brand.social_handles,
            }
        })
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})