from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.core.mail import send_mail
from .models import Campaign
from .serializers import CampaignSerializer
from django.contrib.auth import get_user_model

User = get_user_model()
"""
class CreateCampaign(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        campaigns = Campaign.objects.filter(brand=request.user)
        serializer = CampaignSerializer(campaigns, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request):
        user = request.user
        if not user.is_authenticated:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        
        serializer = CampaignSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(brand=request.user)
            return Response(serializer.data, status.HTTP_201_CREATED)
        return Response(serializer.errors, status.HTTP_400_BAD_REQUEST)
"""
class CreateCampaign(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Fetch campaigns where the brand matches the logged-in user (original implementation)
        campaigns = Campaign.objects.filter(brand=request.user)
        
        # Uncomment the following lines to use hardcoded brand temporarily
        # campaigns = Campaign.objects.filter(brand="Placeholder Brand")
        
        serializer = CampaignSerializer(campaigns, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        user = request.user
        if not user.is_authenticated:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        
        # Hardcoding the brand temporarily for testing purposes
        brand_name = "Placeholder Brand"  # Hardcoded brand value
        
        # Comment out the original brand assignment and use the hardcoded brand for now
        # serializer = CampaignSerializer(data=request.data)
        data = request.data.copy()
        data["brand"] = brand_name  # Set the hardcoded brand
        
        serializer = CampaignSerializer(data=data)
        if serializer.is_valid():
            serializer.save(brand=brand_name)  # Save with hardcoded brand
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    
class UpdateCampaign(APIView):
    def put(self, request, pk):
        try:
            campaign = Campaign.objects.get(pk=pk)
        except Campaign.DoesNotExist:
            return Response({"error": "Campign not found."}, status=status.HTTP_404_NOT_FOUND) 
            
        serializer = CampaignSerializer(campaign, data=request.data, partial=False)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Campaign updated succesfully.", "data": serializer.data}, status=status.HTTP_200_OK)
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    
class UpdateCampaignStatus(APIView):
    def patch(self, request, pk):
        try:
            campaign = Campaign.objects.get(pk=pk)
        except Campaign.DoesNotExist:
            return Response({"error": "Campaign not Found."} , status=status.HTTP_404_NOT_FOUND)
        
        new_status = request.data.get('status')
        if not new_status:
            return Response({"error": "Status is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        valid_statuses = [choice[0] for choice in campaign.STATUS_CHOICES] 
        if new_status not in valid_statuses:
            return Response({"error": "Invalid status. Valid statuses are: {}.".format(', '.join(valid_statuses))}, status=status.HTTP_400_BAD_REQUEST)
        
        old_status = campaign.status
        campaign.status = new_status
        campaign.save()
        
        if old_status != new_status:
            self.send_status_update_email(request.user.email, campaign.title, new_status)
            
        return Response({"message": "Campaign status updated to {}.".format(new_status)}, status=status.HTTP_200_OK)
        
    def send_status_update_email(self, email, campaign_title, status):
        subject = "Campaign Status Update: {}".format(campaign_title)
        message = "The status of your campaign {} has been updated to {}.".format(campaign_title, status)
        send_mail(subject, message, 'noreply@campaignapp.com', [email])  