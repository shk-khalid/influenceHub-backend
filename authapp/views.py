import numpy as np
from django.contrib.auth import get_user_model, login, logout
from django.utils.decorators import method_decorator
from django.core.mail import send_mail
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from .serializers import RegistrationSerializer, LoginSerializer, ProfileUpdateSerializer
from .models import OTP, InstaStats, InstaPost
from .utils import extract_instagram_username, update_insta_stats_for_username
from authapp.serializers import UserSerializer
from django_ratelimit.decorators  import ratelimit
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

User = get_user_model()

from django.core.mail import send_mail

class RegisterUser(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            # Send welcome email
            send_mail(
                'Welcome to InfluenceHub!',
                f'Hi {user.username},\n\nWelcome to InfluenceHub! We are excited to have you on board.\n\nFeel free to explore and connect with the community.\n\nBest Regards,\nThe InfluenceHub Team',
                'no-reply@influenceHub.com',
                [user.email],
                fail_silently=False,
            )

            return Response({"message": "Registration successful. A welcome email has been sent."}, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
  
class UpdateUserDetails(APIView):
    permission_classes = [IsAuthenticated] 
    parser_classes = (JSONParser, MultiPartParser, FormParser)
    
    def patch(self, request):
        serializer = ProfileUpdateSerializer(
            instance=request.user, 
            data=request.data, 
            partial=True, 
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            # After saving, check if socialLinks contains an Instagram id.
            # For example, if socialLinks is a JSON with key "insta_id":
            social_links = serializer.data.get("socialLinks")
            if social_links and isinstance(social_links, dict):
                insta_url = social_links.get("instagram")
                if insta_url:
                    insta_username = extract_instagram_username(insta_url)
                    if insta_username:
                        # Trigger the Instagram stats update.
                        update_insta_stats_for_username(insta_username)
                    
            return Response({"message": "User details updated successfully.", "user": serializer.data}, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
     
@method_decorator(ratelimit(key='ip', rate='5/h', block=True), name='dispatch')
class LoginUser(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.validated_data['user']

            otp = OTP.objects.create(user=user)
            otp_code = otp.generate_otp()
            
            send_mail(
                'Your 2FA code ',
                'Your 2FA code is {}'.format(otp_code),
                'no-reply@influenceHub.com',
                [user.email],
                fail_silently=False,
            )
            return Response({"message": "OTP sent to your email."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VerifyOTP(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        otp_code = request.data.get('otp')
        action = request.data.get('action')

        if not email or not otp_code or not action:
            return Response({"error": "Email, OTP, and action are required."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
            
            # Fetch the latest non-expired OTP for the user
            otp = OTP.objects.filter(user=user, expired=False).order_by('-timestamp').first()

            if not otp or otp.is_expired():
                if otp:
                    otp.expired = True
                    otp.save(update_fields=["expired"])
                return Response({"error": "OTP has expired."}, status=status.HTTP_400_BAD_REQUEST)

            if otp.code == otp_code:
                otp.expired = True
                otp.save(update_fields=["expired"])

                # If the action is login, authenticate the user
                if action == "login":
                    login(request, user)
                    token, _ = Token.objects.get_or_create(user=user)
                    user_serializer = UserSerializer(user)

                    return Response({
                        "message": "Login successful!",
                        "token": token.key,
                        "user": user_serializer.data
                    }, status=status.HTTP_200_OK)

                # If the action is forgot_password, allow password reset
                elif action == "forgot_password":
                    reset_token, _ = Token.objects.get_or_create(user=user)
                    return Response({
                        "message": "OTP verified. Please proceed to reset your password.",
                        "token": reset_token.key
                    }, status=status.HTTP_200_OK)
                else: 
                    return Response({"error": "Invalid action."}, status=status.HTTP_400_BAD_REQUEST)

            return Response({"error": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)
        
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

class ResetOTP(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response({"error": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.filter(email=email).first()
            if not user:
                return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

            # Expire any existing OTPs
            OTP.objects.filter(user=user, expired=False).update(expired=True)

            # Generate a new OTP
            new_otp = OTP.objects.create(user=user)
            otp_code = new_otp.generate_otp()  
            new_otp.save()

            # Send email with the new OTP
            send_mail(
                'Your New OTP Code',
                f'Your new OTP code is {otp_code}',
                'no-reply@influenceHub.com',
                [user.email],
                fail_silently=False,
            )
            
            return Response({"message": "A new OTP has been sent to your email."}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": "Failed to reset OTP. Please try again later."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ForgotPassword(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        email = request.data.get('email')
        
        try:
            user = User.objects.get(email=email)
            
            otp = OTP.objects.create(user=user)
            otp_code = otp.generate_otp()
            
            send_mail(
                'Your Password Reset Code',
                'Your Password reset code is {}'.format(otp_code),
                'no-reply@influenceHub.com',
                [user.email],
                fail_silently=False,
            )           
            return Response({"message": "OTP sent to your email."}, status=status.HTTP_200_OK)
        
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
            
class ResetPassword(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        new_password = request.data.get("new_password")
        reset_token = request.data.get("reset_token")

        if not email or not new_password or not reset_token:
            return Response({"error": "Email, new password, and reset token are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
            token = Token.objects.filter(user=user, key=reset_token).first()

            if not token:
                return Response({"error": "Invalid or expired reset token."}, status=status.HTTP_400_BAD_REQUEST)

            # Update user password
            user.set_password(new_password)
            user.save()

            # Delete reset token after successful password change
            token.delete()

            return Response({"message": "Password reset successful. You may now log in with your new password."}, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
 
class LogoutUser(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Delete the user's authentication token
        Token.objects.filter(user=request.user).delete()

        # Log the user out
        logout(request)

        return Response({"message": "Logged out successfully!"}, status=status.HTTP_200_OK)
    
class ManualFetch(APIView):    
    def post(self, request):
        # Expecting socialLinks to be a JSON object in the request body containing "insta_id"
        social_links = request.data.get("socialLinks")
        if not social_links or not isinstance(social_links, dict):
            return Response(
                {"error": "socialLinks must be provided as a JSON object with an 'insta_id' key."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        insta_url = social_links.get("instagram")
        if not insta_url:
            return Response(
                {"error": "Instagram URL is required in socialLinks under the key 'instagram'."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        insta_username = extract_instagram_username(insta_url)
        if not insta_username:
            return Response(
                {"error": "Instagram id ('insta_id') is required in socialLinks."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Call the helper function to fetch and update Instagram stats
        update_result = update_insta_stats_for_username(insta_username)
        
        # Return a confirmation along with details from the update process
        return Response(
            {
                "message": "Instagram stats updated successfully.",
                "result": {
                    "insta_id": str(update_result.get("insta_stats").insta_id) if update_result.get("insta_stats") else None,
                    "media_count": update_result.get("media_count", 0)
                }
            },
            status=status.HTTP_200_OK
        )
        
class UserOverview(APIView):
    """
    Return an overview of the user's Instagram engagement metrics using
    the stored data in InstaStats and InstaPost. The lookup for the Instagram
    record is performed by extracting the username from the user's socialLinks
    field which is expected to follow the format: "www.instagram.com/username".

    Metrics include:
      - engagement_score: Total likes and comments across all posts.
      - engagement_per_follower: Engagement score divided by the followers count.
      - estimated_reach: Estimated using a heuristic multiplier.
      - estimated_impressions: Estimated using a heuristic multiplier.
      - reach_ratio: Estimated reach normalized by the followers count.

    The API also returns a list containing details of each post.
    """
    
    def get(self, request):
        social_links = request.user.socialLinks
        instagram_url = social_links.get("instagram")
        
        if not instagram_url:
            return Response(
                {"error": "Instagram URL not found in your social links."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        instagram_username = extract_instagram_username(instagram_url)
        if not instagram_username:
            return Response(
                {"error": "Unable to extract Instagram username from the provided URL."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        insta_stats = InstaStats.objects.filter(userName=instagram_username).first()
        if not insta_stats:
            return Response(
                {"error": "Instagram statistics not found for the provided username."},
                status=status.HTTP_404_NOT_FOUND
            )
            
        posts = insta_stats.posts.all()
        
        total_likes, total_comments, count = 0, 0, 0
        posts_data = []
        for post in posts:
            if post.post_detail:
                # Fetch "likeCount" and "commentCount" from post_detail JSON.
                like_count = post.post_detail.get("likeCount")
                comment_count = post.post_detail.get("commentCount")
                if like_count is not None and comment_count is not None:
                    total_likes += float(like_count)
                    total_comments += float(comment_count)
                    count += 1
                    posts_data.append({
                        "post_number": post.post_number,
                        "like_count": float(like_count),
                        "comment_count": float(comment_count),
                    })
                    
        avg_likes_computed = total_likes / count if count > 0 else 0
        avg_comments_computed = total_comments / count if count > 0 else 0
        
        followers = insta_stats.followers
        verified_multiplier = 1.2 if insta_stats.is_verified else 1.0
        professional_multiplier = 1.1 if getattr(insta_stats, "is_professional", False) else 1.0

        # Calculate metrics using the provided formula.
        estimated_reach = ((followers ** 0.6) *
                           ((avg_likes_computed + avg_comments_computed) ** 0.4) *
                           verified_multiplier * professional_multiplier * 100)
        estimated_impression = estimated_reach * 1.5
        reach_ratio = estimated_reach / followers if followers > 0 else 0
        engagement_score = (avg_likes_computed * 0.7) + (avg_comments_computed * 0.3)
        engagement_per_follower = ((avg_likes_computed + avg_comments_computed) / followers) if followers > 0 else np.nan
        
        overview = {
            "estimated_reach": estimated_reach,
            "estimated_impression": estimated_impression,
            "reach_ratio": reach_ratio,
            "engagement_score": engagement_score,
        }
        
        return Response({
            "overview": overview,
            "posts": posts_data
        }, status=status.HTTP_200_OK)
        