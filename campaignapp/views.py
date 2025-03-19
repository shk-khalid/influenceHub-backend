from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
from .models import Campaign, HistoricalCampaign
from .serializers import CampaignSerializer

class CreateCampaign(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Fetch only campaigns that belong to the logged-in user
        campaigns = Campaign.objects.filter(user=request.user)
        serializer = CampaignSerializer(campaigns, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        user = request.user
        serializer = CampaignSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(user=user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UpdateCampaign(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        try:
            campaign = Campaign.objects.get(pk=pk, user=request.user)
        except Campaign.DoesNotExist:
            return Response({"error": "Campaign not found."}, status=status.HTTP_404_NOT_FOUND)
            
        serializer = CampaignSerializer(campaign, data=request.data, partial=False, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Campaign updated successfully.", "data": serializer.data}, status=status.HTTP_200_OK)
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    
class UpdateCampaignStatus(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            campaign = Campaign.objects.get(pk=pk, user=request.user)
        except Campaign.DoesNotExist:
            return Response({"error": "Campaign not found."}, status=status.HTTP_404_NOT_FOUND)
        
        new_status = request.data.get('status')
        if not new_status:
            return Response({"error": "Status is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        valid_statuses = [choice[0] for choice in Campaign.STATUS_CHOICES] 
        if new_status not in valid_statuses:
            return Response({"error": "Invalid status. Valid statuses are: {}.".format(', '.join(valid_statuses))}, status=status.HTTP_400_BAD_REQUEST)
        
        old_status = campaign.status
        campaign.status = new_status
        campaign.save()
        
        if old_status != new_status:
            self.send_status_update_email(request.user.email, campaign.title, new_status)
        
        # Archive campaign if its status is completed and updated_at is more than 3 days old
        if campaign.status == "completed":
            if timezone.now() - campaign.updated_at > timedelta(days=3):
                self.archive_campaign(campaign)
                return Response({"message": "Campaign archived and transferred to history. You have been notified via email."}, status=status.HTTP_200_OK)
        
        return Response({"message": "Campaign status updated to {}.".format(new_status)}, status=status.HTTP_200_OK)
        
    def send_status_update_email(self, email, campaign_title, status):
        subject = "Campaign Status Update: {}".format(campaign_title)
        message = "The status of your campaign '{}' has been updated to '{}'.".format(campaign_title, status)
        send_mail(subject, message, 'noreply@campaignapp.com', [email])
        
    def archive_campaign(self, campaign):
        # Create a historical campaign entry
        HistoricalCampaign.objects.create(
            user=campaign.user,
            title=campaign.title,
            description=campaign.description,
            budget=campaign.budget,
            startDate=campaign.startDate,
            endDate=campaign.endDate,
            priority=campaign.priority,
            status=campaign.status,
            platform=campaign.platform,
            created_at=campaign.created_at
        )
        # Send email notification about transfer
        subject = "Campaign Archived: {}".format(campaign.title)
        message = ("Your campaign '{}' has been archived and transferred to our historical records because it was completed "
                   "and not updated for more than 3 days.").format(campaign.title)
        send_mail(subject, message, 'noreply@campaignapp.com', [campaign.user.email])
        # Delete the active campaign
        campaign.delete()
