# edu_platform/urls/dashboard_urls.py
from django.urls import path
from edu_platform.views.dashboard_views import TeacherDashboardAPIView

urlpatterns = [
    path('teacher/', TeacherDashboardAPIView.as_view(), name='teacher-dashboard'),
]
