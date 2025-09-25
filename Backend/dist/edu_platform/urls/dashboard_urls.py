# edu_platform/urls/dashboard_urls.py
from django.urls import path
from edu_platform.views.dashboard_views import StudentDashboardAPIView, TeacherDashboardAPIView

urlpatterns = [
    path('teacher/', TeacherDashboardAPIView.as_view(), name='teacher-dashboard'),

    # Student dashboard
    path('student/<int:student_id>/', StudentDashboardAPIView.as_view(), name='student-dashboard'),
]
