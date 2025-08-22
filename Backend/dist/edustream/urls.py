"""
URL configuration for edustream project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions

schema_view = get_schema_view(
    openapi.Info(
        title="EduStream API",
        default_version='v1',
        description="API documentation for EduStream VR Learning Platform",
        terms_of_service="https://www.edustream.com/terms/",
        contact=openapi.Contact(email="support@edustream.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API endpoints
    path('api/auth/', include('edu_platform.urls.auth_urls')),
    path('api/courses/', include('edu_platform.urls.course_urls')),
    path('api/classes/', include('edu_platform.urls.class_urls')),
    path('api/payments/', include('edu_platform.urls.payment_urls')),
    # path('api/recordings/', include('edu_platform.urls.recordings_urls')),
    
    # API documentation
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
