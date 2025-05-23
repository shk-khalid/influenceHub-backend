from django.urls import path
from .views import LoginUser, VerifyOTP, ResetOTP, RegisterUser, UpdateUserDetails, ForgotPassword, ResetPassword, LogoutUser, ManualFetch, UserOverview

urlpatterns = [
    path('login/', LoginUser.as_view(), name='Login User'),
    path('verify-otp/', VerifyOTP.as_view(), name='Verify OTP'),
    path('resend-otp/', ResetOTP.as_view(), name="Resend OTP"),
    path('register/', RegisterUser.as_view(), name='Register User'),
    path('update-profile/', UpdateUserDetails.as_view(), name='Update Details'),
    path('forgot-password/', ForgotPassword.as_view(), name='Forgot Password'),
    path('reset-password/', ResetPassword.as_view(), name='Reset Password'),
    path('logout/', LogoutUser.as_view(), name='Logout'),
    path('get-stats/', ManualFetch.as_view(), name='Manual Update InstaStats'),
    path('user-overview/', UserOverview.as_view(), name='Overall User Stastics'),
]
