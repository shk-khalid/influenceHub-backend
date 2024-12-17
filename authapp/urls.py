from django.urls import path
from .views import LoginUser, VerifyOTP, RegisterUser, VerifyEmail, UpdateUserDetails, ForgotPassword, ResetPassword, LogoutUser

urlpatterns = [
    path('login/', LoginUser.as_view(), name='Login User'),
    path('verify-otp/', VerifyOTP.as_view(), name='Verify Otp'),
    path('register/', RegisterUser.as_view(), name='Register User'),
    path('verify-email/', VerifyEmail.as_view(), name='Verify Email'),
    path('update-profile/', UpdateUserDetails.as_view(), name='Update Details'),
    path('forgot-password/', ForgotPassword.as_view(), name='Forgot Password'),
    path('reset-password/', ResetPassword.as_view(), name='Reset Password'),
    path('logout/', LogoutUser.as_view(), name='Logout')
]
