from rest_framework import generics, status, views
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from edu_platform.models import Course
from edu_platform.serializers.course_serializers import CourseSerializer, PurchasedCoursesSerializer
from edu_platform.permissions.auth_permissions import IsTeacher, IsStudent, IsTeacherOrAdmin, IsAdmin
from edu_platform.models import CourseSubscription


class CourseListView(generics.ListAPIView):
    """Lists active courses with filtering for students."""
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated, IsTeacher | IsStudent | IsAdmin]
    
    def get_queryset(self):
        """Filters courses based on user role, purchase status, and query parameters."""
        # Start with active courses
        queryset = Course.objects.filter(is_active=True)
        
        # Apply student-specific filtering
        user = self.request.user
        if user.is_authenticated and user.role == 'student':
            if not user.is_trial_expired and not user.has_purchased_courses:
                # Students in trial with no purchases see all active courses
                pass
            elif user.has_purchased_courses:
                # Exclude purchased courses for students with purchases
                purchased_course_ids = CourseSubscription.objects.filter(
                    student=user,
                    payment_status='completed'
                ).values_list('course__id', flat=True)
                queryset = queryset.exclude(id__in=purchased_course_ids)
        
        # Filter by search query across name, description, or category
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(category__icontains=search)
            )
        
        # Filter by category if provided
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category__iexact=category)
            
        return queryset


# Admin Course Management Views
class AdminCourseCreateView(generics.CreateAPIView):
    """Admin-only API to create new courses"""
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    
    @swagger_auto_schema(
        operation_description="Create a new course with all details (Admin only)",
        request_body=CourseSerializer
    )
    def post(self, request, *args, **kwargs):
        """Saves new course and returns its details."""
        # Validate and create course
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        course = serializer.save()
        
        return Response({
            'message': 'Course created successfully',
            'course': CourseSerializer(course, context={'request': request}).data
        }, status=status.HTTP_201_CREATED)


class AdminCourseUpdateView(generics.UpdateAPIView):
    """Updates existing course details for admin users."""
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    lookup_field = 'id'


class MyCoursesView(generics.ListAPIView):
    """Lists all purchased courses for a student."""
    serializer_class = PurchasedCoursesSerializer
    permission_classes = [IsAuthenticated, IsStudent]
    
    def get_queryset(self):
        """Returns purchased course subscriptions for the authenticated student."""
        # Fetch completed subscriptions for the current user
        return CourseSubscription.objects.filter(
            student=self.request.user,
            payment_status='completed'
        ).select_related('course').order_by('-purchased_at')
