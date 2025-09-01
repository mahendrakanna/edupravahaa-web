from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from edu_platform.models import CourseEnrollment
from edu_platform.serializers.enrollment_serializers import CourseEnrollmentSerializer
from edu_platform.permissions.auth_permissions import IsStudent
import logging

logger = logging.getLogger(__name__)

class UpdateEnrollmentView(views.APIView):
    """Allows students to update their batch selection for a course."""
    permission_classes = [IsAuthenticated, IsStudent]

    @swagger_auto_schema(
        request_body=CourseEnrollmentSerializer,
        responses={
            200: openapi.Response(
                description="Enrollment updated successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'course': openapi.Schema(type=openapi.TYPE_STRING),
                                'batch': openapi.Schema(type=openapi.TYPE_STRING),
                                'enrolled_at': openapi.Schema(type=openapi.TYPE_STRING, format='date-time')
                            }
                        )
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
            404: openapi.Response(
                description="Enrollment not found",
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
    def patch(self, request, subscription_id=None):
        """Updates the batch for a specific enrollment."""
        try:
            enrollment = CourseEnrollment.objects.get(
                subscription_id=subscription_id,
                student=request.user,
                subscription__is_active=True
            )
            serializer = CourseEnrollmentSerializer(enrollment, data=request.data, partial=True, context={'request': request})
            if not serializer.is_valid():
                error_message = list(serializer.errors.values())[0][0] if isinstance(list(serializer.errors.values())[0], list) else list(serializer.errors.values())[0]
                logger.error(f"Enrollment update validation error: {error_message}")
                return Response({
                    'error': error_message,
                    'status': status.HTTP_400_BAD_REQUEST
                }, status=status.HTTP_400_BAD_REQUEST)
            
            serializer.save()
            return Response({
                'message': 'Enrollment updated successfully.',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        except CourseEnrollment.DoesNotExist:
            return Response({
                'error': 'Enrollment not found or subscription is inactive.',
                'status': status.HTTP_404_NOT_FOUND
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error updating enrollment: {str(e)}")
            return Response({
                'error': f'Failed to update enrollment: {str(e)}',
                'status': status.HTTP_500_INTERNAL_SERVER_ERROR
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)





            