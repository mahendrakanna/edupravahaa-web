from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.utils import timezone
from datetime import timedelta, datetime
from django.conf import settings
from django.core.exceptions import ValidationError
from edu_platform.permissions.auth_permissions import IsAdmin, IsTeacher
from edu_platform.models import User, ClassSchedule, ClassSession, Course, CourseEnrollment
from edu_platform.serializers.class_serializers import ClassScheduleSerializer, ClassSessionSerializer, CourseSessionSerializer
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
                    if isinstance(error[0], dict) and 'error' in error[0]:
                        return {'message': error[0]['error'], 'message_type': 'error'}
                    return {'message': str(error[0]), 'message_type': 'error'}
            else:
                if isinstance(error, list) and error:
                    if isinstance(error[0], dict) and 'error' in error[0]:
                        return {'message': error[0]['error'], 'message_type': 'error'}
                    error_msg = str(error[0])
                    field_name = field.replace('_', ' ').title()
                    if error_msg == 'This field may not be blank.':
                        return {'message': f"{field_name} cannot be empty.", 'message_type': 'error'}
                    if error_msg == 'This field is required.':
                        return {'message': f"{field_name} is required.", 'message_type': 'error'}
                    if error_msg == 'Ensure this field has at least 8 characters.':
                        return {'message': f"{field_name} must be at least 8 characters long.", 'message_type': 'error'}
                    return {'message': error_msg, 'message_type': 'error'}
                elif isinstance(error, dict) and 'error' in error:
                    return {'message': error['error'], 'message_type': 'error'}
                return {'message': str(error), 'message_type': 'error'}
    elif isinstance(errors, list) and errors:
        if isinstance(errors[0], dict) and 'error' in errors[0]:
            return {'message': errors[0]['error'], 'message_type': 'error'}
        return {'message': str(errors[0]), 'message_type': 'error'}
    return {'message': 'Invalid input provided.', 'message_type': 'error'}

