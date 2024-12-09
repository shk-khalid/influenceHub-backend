from django.urls import path
from .views import LoginUser, VerifyOTP, RegisterUser, VerifyEmail, ForgotPassword, ResetPassword

urlpatterns = [
    path('login/', LoginUser.as_view(), name='login'),
    path('verify-otp/', VerifyOTP.as_view(), name='verify otp'),
    path('register/', RegisterUser.as_view(), name='register'),
    path('verify-email/', VerifyEmail.as_view(), name='verify email'),
    path('forgot-password/', ForgotPassword.as_view(), name='forgot password'),
    path('reset-password/', ResetPassword.as_view(), name='reset password'),
]
