from django.contrib.auth import get_user_model, login, logout
from django.utils.decorators import method_decorator
from django.core.mail import send_mail
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from .serializers import RegistrationSerializer, LoginSerializer, ProfileUpdateSerializer
from .models import OTP
from authapp.serializers import UserSerializer
from django_ratelimit.decorators  import ratelimit
from rest_framework.permissions import AllowAny

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
            return Response({"message": "User details updated successfully. ", "user": UserSerializer.data}, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status.HTTP_400_BAD_REQUEST)
       
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
                        "redirect": "/dashboard",
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
    def get(self, request):
        logout(request)
        return Response({"message": "Logged out successfully!"}, status=status.HTTP_200_OK)