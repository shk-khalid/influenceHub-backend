from django.contrib.auth import authenticate, get_user_model, login, logout
from django.utils.decorators import method_decorator
from django.core.mail import send_mail
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from .serializers import RegistrationSerializer, LoginSerializer, ProfileUpdateSerializer
from .models import OTP, EmailVerification, PasswordResetOTP
from django.conf import settings
from authapp.serializers import UserSerializer
from django_ratelimit.decorators  import ratelimit
from rest_framework.permissions import AllowAny, IsAdminUser

User = get_user_model()

class RegisterUser(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # Send verification email
            verification = EmailVerification.objects.create(user=user)
            token = verification.generate_token()
            
            verification_link = f"{settings.FRONTEND_URL}/verify-email/?token={token}"
            
            send_mail(
                'Verify your email address',
                f'Please click on the following link to verify your email: {verification_link}',
                'no-reply@influenceHub.com',
                [user.email],
                fail_silently=False,
            )
            return Response({"message": "Verification email sent. Please verify your email."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_404_NOT_FOUND)
   
class VerifyEmail(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        token = request.query_params.get('token')
        
        try:
            verification = EmailVerification.objects.get(token=token)
            
            if verification.is_email_verified:
                return Response({"message": "Email is already verified."}, status=status.HTTP_200_OK)
            
            verification.is_email_verified = True
            verification.save()
            
            return Response({"message": "Email verified successfully!"}, status=status.HTTP_200_OK)
        
        except EmailVerification.DoesNotExist:
            return Response({"message": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST)

class UpdateUserDetails(APIView):
    def post(self, request):
        serializer = ProfileUpdateSerializer(data=request.data, instance=request.user, context={'request': request})
        
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "User details updated successfully. "}, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status.HTTP_400_BAD_REQUEST)
    
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

@method_decorator(ratelimit(key='ip', rate='5/m', block=True), name='dispatch')
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
                f'Your 2FA code is {otp_code}',
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
        
        if not email or not otp_code:
            return Response({"error": "Email and OTP are required."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
            otp = OTP.objects.filter(user=user).last()
            
            if not otp or otp.is_expired():
                return Response({"error": "OTP has expired."}, status=status.HTTP_400_BAD_REQUEST)
            
            if otp.code == otp_code:
                login(request, user)
                # Generate token or session for the authenticated user
                token, created = Token.objects.get_or_create(user=user)
                return Response({"message": "Login successful!", "redirect": "/dashboard", "token":token.key}, status=status.HTTP_200_OK)
            return Response({"error": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)
        
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

class ForgotPassword(APIView):
    def post(self, request):
        email = request.data.get('email')
        
        try:
            user = User.objects.get(email=email)
            
            otp = PasswordResetOTP.objects.create(user=user)
            otp_code = otp.generate_otp()
            
            send_mail(
                'Your Password Reset Code',
                f'Your Password reset code is {otp_code}',
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
        otp_code = request.data.get('otp')
        new_password = request.data.get('new_password')
        
        try:
            user = User.objects.get(email=email)
            otp = PasswordResetOTP.objects.filter(user=user).last()
            
            if otp.is_expired():
                return Response({"error": "OTP has expired."}, status=status.HTTP_400_BAD_REQUEST)
            
            if otp.code == otp_code:
                user.set_password(new_password)
                user.save()
                return Response({"message": "Password reset successful!"}, status=status.HTTP_200_OK)
            return Response({"error": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)
        
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

class UserList(APIView):
    def get(self):
        users = User.object.all() 
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)
    
class LogoutUser(APIView):
    def post(self, request):
        logout(request)
        return Response({"message": "Logged out successfully!"}, status=status.HTTP_200_OK)
