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
from django.utils import timezone
from datetime import date
import logging

logger = logging.getLogger(__name__)

def api_response(message, message_type, data=None, status_code=200):
    """Standardizes API response structure."""
    response_data = {
        'message': message,
        'message_type': message_type
    }
    if data is not None:
        response_data['data'] = data
    return Response(response_data, status=status_code)

def get_serializer_error_message(errors):
    """Extracts a clean error message from serializer errors."""
    if isinstance(errors, dict):
        for field, error in errors.items():
            if field == 'non_field_errors':
                if isinstance(error, list) and error:
                    if isinstance(error[0], dict) and 'message' in error[0]:
                        return {'message': error[0]['message'], 'message_type': 'error'}
                    return {'message': str(error[0]), 'message_type': 'error'}
            else:
                if isinstance(error, list) and error:
                    if isinstance(error[0], dict) and 'message' in error[0]:
                        return {'message': error[0]['message'], 'message_type': 'error'}
                    error_msg = str(error[0])
                    field_name = field.replace('_', ' ').title()
                    if error_msg == 'This field may not be blank.':
                        return {'message': f"{field_name} cannot be empty.", 'message_type': 'error'}
                    if error_msg == 'This field is required.':
                        return {'message': f"{field_name} is required.", 'message_type': 'error'}
                    if error_msg == 'Ensure this field has at least 8 characters.':
                        return {'message': f"{field_name} must be at least 8 characters long.", 'message_type': 'error'}
                    return {'message': error_msg, 'message_type': 'error'}
                elif isinstance(error, dict) and 'message' in error:
                    return {'message': error['message'], 'message_type': 'error'}
                return {'message': str(error), 'message_type': 'error'}
    elif isinstance(errors, list) and errors:
        if isinstance(errors[0], dict) and 'message' in errors[0]:
            return {'message': errors[0]['message'], 'message_type': 'error'}
        return {'message': str(errors[0]), 'message_type': 'error'}
    return {'message': 'Invalid input provided.', 'message_type': 'error'}

class CourseListView(generics.ListAPIView):
    """Lists active courses with filtering for students."""
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated, IsTeacher | IsStudent | IsAdmin]
    
    def get_queryset(self):
        """Filters courses based on user role, purchase status, and query parameters."""
        queryset = Course.objects.filter(is_active=True).prefetch_related("pricings")
        user = self.request.user
        if user.is_authenticated and user.role == 'student':
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
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error']),
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
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'])
                    }
                )
            ),
            403: openapi.Response(
                description="Forbidden",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'])
                    }
                )
            ),
            500: openapi.Response(
                description="Server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'])
                    }
                )
            )
        }
    )
    def get(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return api_response(
                message='Courses retrieved successfully.',
                message_type='success',
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Course list error: {str(e)}")
            return api_response(
                message='Failed to retrieve courses. Please try again.',
                message_type='error',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class AdminCourseCreateView(generics.CreateAPIView):
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
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error']),
                        'data': openapi.Schema(type=openapi.TYPE_OBJECT)
                    }
                )
            ),
            400: openapi.Response(
                description="Invalid input",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'])
                    }
                )
            ),
            401: openapi.Response(
                description="Unauthorized",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'])
                    }
                )
            ),
            403: openapi.Response(
                description="Forbidden",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'])
                    }
                )
            ),
            500: openapi.Response(
                description="Server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'])
                    }
                )
            )
        }
    )

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            error_response = get_serializer_error_message(serializer.errors)
            return api_response(
                message=error_response['message'],
                message_type='error',
                status_code=status.HTTP_400_BAD_REQUEST
            )
        try:
            course = serializer.save()
            return api_response(
                message='Course created successfully.',
                message_type='success',
                data=CourseSerializer(course, context={'request': request}).data,
                status_code=status.HTTP_201_CREATED
            )
        except Exception as e:
            logger.error(f"Course creation error: {str(e)}")
            return api_response(
                message='Failed to create course. Please try again.',
                message_type='error',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminCourseUpdateView(generics.UpdateAPIView):
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
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error']),
                        'data': openapi.Schema(type=openapi.TYPE_OBJECT)
                    }
                )
            ),
            400: openapi.Response(
                description="Invalid input",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'])
                    }
                )
            ),
            401: openapi.Response(
                description="Unauthorized",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'])
                    }
                )
            ),
            403: openapi.Response(
                description="Forbidden",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'])
                    }
                )
            ),
            404: openapi.Response(
                description="Course not found",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'])
                    }
                )
            ),
            500: openapi.Response(
                description="Server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'])
                    }
                )
            )
        }
    )
    def put(self, request, *args, **kwargs):
        try:
            course = self.get_object()
            serializer = self.get_serializer(course, data=request.data, context={'request': request})
            if not serializer.is_valid():
                error_response = get_serializer_error_message(serializer.errors)
                return api_response(
                    message=error_response['message'],
                    message_type='error',
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            serializer.save()
            return api_response(
                message='Course updated successfully.',
                message_type='success',
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )
        except Course.DoesNotExist:
            return api_response(
                message='Course not found.',
                message_type='error',
                status_code=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Course update error: {str(e)}")
            return api_response(
                message='Failed to update course. Please try again.',
                message_type='error',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error']),
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
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'])
                    }
                )
            ),
            403: openapi.Response(
                description="Forbidden",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'])
                    }
                )
            ),
            500: openapi.Response(
                description="Server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'])
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
            return api_response(
                message=message,
                message_type='success',
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Courses retrieval error for {request.user.role}: {str(e)}")
            return api_response(
                message='Failed to retrieve courses. Please try again.',
                message_type='error',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )