from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from edu_platform.views.auth_views import (
    RegisterView, LoginView, LogoutView, ProfileView,
    TeacherRegisterView, ListTeachersView, ListStudentsView,
    ChangePasswordView, SendOTPView,
    VerifyOTPView, ForgotPasswordView, TrialStatusView,
    AdminRegisterView
)


urlpatterns = [
    # OTP endpoints
    path('send-otp/', SendOTPView.as_view(), name='send_otp'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify_otp'),
    
    # Auth endpoints
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot_password'),
    
    # Profile endpoints
    path('profile/', ProfileView.as_view(), name='profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('trial-status/', TrialStatusView.as_view(), name='trial_status'),

    # Admin endpoints
    path('register/teacher/', TeacherRegisterView.as_view(), name='register_teacher'),
    path('register/admin/', AdminRegisterView.as_view(), name='register_admin'),
    path('admin/teachers/', ListTeachersView.as_view(), name='list_teachers'),
    path('admin/students/', ListStudentsView.as_view(), name='list_students'),
]