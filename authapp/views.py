from django.contrib.auth import get_user_model, login, logout
from django.utils.decorators import method_decorator
from django.core.mail import send_mail
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from .serializers import RegistrationSerializer, LoginSerializer, ProfileUpdateSerializer
from .models import OTP, EmailVerification, PasswordResetOTP
from authapp.serializers import UserSerializer
from django_ratelimit.decorators  import ratelimit
from rest_framework.permissions import AllowAny, IsAdminUser

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
    def patch(self, request):
        serializer = ProfileUpdateSerializer(instance=request.user, data=request.data, partial=True, context={'request': request})
        
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "User details updated successfully. "}, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status.HTTP_400_BAD_REQUEST)
    
class ViewUserProfile(APIView):
    def get(self, request):
        user = request.user
        serializer = ProfileUpdateSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class AdminVerifyUser(APIView):
    permission_classes = [IsAdminUser]
    
    def post(self, request):
        user_id = request.data.get('user_id')
        action = request.data.get('action')  # either 'verify' or 'unverify'

        if not user_id or action not in ['verify', 'unverify']:
            return Response({"error": "Invalid request parameters."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            verification = EmailVerification.objects.get(user_id=user_id)
            
            # Admin verification logic
            if action == 'verify':
                if verification.is_admin_verified:
                    return Response({"message": "User is already verified by admin."}, status=status.HTTP_200_OK)
                verification.is_admin_verified = True
                verification.save()
                return Response({"message": "User profile has been approved by admin."}, status=status.HTTP_200_OK)
            elif action == 'unverify':
                if not verification.is_admin_verified:
                    return Response({"message": "User is already unverified by admin."}, status=status.HTTP_200_OK)
                verification.is_admin_verified = False
                verification.save()
                return Response({"message": "User profile has been unverified by admin."}, status=status.HTTP_200_OK)
        
        except EmailVerification.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

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

@method_decorator(ratelimit(key='ip', rate='10/h', block=True), name='dispatch')
class VerifyOTP(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        otp_code = request.data.get('otp')
        action = request.data.get('action')  # Add this parameter to distinguish the action
        
        if not email or not otp_code or not action:
            return Response({"error": "Email, OTP, and action are required."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
            otp = OTP.objects.filter(user=user, expired=False).order_by('-timestamp').first()

            if not otp or otp.is_expired():
                otp.expired = True 
                otp.save(update_fields=["expired"])
                print(f"Email: {email}, OTP: {otp_code}, Action: {action}, OTP Found: {otp.code}, Expired: {otp.is_expired()}")
                return Response({"error": "OTP has expired."}, status=status.HTTP_400_BAD_REQUEST)


            if otp.code == otp_code:
                # If the action is login, authenticate the user
                if action == "login":
                    login(request, user)
                    # Generate token or session for the authenticated user
                    token, created = Token.objects.get_or_create(user=user)
                    return Response({"message": "Login successful!", "redirect": "/dashboard", "token": token.key}, status=status.HTTP_200_OK)

                # If the action is forgot password, you can implement the password reset logic
                elif action == "forgot_password":
                    # Assuming you have a function or view to handle password reset
                    return Response({"message": "OTP verified. Please proceed to reset your password."}, status=status.HTTP_200_OK)

                # In case of an invalid action
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
            
            otp = PasswordResetOTP.objects.create(user=user)
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
    def post(self, request):
        email = request.data.get('email')
        new_password = request.data.get('new_password')
        
        if not email or not new_password:
            return Response({"error": "Email and new password are required."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
            # Set the new password and save it
            user.set_password(new_password)
            user.save()
            return Response({"message": "Password reset successful!"}, status=status.HTTP_200_OK)
        
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

class UserList(APIView):
    def get(self):
        users = User.object.all() 
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)
    
class LogoutUser(APIView):
    def get(self, request):
        logout(request)
        return Response({"message": "Logged out successfully!"}, status=status.HTTP_200_OK)
