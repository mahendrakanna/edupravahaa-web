from django.urls import path
from asgiref.sync import sync_to_async
from edu_platform.views.class_views import ClassScheduleView, ClassSessionRecordingView
from django.views.generic import TemplateView

urlpatterns = [
    path('schedules/', ClassScheduleView.as_view(), name='class-schedule-list'),
    path('schedules/<int:schedule_id>/', ClassScheduleView.as_view(), name='class-schedule-detail'),
    path('sessions/<uuid:class_id>/recording/', ClassSessionRecordingView.as_view(), name='class-session-recording'),
    path('classroom/test/', TemplateView.as_view(template_name='classroom.html'), name='classroom_test'),
]