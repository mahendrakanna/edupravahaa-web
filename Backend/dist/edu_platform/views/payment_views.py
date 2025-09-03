from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.utils import timezone
from rest_framework import serializers
from edu_platform.models import Course, CourseSubscription, CourseEnrollment
from edu_platform.permissions.auth_permissions import IsStudent
from edu_platform.serializers.payment_serializers import CreateOrderSerializer, VerifyPaymentSerializer
import razorpay
import logging

# Initialize Razorpay client
client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

# Set up logging
logger = logging.getLogger(__name__)

def get_error_message(serializer):
    """Extracts a specific error message from serializer errors."""
    errors = serializer.errors
    if 'non_field_errors' in errors:
        return errors['non_field_errors'][0]
    for field, error in errors.items():
        if isinstance(error, dict) and 'error' in error:
            return error['error']
        return error[0] if isinstance(error, list) else error
    return 'Invalid input data.'

class BaseAPIView(views.APIView):
    def validate_serializer(self, serializer_class, data, context=None):
        serializer = serializer_class(data=data, context=context or {'request': self.request})
        if not serializer.is_valid():
            raise serializers.ValidationError({
                'error': get_error_message(serializer),
                'status': status.HTTP_400_BAD_REQUEST
            })
        return serializer

class CreateOrderView(BaseAPIView):
    """Creates a Razorpay order for course purchase."""
    permission_classes = [IsAuthenticated, IsStudent]

    @swagger_auto_schema(
        request_body=CreateOrderSerializer,
        responses={
            200: openapi.Response(
                description="Order created successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'order_id': openapi.Schema(type=openapi.TYPE_STRING),
                                'amount': openapi.Schema(type=openapi.TYPE_NUMBER),
                                'currency': openapi.Schema(type=openapi.TYPE_STRING),
                                'key': openapi.Schema(type=openapi.TYPE_STRING),
                                'subscription_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'batch': openapi.Schema(type=openapi.TYPE_STRING)
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
    def post(self, request):
        """Generates Razorpay order and creates/updates subscription and enrollment."""
        try:
            serializer = self.validate_serializer(CreateOrderSerializer, request.data)
            course_id = serializer.validated_data['course_id']
            batch = serializer.validated_data['batch']
            course = Course.objects.get(id=course_id, is_active=True)

            # Check for existing pending subscription
            try:
                subscription = CourseSubscription.objects.get(
                    student=request.user,
                    course=course,
                    payment_status='pending'
                )
                logger.info(f"Reusing existing pending subscription {subscription.id} for user {request.user.id}, course {course.id}")
            except CourseSubscription.DoesNotExist:
                subscription = None

            # Create Razorpay order
            amount = int(course.base_price * 100)
            order_data = {
                'amount': amount,
                'currency': 'INR',
                'payment_capture': '1',
                'notes': {
                    'course_id': str(course.id),
                    'student_id': str(request.user.id),
                    'student_email': request.user.email,
                    'batch': batch
                }
            }
            order = client.order.create(data=order_data)

            # Update or create subscription
            if subscription:
                subscription.order_id = order['id']
                subscription.purchased_at = timezone.now()
                subscription.save(update_fields=['order_id', 'purchased_at'])
                logger.info(f"Updated subscription {subscription.id} with new order_id {order['id']}")
            else:
                subscription = CourseSubscription.objects.create(
                    student=request.user,
                    course=course,
                    amount_paid=course.base_price,
                    order_id=order['id'],
                    payment_method='razorpay',
                    payment_status='pending',
                    currency='INR'
                )
                logger.info(f"Created new subscription {subscription.id} for user {request.user.id}, course {course.id}")

            try:
                enrollment = CourseEnrollment.objects.get(
                    student=request.user,
                    course=course,
                    subscription=subscription
                )
                enrollment.batch = batch
                enrollment.save(update_fields=['batch'])
                logger.info(f"Updated enrollment for subscription {subscription.id} with batch {batch}")
            except CourseEnrollment.DoesNotExist:
                enrollment = CourseEnrollment.objects.create(
                    student=request.user,
                    course=course,
                    batch=batch,
                    subscription=subscription
                )
                logger.info(f"Created new enrollment for subscription {subscription.id} with batch {batch}")

            return Response({
                'message': 'Order created successfully.',
                'data': {
                    'order_id': order['id'],
                    'amount': order['amount'],
                    'currency': order['currency'],
                    'key': settings.RAZORPAY_KEY_ID,
                    'subscription_id': subscription.id,
                    'batch': batch
                }
            }, status=status.HTTP_200_OK)

        except serializers.ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Course.DoesNotExist:
            return Response({
                'error': 'Course not found or inactive.',
                'status': status.HTTP_400_BAD_REQUEST
            }, status=status.HTTP_400_BAD_REQUEST)
        except razorpay.errors.BadRequestError as e:
            logger.error(f"Razorpay error creating order: {str(e)}")
            return Response({
                'error': f'Payment gateway error: {str(e)}',
                'status': status.HTTP_400_BAD_REQUEST
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Unexpected error creating order: {str(e)}")
            return Response({
                'error': 'Failed to create order. Please try again.',
                'status': status.HTTP_500_INTERNAL_SERVER_ERROR
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class VerifyPaymentView(BaseAPIView):
    """Verifies Razorpay payment and updates subscription and enrollment."""
    permission_classes = [IsAuthenticated, IsStudent]

    @swagger_auto_schema(
        request_body=VerifyPaymentSerializer,
        responses={
            200: openapi.Response(
                description="Payment verified successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'subscription_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'course_name': openapi.Schema(type=openapi.TYPE_STRING),
                                'batch': openapi.Schema(type=openapi.TYPE_STRING)
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
    def post(self, request):
        """Verifies payment signature and updates subscription and enrollment status."""
        try:
            serializer = self.validate_serializer(VerifyPaymentSerializer, request.data)
            payment_id = serializer.validated_data['razorpay_payment_id']
            order_id = serializer.validated_data['razorpay_order_id']
            signature = serializer.validated_data['razorpay_signature']
            subscription = serializer.validated_data['subscription']

            # Handle idempotency for completed payments
            if subscription.payment_status == 'completed':
                enrollment = CourseEnrollment.objects.get(subscription=subscription)
                logger.info(f"Payment already verified for subscription {subscription.id}, user {request.user.id}")
                return Response({
                    'message': 'Payment already verified.',
                    'data': {
                        'subscription_id': subscription.id,
                        'course_name': subscription.course.name,
                        'batch': enrollment.batch
                    }
                }, status=status.HTTP_200_OK)

            # Verify payment signature
            params_dict = {
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            }

            if settings.DEBUG and settings.RAZORPAY_KEY_SECRET == 'fake_secret_for_testing':
                logger.info(f"Skipping signature verification for subscription {subscription.id} in test mode")
            else:
                try:
                    client.utility.verify_payment_signature(params_dict)
                except razorpay.errors.SignatureVerificationError as e:
                    logger.error(f"Signature verification failed for subscription {subscription.id}, user {request.user.id}: {str(e)}")
                    subscription.payment_status = 'failed'
                    subscription.save()
                    return Response({
                        'error': 'Invalid payment signature.',
                        'status': status.HTTP_400_BAD_REQUEST
                    }, status=status.HTTP_400_BAD_REQUEST)

            # Update subscription details
            subscription.payment_id = payment_id
            subscription.payment_status = 'completed'
            subscription.payment_response = params_dict
            subscription.payment_completed_at = timezone.now()
            subscription.save()
            
            enrollment = CourseEnrollment.objects.get(subscription=subscription)
            
            logger.info(f"Payment verified for subscription {subscription.id}, user {request.user.id}, course {subscription.course.name}, batch {enrollment.batch}")
            return Response({
                'message': 'Payment verified successfully.',
                'data': {
                    'subscription_id': subscription.id,
                    'course_name': subscription.course.name,
                    'batch': enrollment.batch
                }
            }, status=status.HTTP_200_OK)

        except serializers.ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except CourseEnrollment.DoesNotExist:
            logger.error(f"No enrollment found for subscription {subscription.id if 'subscription' in locals() else 'unknown'}")
            return Response({
                'error': 'No enrollment found for this subscription.',
                'status': status.HTTP_400_BAD_REQUEST
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error updating subscription {subscription.id if 'subscription' in locals() else 'unknown'} for user {request.user.id}: {str(e)}")
            return Response({
                'error': 'Failed to verify payment. Please try again.',
                'status': status.HTTP_500_INTERNAL_SERVER_ERROR
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)