class ClassScheduleView(APIView):
    """Manages retrieval, creation, and updates of ClassSchedule objects."""
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="List all class schedules (admin) or teacher's own schedules",
        responses={
            200: openapi.Response(
                description="Class schedules retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description="Response message"),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'], description="Type of message"),
                        'data': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_INTEGER, description="Schedule ID"),
                                    'course': openapi.Schema(type=openapi.TYPE_STRING, description="Course name"),
                                    'course_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="Course ID"),
                                    'teacher': openapi.Schema(type=openapi.TYPE_STRING, description="Teacher email"),
                                    'batch': openapi.Schema(type=openapi.TYPE_STRING, description="Batch type (weekdays/weekends)"),
                                    'sessions': openapi.Schema(
                                        type=openapi.TYPE_ARRAY,
                                        items=openapi.Schema(
                                            type=openapi.TYPE_OBJECT,
                                            properties={
                                                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                                'session_date': openapi.Schema(type=openapi.TYPE_STRING, format='date'),
                                                'start_time': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                                                'end_time': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                                                'recording_url': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                                'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN)
                                            }
                                        ),
                                        description="List of class sessions"
                                    ),
                                    'weekdays_start_date': openapi.Schema(type=openapi.TYPE_STRING, format='date', nullable=True),
                                    'weekdays_end_date': openapi.Schema(type=openapi.TYPE_STRING, format='date', nullable=True),
                                    'weekdays_days': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), nullable=True),
                                    'weekdays_start': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                    'weekdays_end': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                    'weekend_start_date': openapi.Schema(type=openapi.TYPE_STRING, format='date', nullable=True),
                                    'weekend_end_date': openapi.Schema(type=openapi.TYPE_STRING, format='date', nullable=True),
                                    'saturday_start': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                    'saturday_end': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                    'sunday_start': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                    'sunday_end': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                    'teacher_id': openapi.Schema(type=openapi.TYPE_INTEGER, nullable=True),
                                    'batch_assignment': openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            'teacher_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                            'course_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                            'batches': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING)),
                                            'weekdays_start_date': openapi.Schema(type=openapi.TYPE_STRING, format='date', nullable=True),
                                            'weekdays_end_date': openapi.Schema(type=openapi.TYPE_STRING, format='date', nullable=True),
                                            'weekdays_days': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), nullable=True),
                                            'weekdays_start': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                            'weekdays_end': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                            'weekend_start_date': openapi.Schema(type=openapi.TYPE_STRING, format='date', nullable=True),
                                            'weekend_end_date': openapi.Schema(type=openapi.TYPE_STRING, format='date', nullable=True),
                                            'saturday_start': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                            'saturday_end': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                            'sunday_start': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                            'sunday_end': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                        },
                                        nullable=True
                                    )
                                },
                                description="Class schedule details"
                            ),
                            description="List of class schedules"
                        )
                    }
                )
            ),
            403: openapi.Response(
                description="Permission denied",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description="Error message"),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'], description="Type of message")
                    }
                )
            ),
            500: openapi.Response(
                description="Server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description="Error message"),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'], description="Type of message")
                    }
                )
            )
        }
    )
    def get(self, request, *args, **kwargs):
        """Lists all class schedules for admins or teacher's own schedules."""
        try:
            if request.user.is_admin:
                schedules = ClassSchedule.objects.all()
            else:
                if not request.user.is_teacher:
                    return api_response(
                        message='Only admins or teachers can access class schedules.',
                        message_type='error',
                        status_code=status.HTTP_403_FORBIDDEN
                    )
                schedules = ClassSchedule.objects.filter(teacher=request.user)
            
            serializer = ClassScheduleSerializer(schedules, many=True)
            return api_response(
                message='Class schedules retrieved successfully.',
                message_type='success',
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Error retrieving class schedules: {str(e)}")
            return api_response(
                message='Failed to retrieve schedules. Please try again.',
                message_type='error',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @swagger_auto_schema(
        operation_description="Create a class schedule with sessions (admin only for batch assignments, admin/teacher for single batch)",
        request_body=ClassScheduleSerializer,
        responses={
            201: openapi.Response(
                description="Class schedule created successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description="Response message"),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'], description="Type of message"),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,  # Added top-level type
                            oneOf=[
                                openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                        'course': openapi.Schema(type=openapi.TYPE_STRING),
                                        'course_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                        'teacher': openapi.Schema(type=openapi.TYPE_STRING),
                                        'batch': openapi.Schema(type=openapi.TYPE_STRING),
                                        'sessions': openapi.Schema(
                                            type=openapi.TYPE_ARRAY,
                                            items=openapi.Schema(
                                                type=openapi.TYPE_OBJECT,
                                                properties={
                                                    'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                                    'session_date': openapi.Schema(type=openapi.TYPE_STRING, format='date'),
                                                    'start_time': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                                                    'end_time': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                                                    'recording_url': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                                    'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN)
                                                }
                                            )
                                        ),
                                        'weekdays_start_date': openapi.Schema(type=openapi.TYPE_STRING, format='date', nullable=True),
                                        'weekdays_end_date': openapi.Schema(type=openapi.TYPE_STRING, format='date', nullable=True),
                                        'weekdays_days': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), nullable=True),
                                        'weekdays_start': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                        'weekdays_end': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                        'weekend_start_date': openapi.Schema(type=openapi.TYPE_STRING, format='date', nullable=True),
                                        'weekend_end_date': openapi.Schema(type=openapi.TYPE_STRING, format='date', nullable=True),
                                        'saturday_start': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                        'saturday_end': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                        'sunday_start': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                        'sunday_end': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                        'teacher_id': openapi.Schema(type=openapi.TYPE_INTEGER, nullable=True),
                                        'batch_assignment': openapi.Schema(type=openapi.TYPE_OBJECT, nullable=True)
                                    },
                                    description="Single class schedule"
                                ),
                                openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                            'course': openapi.Schema(type=openapi.TYPE_STRING),
                                            'course_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                            'teacher': openapi.Schema(type=openapi.TYPE_STRING),
                                            'batch': openapi.Schema(type=openapi.TYPE_STRING),
                                            'sessions': openapi.Schema(
                                                type=openapi.TYPE_ARRAY,
                                                items=openapi.Schema(
                                                    type=openapi.TYPE_OBJECT,
                                                    properties={
                                                        'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                                        'session_date': openapi.Schema(type=openapi.TYPE_STRING, format='date'),
                                                        'start_time': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                                                        'end_time': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                                                        'recording_url': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                                        'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN)
                                                    }
                                                )
                                            ),
                                            'weekdays_start_date': openapi.Schema(type=openapi.TYPE_STRING, format='date', nullable=True),
                                            'weekdays_end_date': openapi.Schema(type=openapi.TYPE_STRING, format='date', nullable=True),
                                            'weekdays_days': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), nullable=True),
                                            'weekdays_start': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                            'weekdays_end': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                            'weekend_start_date': openapi.Schema(type=openapi.TYPE_STRING, format='date', nullable=True),
                                            'weekend_end_date': openapi.Schema(type=openapi.TYPE_STRING, format='date', nullable=True),
                                            'saturday_start': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                            'saturday_end': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                            'sunday_start': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                            'sunday_end': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                            'teacher_id': openapi.Schema(type=openapi.TYPE_INTEGER, nullable=True),
                                            'batch_assignment': openapi.Schema(type=openapi.TYPE_OBJECT, nullable=True)
                                        }
                                    ),
                                    description="List of class schedules"
                                )
                            ],
                            description="Single schedule or list of schedules for batch assignments"
                        )
                    }
                )
            ),
            400: openapi.Response(
                description="Invalid input or conflict",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description="Error message"),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'], description="Type of message")
                    }
                )
            ),
            403: openapi.Response(
                description="Permission denied",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description="Error message"),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'], description="Type of message")
                    }
                )
            ),
            500: openapi.Response(
                description="Server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description="Error message"),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'], description="Type of message")
                    }
                )
            )
        }
    )
    def post(self, request, *args, **kwargs):
        """Creates a class schedule with sessions."""
        try:
            # Restrict batch assignments to admins only
            if 'batch_assignment' in request.data and not request.user.is_admin:
                return api_response(
                    message='Only admins can create multiple batch assignments.',
                    message_type='error',
                    status_code=status.HTTP_403_FORBIDDEN
                )
            
            # Restrict single batch creation to admins or the teacher themselves
            if not (request.user.is_admin or request.user.is_teacher):
                return api_response(
                    message='You do not have permission to create schedules.',
                    message_type='error',
                    status_code=status.HTTP_403_FORBIDDEN
                )
            
            serializer = ClassScheduleSerializer(data=request.data, context={'request': request})
            if not serializer.is_valid():
                error_response = get_serializer_error_message(serializer.errors)
                return api_response(
                    message=error_response['message'],
                    message_type='error',
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            result = serializer.save()
            if isinstance(result, dict):
                return api_response(
                    message='Batch assignment created successfully.',
                    message_type='success',
                    data=[ClassScheduleSerializer(s).data for s in result['schedules']],
                    status_code=status.HTTP_201_CREATED
                )
            else:
                return api_response(
                    message='Schedule created successfully.',
                    message_type='success',
                    data=ClassScheduleSerializer(result).data,
                    status_code=status.HTTP_201_CREATED
                )
        except Exception as e:
            logger.error(f"Error creating class schedule: {str(e)}")
            return api_response(
                message='Failed to create schedule. Please try again.',
                message_type='error',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @swagger_auto_schema(
        operation_description="Update a class schedule and sessions by ID (teacher within 7 hours or admin)",
        request_body=ClassScheduleSerializer,
        responses={
            200: openapi.Response(
                description="Class schedule updated successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description="Response message"),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'], description="Type of message"),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'course': openapi.Schema(type=openapi.TYPE_STRING),
                                'course_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'teacher': openapi.Schema(type=openapi.TYPE_STRING),
                                'batch': openapi.Schema(type=openapi.TYPE_STRING),
                                'sessions': openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                            'session_date': openapi.Schema(type=openapi.TYPE_STRING, format='date'),
                                            'start_time': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                                            'end_time': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                                            'recording_url': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                            'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN)
                                        }
                                    )
                                ),
                                'weekdays_start_date': openapi.Schema(type=openapi.TYPE_STRING, format='date', nullable=True),
                                'weekdays_end_date': openapi.Schema(type=openapi.TYPE_STRING, format='date', nullable=True),
                                'weekdays_days': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), nullable=True),
                                'weekdays_start': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                'weekdays_end': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                'weekend_start_date': openapi.Schema(type=openapi.TYPE_STRING, format='date', nullable=True),
                                'weekend_end_date': openapi.Schema(type=openapi.TYPE_STRING, format='date', nullable=True),
                                'saturday_start': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                'saturday_end': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                'sunday_start': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                'sunday_end': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                'teacher_id': openapi.Schema(type=openapi.TYPE_INTEGER, nullable=True),
                                'batch_assignment': openapi.Schema(type=openapi.TYPE_OBJECT, nullable=True)
                            },
                            description="Updated class schedule"
                        )
                    }
                )
            ),
            400: openapi.Response(
                description="Invalid input",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description="Error message"),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'], description="Type of message")
                    }
                )
            ),
            403: openapi.Response(
                description="Permission denied",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description="Error message"),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'], description="Type of message")
                    }
                )
            ),
            404: openapi.Response(
                description="Schedule not found",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description="Error message"),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'], description="Type of message")
                    }
                )
            ),
            500: openapi.Response(
                description="Server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description="Error message"),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'], description="Type of message")
                    }
                )
            )
        }
    )
    def put(self, request, schedule_id=None, *args, **kwargs):
        """Updates a specific class schedule and its sessions."""
        try:
            schedule = ClassSchedule.objects.get(id=schedule_id)
            if request.user.is_teacher:
                if schedule.teacher != request.user:
                    return api_response(
                        message='You can only update your own schedules.',
                        message_type='error',
                        status_code=status.HTTP_403_FORBIDDEN
                    )
                if timezone.now() - schedule.created_at > timedelta(hours=7):
                    return api_response(
                        message='You can only update schedules within 7 hours of their creation.',
                        message_type='error',
                        status_code=status.HTTP_403_FORBIDDEN
                    )
            elif not request.user.is_admin:
                return api_response(
                    message='You do not have permission to update this schedule.',
                    message_type='error',
                    status_code=status.HTTP_403_FORBIDDEN
                )
            
            serializer = ClassScheduleSerializer(schedule, data=request.data, partial=True)
            if not serializer.is_valid():
                error_response = get_serializer_error_message(serializer.errors)
                return api_response(
                    message=error_response['message'],
                    message_type='error',
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            serializer.save()
            return api_response(
                message='Class schedule updated successfully.',
                message_type='success',
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )
        except ClassSchedule.DoesNotExist:
            return api_response(
                message='Class schedule not found.',
                message_type='error',
                status_code=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error updating class schedule: {str(e)}")
            return api_response(
                message='Failed to update schedule. Please try again.',
                message_type='error',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ClassSessionListView(APIView):
    """Lists all class sessions grouped by course and batch."""
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="List all courses with their batches and class sessions (admin: all courses; teacher: assigned courses; student: enrolled batches)",
        responses={
            200: openapi.Response(
                description="Class sessions retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description="Response message"),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'], description="Type of message"),
                        'data': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'course_name': openapi.Schema(type=openapi.TYPE_STRING, description="Course name"),
                                    'batches': openapi.Schema(
                                        type=openapi.TYPE_ARRAY,
                                        items=openapi.Schema(
                                            type=openapi.TYPE_OBJECT,
                                            properties={
                                                'batch_name': openapi.Schema(type=openapi.TYPE_STRING, description="Batch name"),
                                                'batch_start_date': openapi.Schema(type=openapi.TYPE_STRING, format='date', description="Batch start date"),
                                                'batch_end_date': openapi.Schema(type=openapi.TYPE_STRING, format='date', description="Batch end date"),
                                                'classes': openapi.Schema(
                                                    type=openapi.TYPE_ARRAY,
                                                    items=openapi.Schema(
                                                        type=openapi.TYPE_OBJECT,
                                                        properties={
                                                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                                            'session_date': openapi.Schema(type=openapi.TYPE_STRING, format='date'),
                                                            'start_time': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                                                            'end_time': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                                                            'recording_url': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                                            'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN)
                                                        }
                                                    ),
                                                    description="List of class sessions"
                                                )
                                            },
                                            description="Batch details"
                                        ),
                                        description="List of batches"
                                    )
                                },
                                description="Course with batches and sessions"
                            ),
                            description="List of courses with their batches and sessions"
                        )
                    }
                )
            ),
            403: openapi.Response(
                description="Permission denied",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description="Error message"),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'], description="Type of message")
                    }
                )
            ),
            500: openapi.Response(
                description="Server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description="Error message"),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'], description="Type of message")
                    }
                )
            )
        }
    )
    def get(self, request, *args, **kwargs):
        """Lists courses with their batches and class sessions based on user role."""
        try:
            if request.user.is_admin:
                courses = Course.objects.all()
            elif request.user.is_teacher:
                courses = Course.objects.filter(class_schedules__teacher=request.user).distinct()
            elif request.user.is_student:
                courses = Course.objects.filter(
                    enrollments__student=request.user,
                    enrollments__subscription__payment_status='completed'
                ).distinct()
            else:
                return api_response(
                    message='You do not have permission to access class sessions.',
                    message_type='error',
                    status_code=status.HTTP_403_FORBIDDEN
                )
            
            serializer = CourseSessionSerializer(courses, many=True, context={'request': request})
            return api_response(
                message='Class sessions retrieved successfully.',
                message_type='success',
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Error retrieving class sessions: {str(e)}")
            return api_response(
                message='Failed to retrieve sessions. Please try again.',
                message_type='error',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ClassSessionUpdateView(APIView):
    """Handles updating details for a specific class session."""
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Update class session details by class_id (admin: anytime, teacher: timings only ≥7 hours before start)",
        request_body=ClassSessionSerializer,
        responses={
            200: openapi.Response(
                description="Class session updated successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description="Response message"),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'], description="Type of message"),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_INTEGER, description="Session ID"),
                                'session_date': openapi.Schema(type=openapi.TYPE_STRING, format='date', description="Session date"),
                                'start_time': openapi.Schema(type=openapi.TYPE_STRING, format='date-time', description="Start time"),
                                'end_time': openapi.Schema(type=openapi.TYPE_STRING, format='date-time', description="End time"),
                                'recording_url': openapi.Schema(type=openapi.TYPE_STRING, nullable=True, description="Recording URL"),
                                'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Active status")
                            },
                            description="Updated class session"
                        )
                    }
                )
            ),
            400: openapi.Response(
                description="Invalid input or scheduling conflict",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description="Error message"),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'], description="Type of message")
                    }
                )
            ),
            403: openapi.Response(
                description="Permission denied",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description="Error message"),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'], description="Type of message")
                    }
                )
            ),
            404: openapi.Response(
                description="Class session not found",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description="Error message"),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'], description="Type of message")
                    }
                )
            ),
            500: openapi.Response(
                description="Server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description="Error message"),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'], description="Type of message")
                    }
                )
            )
        }
    )
    def patch(self, request, class_id=None, *args, **kwargs):
        """Updates specific fields of a class session.
        Accepts times like '02:00 PM' or ISO datetimes. Treats incoming times as local (settings.TIME_ZONE).
        """
        def parse_to_aware_datetime(value, session_date_for_combination):
            """
            Parse `value` that can be:
            - a 12-hour string like '02:00 PM' -> returns aware datetime in local tz combined with session_date
            - an ISO time '14:20' or '14:20:00' -> combine with session_date and localize
            - an ISO datetime '2025-09-16T14:20:00Z' -> returns aware datetime (UTC)
            - a full ISO datetime without Z (assume local tz)
            Raises ValueError for invalid formats.
            """
            # already a datetime
            if isinstance(value, datetime):
                dt = value
                if timezone.is_naive(dt):
                    return timezone.make_aware(dt, timezone.get_default_timezone())
                return dt

            s = str(value).strip()

            # Try 12-hour format e.g. '02:00 PM'
            try:
                t = datetime.strptime(s, '%I:%M %p').time()
                dt = datetime.combine(session_date_for_combination, t)
                return timezone.make_aware(dt, timezone.get_default_timezone())
            except Exception:
                pass

            # Try ISO datetime with trailing Z (UTC)
            try:
                if s.endswith('Z'):
                    dt = datetime.strptime(s, '%Y-%m-%dT%H:%M:%SZ')
                    return timezone.make_aware(dt, timezone.utc)
            except Exception:
                pass

            # Try full ISO datetime (may include offset)
            try:
                dt = datetime.fromisoformat(s)
                if dt.tzinfo is None:
                    return timezone.make_aware(dt, timezone.get_default_timezone())
                return dt
            except Exception:
                pass

            # Try 24h time like '14:20' or '14:20:00'
            for fmt in ('%H:%M:%S', '%H:%M'):
                try:
                    t = datetime.strptime(s, fmt).time()
                    dt = datetime.combine(session_date_for_combination, t)
                    return timezone.make_aware(dt, timezone.get_default_timezone())
                except Exception:
                    continue

            raise ValueError("Invalid time format. Use '02:00 PM', '14:20', or ISO datetime like '2025-09-16T14:20:00Z'.")

        try:
            session = ClassSession.objects.get(id=class_id)
            data = request.data.copy()

            # === Permission checks ===
            if request.user.is_teacher:
                if session.schedule.teacher != request.user:
                    return api_response(
                        message='You can only update your own class sessions.',
                        message_type='error',
                        status_code=status.HTTP_403_FORBIDDEN
                    )
                if timezone.now() - session.created_at > timedelta(hours=7):
                    return api_response(
                        message='You can only update sessions within 7 hours of their creation.',
                        message_type='error',
                        status_code=status.HTTP_403_FORBIDDEN
                    )
            elif not request.user.is_admin:
                return api_response(
                    message='You do not have permission to update this session.',
                    message_type='error',
                    status_code=status.HTTP_403_FORBIDDEN
                )

            # Detect if timing fields are being updated
            updating_timing = any(f in data for f in ['session_date', 'start_time', 'end_time'])

            # Determine session_date to use for combining with times
            if 'session_date' in data and data['session_date']:
                # expected 'YYYY-MM-DD'
                try:
                    session_date_obj = datetime.fromisoformat(str(data['session_date'])).date()
                except Exception:
                    return api_response(
                        message='Invalid session_date. Use YYYY-MM-DD.',
                        message_type='error',
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
            else:
                session_date_obj = session.session_date

            # If timing is updated, parse incoming start/end to aware datetimes (local tz)
            proposed_start_dt = None
            proposed_end_dt = None
            if updating_timing:
                # parse start_time (if provided) otherwise use existing session.start_time
                if 'start_time' in data and data['start_time']:
                    try:
                        proposed_start_dt = parse_to_aware_datetime(data['start_time'], session_date_obj)
                    except ValueError as e:
                        return api_response(
                            message=str(e),
                            message_type='error',
                            status_code=status.HTTP_400_BAD_REQUEST
                        )
                else:
                    proposed_start_dt = session.start_time

                # parse end_time (if provided) otherwise use existing session.end_time
                if 'end_time' in data and data['end_time']:
                    try:
                        proposed_end_dt = parse_to_aware_datetime(data['end_time'], session_date_obj)
                    except ValueError as e:
                        return api_response(
                            message=str(e),
                            message_type='error',
                            status_code=status.HTTP_400_BAD_REQUEST
                        )
                else:
                    proposed_end_dt = session.end_time

                # Normalize both to timezone-aware datetimes
                proposed_start_utc = proposed_start_dt.astimezone(timezone.utc)
                proposed_end_utc = proposed_end_dt.astimezone(timezone.utc)

                # Debug prints (preserved as part of original logic)
                print("DEBUG: parsed proposed_start (local tz):", proposed_start_dt)
                print("DEBUG: parsed proposed_start (UTC):", proposed_start_utc)
                print("DEBUG: parsed proposed_end (local tz):", proposed_end_dt)
                print("DEBUG: parsed proposed_end (UTC):", proposed_end_utc)
                print("DEBUG: server now (UTC):", timezone.now())

                # --- New Validation: Start time cannot be in the past ---
                now = timezone.now()
                if proposed_start_utc <= now:
                    return api_response(
                        message='You cannot create or update a class with a start time that has already passed.',
                        message_type='error',
                        status_code=status.HTTP_400_BAD_REQUEST
                    )

                # Teacher cutoff check (based on existing scheduled start time)
                if request.user.is_teacher:
                    cutoff_hours = getattr(settings, "SESSION_UPDATE_CUTOFF_HOURS", 7)
                    hours_until_existing = (session.start_time - now).total_seconds() / 3600
                    print("DEBUG: Teacher updating timing")
                    print("DEBUG: now:", now)
                    print("DEBUG: existing scheduled start (session.start_time):", session.start_time)
                    print("DEBUG: hours_until_existing:", hours_until_existing, "cutoff:", cutoff_hours)
                    if hours_until_existing < cutoff_hours:
                        return api_response(
                            message=f'Timing can only be updated at least {cutoff_hours} hours before the currently scheduled class start.',
                            message_type='error',
                            status_code=status.HTTP_403_FORBIDDEN
                        )

                # Put normalized ISO UTC strings back into `data` so serializer will parse them correctly
                data['start_time'] = proposed_start_utc.isoformat()
                data['end_time'] = proposed_end_utc.isoformat()
                data['session_date'] = session_date_obj.isoformat()

            # Run serializer validation
            serializer = ClassSessionSerializer(session, data=data, partial=True)
            if not serializer.is_valid():
                error_response = get_serializer_error_message(serializer.errors)
                return api_response(
                    message=error_response['message'],
                    message_type='error',
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            # Validate S3 URL if provided
            if 'recording_url' in data and data['recording_url']:
                s3_url = data['recording_url']
                if not s3_url.startswith('https://') or 's3' not in s3_url:
                    return api_response(
                        message='Invalid S3 URL format.',
                        message_type='error',
                        status_code=status.HTTP_400_BAD_REQUEST
                    )

            # Conflict validation: use serializer.validated_data (parsed datetimes) to set session for clean()
            if updating_timing:
                validated = serializer.validated_data
                session.session_date = validated.get('session_date', session.session_date)
                session.start_time = validated.get('start_time', session.start_time)
                session.end_time = validated.get('end_time', session.end_time)
                try:
                    session.clean()  # keeps your conflict and start<end checks
                except ValidationError as e:
                    # Format conflict error message
                    error_message = str(e)
                    if "already has a class" in error_message:
                        # Extract conflicting time from the error message
                        parts = error_message.split(' at ')[1].split(' on ')
                        time_range = parts[0].strip()
                        date = parts[1].split('.')[0].strip()
                        error_message = f"You already have a session scheduled from {time_range} on {date}."
                    elif "Start time must be before end time" in error_message:
                        error_message = "Start time must be before end time."
                    return api_response(
                        message=error_message,
                        message_type='error',
                        status_code=status.HTTP_400_BAD_REQUEST
                    )

            # Passed all checks — save
            serializer.save()
            return api_response(
                message='Class session updated successfully.',
                message_type='success',
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )

        except ClassSession.DoesNotExist:
            return api_response(
                message='Class session not found.',
                message_type='error',
                status_code=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error updating class session: {str(e)}")
            return api_response(
                message='Failed to update session. Please try again.',
                message_type='error',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )