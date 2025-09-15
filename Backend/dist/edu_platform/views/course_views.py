from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db.models import Q
from rest_framework import serializers
from edu_platform.models import Course, CourseSubscription, ClassSchedule
from edu_platform.serializers.course_serializers import CourseSerializer, MyCoursesSerializer
from edu_platform.permissions.auth_permissions import IsTeacher, IsStudent, IsTeacherOrAdmin, IsAdmin
import logging

logger = logging.getLogger(__name__)

def get_error_message(serializer):
    """Extracts a specific error message from serializer errors."""
    error_message = 'Invalid input data.'
    for field in serializer.errors:
        if isinstance(serializer.errors[field], dict) and 'error' in serializer.errors[field]:
            return serializer.errors[field]['error']
        elif isinstance(serializer.errors[field], list):
            return serializer.errors[field][0]
    if 'non_field_errors' in serializer.errors:
        return serializer.errors['non_field_errors'][0]
    if serializer.errors:
        return list(serializer.errors.values())[0][0] if isinstance(list(serializer.errors.values())[0], list) else list(serializer.errors.values())[0]
    return error_message

class BaseAPIView(APIView):
    def validate_serializer(self, serializer_class, data, context=None):
        serializer = serializer_class(data=data, context=context or {'request': self.request})
        if not serializer.is_valid():
            raise serializers.ValidationError({
                'error': get_error_message(serializer),
                'status': status.HTTP_400_BAD_REQUEST
            })
        return serializer

class CourseListView(generics.ListAPIView):
    """Lists active courses with filtering for students."""
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated, IsTeacher | IsStudent | IsAdmin]
    
    def get_queryset(self):
        """Filters courses based on user role, purchase status, and query parameters."""
        queryset = Course.objects.filter(is_active=True)
        user = self.request.user
        if user.is_authenticated and user.role == 'student':
            if not user.is_trial_expired and not user.has_purchased_courses:
                pass
            elif user.has_purchased_courses:
                purchased_course_ids = CourseSubscription.objects.filter(
                    student=user, payment_status='completed'
                ).values_list('course__id', flat=True)
                queryset = queryset.exclude(id__in=purchased_course_ids)
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(category__icontains=search)
            )
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category__iexact=category)
        return queryset

    @swagger_auto_schema(
        operation_description="List active courses with optional search and category filters, including batch details",
        responses={
            200: openapi.Response(
                description="Courses retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'data': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Items(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'name': openapi.Schema(type=openapi.TYPE_STRING),
                                    'slug': openapi.Schema(type=openapi.TYPE_STRING),
                                    'description': openapi.Schema(type=openapi.TYPE_STRING),
                                    'category': openapi.Schema(type=openapi.TYPE_STRING),
                                    'level': openapi.Schema(type=openapi.TYPE_STRING),
                                    'thumbnail': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                    'duration_hours': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'base_price': openapi.Schema(type=openapi.TYPE_NUMBER),
                                    'advantages': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING)),
                                    'batches': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING)),
                                    'schedule': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_OBJECT)),
                                    'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                    'created_at': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                                    'updated_at': openapi.Schema(type=openapi.TYPE_STRING, format='date-time')
                                }
                            )
                        )
                    }
                )
            ),
            401: openapi.Response(
                description="Unauthorized",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER)
                    }
                )
            ),
            500: openapi.Response(
                description="Server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER)
                    }
                )
            )
        }
    )
    def get(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'message': 'Courses retrieved successfully.',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Course list error: {str(e)}")
            return Response({
                'error': 'Failed to retrieve courses. Please try again.',
                'status': status.HTTP_500_INTERNAL_SERVER_ERROR
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AdminCourseCreateView(BaseAPIView, generics.CreateAPIView):
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    @swagger_auto_schema(
        operation_description="Create a new course (Admin only)",
        responses={
            201: openapi.Response(
                description="Course created successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'data': openapi.Schema(type=openapi.TYPE_OBJECT)
                    }
                )
            ),
            400: openapi.Response(
                description="Invalid input",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER)
                    }
                )
            ),
            401: openapi.Response(
                description="Unauthorized",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER)
                    }
                )
            ),
            403: openapi.Response(
                description="Forbidden",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER)
                    }
                )
            ),
            500: openapi.Response(
                description="Server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER)
                    }
                )
            )
        }
    )

    def post(self, request, *args, **kwargs):
        try:
            serializer = self.validate_serializer(CourseSerializer, request.data)
            course = serializer.save()
            return Response({
                'message': 'Course created successfully.',
                'data': CourseSerializer(course, context={'request': request}).data
            }, status=status.HTTP_201_CREATED)
        except serializers.ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Course creation error: {str(e)}")
            return Response({
                'error': 'Failed to create course. Please try again.',
                'status': status.HTTP_500_INTERNAL_SERVER_ERROR
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AdminCourseUpdateView(BaseAPIView, generics.UpdateAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_description="Update a course (Admin only)",
        responses={
            200: openapi.Response(
                description="Course updated successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'data': openapi.Schema(type=openapi.TYPE_OBJECT)
                    }
                )
            ),
            400: openapi.Response(
                description="Invalid input",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER)
                    }
                )
            ),
            401: openapi.Response(
                description="Unauthorized",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER)
                    }
                )
            ),
            403: openapi.Response(
                description="Forbidden",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER)
                    }
                )
            ),
            500: openapi.Response(
                description="Server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER)
                    }
                )
            )
        }
    )
    def put(self, request, *args, **kwargs):
        try:
            course = self.get_object()
            serializer = self.validate_serializer(CourseSerializer, request.data, context={'request': request})
            serializer.instance = course
            serializer.save()
            return Response({
                'message': 'Course updated successfully.',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        except serializers.ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Course update error: {str(e)}")
            return Response({
                'error': 'Failed to update course. Please try again.',
                'status': status.HTTP_500_INTERNAL_SERVER_ERROR
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class MyCoursesView(generics.ListAPIView):
    """Lists purchased courses for students or assigned courses for teachers with their specific batch and schedule details."""
    serializer_class = MyCoursesSerializer
    permission_classes = [IsAuthenticated, IsStudent | IsTeacher]
    
    def get_queryset(self):
        """Returns purchased courses for students or assigned courses for teachers."""
        user = self.request.user
        if user.role == 'student':
            return CourseSubscription.objects.filter(
                student=user,
                payment_status='completed'
            ).select_related('course').prefetch_related('enrollments').order_by('-purchased_at')
        elif user.role == 'teacher':
            return Course.objects.filter(
                class_schedules__teacher=user,
                is_active=True
            ).distinct().order_by('-created_at')
        return CourseSubscription.objects.none()

    @swagger_auto_schema(
        operation_description="List purchased courses for students (with enrolled batch and schedule details) or assigned courses for teachers (with all assigned batches and their schedule details)",
        responses={
            200: openapi.Response(
                description="Courses retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'data': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Items(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                    'course': openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                            'name': openapi.Schema(type=openapi.TYPE_STRING),
                                            'slug': openapi.Schema(type=openapi.TYPE_STRING),
                                            'description': openapi.Schema(type=openapi.TYPE_STRING),
                                            'category': openapi.Schema(type=openapi.TYPE_STRING),
                                            'level': openapi.Schema(type=openapi.TYPE_STRING),
                                            'thumbnail': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                            'duration_hours': openapi.Schema(type=openapi.TYPE_INTEGER),
                                            'base_price': openapi.Schema(type=openapi.TYPE_NUMBER),
                                            'advantages': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING)),
                                            'batches': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING)),
                                            'schedule': openapi.Schema(
                                                type=openapi.TYPE_ARRAY,
                                                items=openapi.Items(
                                                    type=openapi.TYPE_OBJECT,
                                                    properties={
                                                        'days': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING)),
                                                        'time': openapi.Schema(type=openapi.TYPE_STRING),
                                                        'type': openapi.Schema(type=openapi.TYPE_STRING),
                                                        'batchStartDate': openapi.Schema(type=openapi.TYPE_STRING),
                                                        'batchEndDate': openapi.Schema(type=openapi.TYPE_STRING)
                                                    }
                                                )
                                            ),
                                            'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                            'created_at': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                                            'updated_at': openapi.Schema(type=openapi.TYPE_STRING, format='date-time')
                                        }
                                    ),
                                    'purchased_at': openapi.Schema(type=openapi.TYPE_STRING, format='date-time', nullable=True),
                                    'payment_status': openapi.Schema(type=openapi.TYPE_STRING, nullable=True)
                                }
                            )
                        )
                    }
                )
            ),
            401: openapi.Response(
                description="Unauthorized",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER)
                    }
                )
            ),
            403: openapi.Response(
                description="Forbidden",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER)
                    }
                )
            ),
            500: openapi.Response(
                description="Server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER)
                    }
                )
            )
        }
    )
    
    def get(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            message = 'Assigned courses retrieved successfully.' if request.user.role == 'teacher' else 'Purchased courses retrieved successfully.'
            return Response({
                'message': message,
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Courses retrieval error for {request.user.role}: {str(e)}")
            return Response({
                'error': 'Failed to retrieve courses. Please try again.',
                'status': status.HTTP_500_INTERNAL_SERVER_ERROR
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)