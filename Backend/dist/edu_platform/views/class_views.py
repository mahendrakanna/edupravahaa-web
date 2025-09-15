from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.utils import timezone
from datetime import timedelta
from edu_platform.permissions.auth_permissions import IsAdmin, IsTeacher
from edu_platform.models import User, ClassSchedule, ClassSession
from edu_platform.serializers.class_serializers import ClassScheduleSerializer, ClassSessionSerializer
from botocore.exceptions import ClientError
from django.db.models import Q
import boto3
import logging

logger = logging.getLogger(__name__)

class ClassScheduleView(APIView):
    """Manages retrieval, creation, and updates of ClassSchedule objects."""
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="List all class schedules (admin) or teacher's own schedules",
        responses={
            200: openapi.Response(
                description="List of class schedules",
                schema=ClassScheduleSerializer(many=True)
            ),
            403: openapi.Response(
                description="Permission denied",
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
        """Lists all class schedules for admins or teacher's own schedules."""
        try:
            if request.user.is_admin:
                schedules = ClassSchedule.objects.all()
            else:
                if not request.user.is_teacher:
                    return Response({
                        'error': 'Only admins or teachers can access class schedules.',
                        'status': status.HTTP_403_FORBIDDEN
                    }, status=status.HTTP_403_FORBIDDEN)
                schedules = ClassSchedule.objects.filter(teacher=request.user)
            
            serializer = ClassScheduleSerializer(schedules, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error retrieving class schedules: {str(e)}")
            return Response({
                'error': f'Failed to retrieve schedules: {str(e)}',
                'status': status.HTTP_500_INTERNAL_SERVER_ERROR
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        operation_description="Create a class schedule with sessions (admin only for batch assignments, admin/teacher for single batch)",
        request_body=ClassScheduleSerializer,
        responses={
            201: openapi.Response(
                description="Class schedule created",
                schema=ClassScheduleSerializer
            ),
            400: openapi.Response(
                description="Invalid input or conflict",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                        'details': openapi.Schema(type=openapi.TYPE_OBJECT),
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER)
                    }
                )
            ),
            403: openapi.Response(
                description="Permission denied",
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
        """Creates a class schedule with sessions."""
        try:
            # Restrict batch assignments to admins only
            if 'batch_assignment' in request.data and not request.user.is_admin:
                return Response({
                    'error': 'Only admins can create multiple batch assignments.',
                    'status': status.HTTP_403_FORBIDDEN
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Restrict single batch creation to admins or the teacher themselves
            if not (request.user.is_admin or request.user.is_teacher):
                return Response({
                    'error': 'You do not have permission to create schedules.',
                    'status': status.HTTP_403_FORBIDDEN
                }, status=status.HTTP_403_FORBIDDEN)
            
            serializer = ClassScheduleSerializer(data=request.data, context={'request': request})
            if not serializer.is_valid():
                logger.error(f"Class schedule creation validation error: {serializer.errors}")
                return Response({
                    'error': 'Validation failed.',
                    'details': serializer.errors,
                    'status': status.HTTP_400_BAD_REQUEST
                }, status=status.HTTP_400_BAD_REQUEST)
            
            result = serializer.save()
            if isinstance(result, dict):
                return Response({
                    'message': 'Batch assignment created successfully.',
                    'data': [ClassScheduleSerializer(s).data for s in result['schedules']]
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    'message': 'Schedule created successfully.',
                    'data': ClassScheduleSerializer(result).data
                }, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error creating class schedule: {str(e)}")
            return Response({
                'error': f'Failed to create schedule: {str(e)}',
                'status': status.HTTP_500_INTERNAL_SERVER_ERROR
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        operation_description="Update a class schedule and sessions by ID (teacher within 1 hour or admin)",
        request_body=ClassScheduleSerializer,
        responses={
            200: openapi.Response(
                description="Updated class schedule",
                schema=ClassScheduleSerializer
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
            403: openapi.Response(
                description="Permission denied",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER)
                    }
                )
            ),
            404: openapi.Response(
                description="Schedule not found",
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
    def put(self, request, schedule_id=None, *args, **kwargs):
        """Updates a specific class schedule and its sessions."""
        try:
            schedule = ClassSchedule.objects.get(id=schedule_id)
            if request.user.is_teacher:
                if schedule.teacher != request.user:
                    return Response({
                        'error': 'You can only update your own schedules.',
                        'status': status.HTTP_403_FORBIDDEN
                    }, status=status.HTTP_403_FORBIDDEN)

                if timezone.now() - schedule.created_at > timedelta(hours=1):
                    return Response({
                        'error': 'You can only update schedules within 1 hour of their creation.',
                        'status': status.HTTP_403_FORBIDDEN
                    }, status=status.HTTP_403_FORBIDDEN)
            elif not request.user.is_admin:
                return Response({
                    'error': 'You do not have permission to update this schedule.',
                    'status': status.HTTP_403_FORBIDDEN
                }, status=status.HTTP_403_FORBIDDEN)
            
            serializer = ClassScheduleSerializer(schedule, data=request.data, partial=True)
            if not serializer.is_valid():
                error_message = list(serializer.errors.values())[0][0] if isinstance(list(serializer.errors.values())[0], list) else list(serializer.errors.values())[0]
                logger.error(f"Class schedule update validation error: {error_message}")
                return Response({
                    'error': error_message,
                    'status': status.HTTP_400_BAD_REQUEST
                }, status=status.HTTP_400_BAD_REQUEST)
            
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ClassSchedule.DoesNotExist:
            return Response({
                'error': 'Class schedule not found.',
                'status': status.HTTP_404_NOT_FOUND
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error updating class schedule: {str(e)}")
            return Response({
                'error': f'Failed to update schedule: {str(e)}',
                'status': status.HTTP_500_INTERNAL_SERVER_ERROR
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ClassSessionRecordingView(APIView):
    """Handles updating the recording URL for a ClassSession."""
    permission_classes = [IsAuthenticated, IsTeacher]

    @swagger_auto_schema(
        operation_description="Update recording URL for a class session (teacher only)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'recording_url': openapi.Schema(type=openapi.TYPE_STRING, description='S3 URL of the recording')
            },
            required=['recording_url']
        ),
        responses={
            200: openapi.Response(
                description="Recording URL updated",
                schema=ClassSessionSerializer
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
            403: openapi.Response(
                description="Permission denied",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER)
                    }
                )
            ),
            404: openapi.Response(
                description="Class session not found",
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
    def patch(self, request, class_id=None):
        """Updates the recording URL for a specific class session."""
        try:
            session = ClassSession.objects.get(class_id=class_id)
            if session.schedule.teacher != request.user:
                return Response({
                    'error': 'You can only update recordings for your own classes.',
                    'status': status.HTTP_403_FORBIDDEN
                }, status=status.HTTP_403_FORBIDDEN)
            
            serializer = ClassSessionSerializer(session, data={'recording_url': request.data.get('recording_url')}, partial=True)
            if not serializer.is_valid():
                error_message = list(serializer.errors.values())[0][0] if isinstance(list(serializer.errors.values())[0], list) else list(serializer.errors.values())[0]
                logger.error(f"Recording update validation error: {error_message}")
                return Response({
                    'error': error_message,
                    'status': status.HTTP_400_BAD_REQUEST
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate S3 URL (basic check, adjust based on your S3 configuration)
            s3_url = request.data.get('recording_url')
            if not s3_url.startswith('https://') or 's3' not in s3_url:
                return Response({
                    'error': 'Invalid S3 URL format.',
                    'status': status.HTTP_400_BAD_REQUEST
                }, status=status.HTTP_400_BAD_REQUEST)
            
            serializer.save()
            return Response({
                'message': 'Recording URL updated successfully.',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        except ClassSession.DoesNotExist:
            return Response({
                'error': 'Class session not found.',
                'status': status.HTTP_404_NOT_FOUND
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error updating recording URL: {str(e)}")
            return Response({
                'error': f'Failed to update recording URL: {str(e)}',
                'status': status.HTTP_500_INTERNAL_SERVER_ERROR
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)