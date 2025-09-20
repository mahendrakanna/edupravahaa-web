from django.urls import path
from asgiref.sync import sync_to_async
from edu_platform.views.class_views import ClassScheduleView, ClassSessionListView, ClassSessionUpdateView, upload_class_recording, get_recordings, course_recording_count
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('schedules/', ClassScheduleView.as_view(), name='class-schedule-list'),
    path('schedules/<int:schedule_id>/', ClassScheduleView.as_view(), name='class-schedule-detail'),

    path('classroom/test/', TemplateView.as_view(template_name='classroom.html'), name='classroom_test'),

    path('sessions/', ClassSessionListView.as_view(), name='session-list'),
    path('sessions/<int:class_id>/', ClassSessionUpdateView.as_view(), name='session-update'),

    path("sessions/<int:class_id>/upload-recording/", upload_class_recording, name="upload_class_recording"),
    path("recordings/", get_recordings, name="get_recordings"),
    path("recording_count/", course_recording_count, name="courses-with-recordings"),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)