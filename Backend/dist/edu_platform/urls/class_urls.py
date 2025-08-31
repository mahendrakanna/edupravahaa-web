from django.urls import path
from edu_platform.views.class_views import ClassScheduleView

urlpatterns = [
    path('schedules/', ClassScheduleView.as_view(), name='class-schedule-list'),
    path('schedules/<int:schedule_id>/', ClassScheduleView.as_view(), name='class-schedule-detail'),
]