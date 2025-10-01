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

def api_response(message, message_type, data=None, status_code=200):
    """Standardizes API response structure."""
    response_data = {
        'message': message,
        'message_type': message_type
    }
    if data is not None:
        response_data['data'] = data
    return Response(response_data, status=status_code)

def get_error_message(serializer):
    """Extracts a specific, field-aware error message from serializer errors."""
    errors = serializer.errors
    if 'non_field_errors' in errors:
        return errors['non_field_errors'][0]
    for field, error in errors.items():
        if isinstance(error, dict) and 'error' in error:
            return error['error']
        error_msg = error[0] if isinstance(error, list) else str(error)
        field_name = field.replace('_', ' ').title()
        if error_msg == 'This field is required.':
            return f"{field_name} is required."
        if error_msg == 'This field may not be blank.':
            return f"{field_name} cannot be empty."
        return error_msg
    return 'Invalid input data provided.'

class BaseAPIView(views.APIView):
    def validate_serializer(self, serializer_class, data, context=None):
        serializer = serializer_class(data=data, context=context or {'request': self.request})
        if not serializer.is_valid():
            error_msg = get_error_message(serializer)
            return api_response(
                message=error_msg,
                message_type='error',
                status_code=status.HTTP_400_BAD_REQUEST
            )
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
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error']),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'order_id': openapi.Schema(type=openapi.TYPE_STRING, description="Razorpay order ID"),
                                'amount': openapi.Schema(type=openapi.TYPE_NUMBER, description="Order amount in paise"),
                                'currency': openapi.Schema(type=openapi.TYPE_STRING, description="Currency code (e.g., INR)"),
                                'key': openapi.Schema(type=openapi.TYPE_STRING, description="Razorpay key ID"),
                                'subscription_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="Subscription ID"),
                                'batch': openapi.Schema(type=openapi.TYPE_STRING, description="Selected batch"),
                                'start_date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
                                'end_date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
                                'start_time': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                'end_time': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                'saturday_start_time': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME, nullable=True),
                                'saturday_end_time': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME, nullable=True),
                                'sunday_start_time': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME, nullable=True),
                                'sunday_end_time': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME, nullable=True)
                            }
                        )
                    }
                )
            ),
            400: openapi.Response(description="Invalid input"),
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="Forbidden"),
            500: openapi.Response(description="Server error")
        }
    )
    def post(self, request):
        """Generates Razorpay order and creates/updates subscription and enrollment."""
        try:
            serializer = self.validate_serializer(CreateOrderSerializer, request.data)
            if isinstance(serializer, Response):
                return serializer 
            
            course_id = serializer.validated_data['course_id']
            batch = serializer.validated_data['batch']
            start_date = serializer.validated_data['start_date']
            end_date = serializer.validated_data['end_date']
            start_time = serializer.validated_data.get('start_time')
            end_time = serializer.validated_data.get('end_time')
            saturday_start_time = serializer.validated_data.get('saturday_start_time')
            saturday_end_time = serializer.validated_data.get('saturday_end_time')
            sunday_start_time = serializer.validated_data.get('sunday_start_time')
            sunday_end_time = serializer.validated_data.get('sunday_end_time')
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
                    'batch': batch,
                    'start_date': str(start_date),
                    'end_date': str(end_date),
                    'start_time': str(start_time) if start_time else '',
                    'end_time': str(end_time) if end_time else '',
                    'saturday_start_time': str(saturday_start_time) if saturday_start_time else '',
                    'saturday_end_time': str(saturday_end_time) if saturday_end_time else '',
                    'sunday_start_time': str(sunday_start_time) if sunday_start_time else '',
                    'sunday_end_time': str(sunday_end_time) if sunday_end_time else ''
                }
            }
            order = client.order.create(data=order_data)

            # Update or create subscription
            if subscription:
                subscription.order_id = order['id']
                subscription.batch = batch
                subscription.start_date = start_date
                subscription.end_date = end_date
                subscription.start_time = start_time
                subscription.end_time = end_time
                subscription.saturday_start_time = saturday_start_time
                subscription.saturday_end_time = saturday_end_time
                subscription.sunday_start_time = sunday_start_time
                subscription.sunday_end_time = sunday_end_time
                subscription.purchased_at = timezone.now()
                subscription.save(update_fields=[
                    'order_id', 'batch', 'start_date', 'end_date', 'start_time', 'end_time',
                    'saturday_start_time', 'saturday_end_time', 'sunday_start_time', 'sunday_end_time', 'purchased_at'
                ])
                logger.info(f"Updated subscription {subscription.id} with new order_id {order['id']}")
            else:
                subscription = CourseSubscription.objects.create(
                    student=request.user,
                    course=course,
                    batch=batch,
                    start_date=start_date,
                    end_date=end_date,
                    start_time=start_time,
                    end_time=end_time,
                    saturday_start_time=saturday_start_time,
                    saturday_end_time=saturday_end_time,
                    sunday_start_time=sunday_start_time,
                    sunday_end_time=sunday_end_time,
                    amount_paid=course.base_price,
                    order_id=order['id'],
                    payment_method='razorpay',
                    payment_status='pending',
                    currency='INR'
                )
                logger.info(f"Created new subscription {subscription.id} for user {request.user.id}, course {course.id}")

            # Update or create enrollment
            try:
                enrollment = CourseEnrollment.objects.get(
                    student=request.user,
                    course=course,
                    subscription=subscription
                )
                enrollment.batch = batch
                enrollment.start_date = start_date
                enrollment.end_date = end_date
                enrollment.start_time = start_time
                enrollment.end_time = end_time
                enrollment.saturday_start_time = saturday_start_time
                enrollment.saturday_end_time = saturday_end_time
                enrollment.sunday_start_time = sunday_start_time
                enrollment.sunday_end_time = sunday_end_time
                enrollment.save(update_fields=[
                    'batch', 'start_date', 'end_date', 'start_time', 'end_time',
                    'saturday_start_time', 'saturday_end_time', 'sunday_start_time', 'sunday_end_time'
                ])
                logger.info(f"Updated enrollment for subscription {subscription.id} with batch {batch}")
            except CourseEnrollment.DoesNotExist:
                enrollment = CourseEnrollment.objects.create(
                    student=request.user,
                    course=course,
                    batch=batch,
                    start_date=start_date,
                    end_date=end_date,
                    start_time=start_time,
                    end_time=end_time,
                    saturday_start_time=saturday_start_time,
                    saturday_end_time=saturday_end_time,
                    sunday_start_time=sunday_start_time,
                    sunday_end_time=sunday_end_time,
                    subscription=subscription
                )
                logger.info(f"Created new enrollment for subscription {subscription.id} with batch {batch}")

            return api_response(
                message='Order created successfully.',
                message_type='success',
                data={
                    'order_id': order['id'],
                    'amount': order['amount'],
                    'currency': order['currency'],
                    'key': settings.RAZORPAY_KEY_ID,
                    'subscription_id': subscription.id,
                    'batch': batch,
                    'start_date': str(start_date),
                    'end_date': str(end_date),
                    'start_time': str(start_time) if start_time else None,
                    'end_time': str(end_time) if end_time else None,
                    'saturday_start_time': str(saturday_start_time) if saturday_start_time else None,
                    'saturday_end_time': str(saturday_end_time) if saturday_end_time else None,
                    'sunday_start_time': str(sunday_start_time) if sunday_start_time else None,
                    'sunday_end_time': str(sunday_end_time) if sunday_end_time else None
                },
                status_code=status.HTTP_200_OK
            )

        except serializers.ValidationError as e:
            return api_response(
                message=get_error_message(e),
                message_type='error',
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Course.DoesNotExist:
            return api_response(
                message='The selected course does not exist or is not active.',
                message_type='error',
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except razorpay.errors.BadRequestError as e:
            logger.error(f"Razorpay error creating order: {str(e)}")
            return api_response(
                message='Payment gateway error. Please try again or contact support.',
                message_type='error',
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Unexpected error creating order: {str(e)}")
            return api_response(
                message='Failed to create order. Please try again later.',
                message_type='error',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error']),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'subscription_id': openapi.Schema(type=openapi.TYPE_INTEGER, description="Subscription ID"),
                                'course_name': openapi.Schema(type=openapi.TYPE_STRING, description="Course name"),
                                'batch': openapi.Schema(type=openapi.TYPE_STRING, description="Selected batch"),
                                'start_date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
                                'end_date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
                                'start_time': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME, nullable=True),
                                'end_time': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME, nullable=True),
                                'saturday_start_time': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME, nullable=True),
                                'saturday_end_time': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME, nullable=True),
                                'sunday_start_time': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME, nullable=True),
                                'sunday_end_time': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME, nullable=True)
                            }
                        )
                    }
                )
            ),
            400: openapi.Response(description="Invalid input"),
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="Forbidden"),
            500: openapi.Response(description="Server error")
        }
    )
    def post(self, request):
        """Verifies payment signature and updates subscription and enrollment status."""
        try:
            serializer = self.validate_serializer(VerifyPaymentSerializer, request.data)
            if isinstance(serializer, Response):
                return serializer
            
            payment_id = serializer.validated_data['razorpay_payment_id']
            order_id = serializer.validated_data['razorpay_order_id']
            signature = serializer.validated_data['razorpay_signature']
            subscription = serializer.validated_data['subscription']

            # Handle idempotency for completed payments
            if subscription.payment_status == 'completed':
                enrollment = CourseEnrollment.objects.get(subscription=subscription)
                logger.info(f"Payment already verified for subscription {subscription.id}, user {request.user.id}")
                return api_response(
                    message='Payment has already been verified.',
                    message_type='success',
                    data={
                        'subscription_id': subscription.id,
                        'course_name': subscription.course.name,
                        'batch': enrollment.batch,
                        'start_date': str(enrollment.start_date),
                        'end_date': str(enrollment.end_date),
                        'start_time': str(enrollment.start_time) if enrollment.start_time else None,
                        'end_time': str(enrollment.end_time) if enrollment.end_time else None,
                        'saturday_start_time': str(enrollment.saturday_start_time) if enrollment.saturday_start_time else None,
                        'saturday_end_time': str(enrollment.saturday_end_time) if enrollment.saturday_end_time else None,
                        'sunday_start_time': str(enrollment.sunday_start_time) if enrollment.sunday_start_time else None,
                        'sunday_end_time': str(enrollment.sunday_end_time) if enrollment.sunday_end_time else None
                    },
                    status_code=status.HTTP_200_OK
                )

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
                    return api_response(
                        message='Invalid payment signature. Please try again.',
                        message_type='error',
                        status_code=status.HTTP_400_BAD_REQUEST
                    )

            # Update subscription details
            subscription.payment_id = payment_id
            subscription.payment_status = 'completed'
            subscription.payment_response = params_dict
            subscription.payment_completed_at = timezone.now()
            subscription.save()

            # ✅ Update user (make is_trial = False and has_purchased = True)
            user = request.user
            if user.role == 'student':
                user.has_purchased_courses = True
                user.trial_end_date = None  # optional: disable trial immediately
                user.save(update_fields=['has_purchased_courses', 'trial_end_date'])
                user.save(update_fields=['has_purchased_courses', 'trial_end_date'])
            
            enrollment = CourseEnrollment.objects.get(subscription=subscription)

            # ✅ Store the final price student paid
            latest_pricing = subscription.course.pricings.first()
            if latest_pricing:
                enrollment.price = latest_pricing.final_price

            enrollment.save(update_fields=['price'])
            
            logger.info(f"Payment verified for subscription {subscription.id}, user {request.user.id}, course {subscription.course.name}, batch {enrollment.batch}")
            return api_response(
                message='Payment verified successfully.',
                message_type='success',
                data={
                    'subscription_id': subscription.id,
                    'course_name': subscription.course.name,
                    'batch': enrollment.batch,
                    'start_date': str(enrollment.start_date),
                    'end_date': str(enrollment.end_date),
                    'start_time': str(enrollment.start_time) if enrollment.start_time else None,
                    'end_time': str(enrollment.end_time) if enrollment.end_time else None,
                    'saturday_start_time': str(enrollment.saturday_start_time) if enrollment.saturday_start_time else None,
                    'saturday_end_time': str(enrollment.saturday_end_time) if enrollment.saturday_end_time else None,
                    'sunday_start_time': str(enrollment.sunday_start_time) if enrollment.sunday_start_time else None,
                    'sunday_end_time': str(enrollment.sunday_end_time) if enrollment.sunday_end_time else None
                },
                status_code=status.HTTP_200_OK
            )

        except serializers.ValidationError as e:
            return api_response(
                message=get_error_message(e),
                message_type='error',
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except CourseEnrollment.DoesNotExist:
            logger.error(f"No enrollment found for subscription {subscription.id if 'subscription' in locals() else 'unknown'}")
            return api_response(
                message='No enrollment found for this subscription. Please contact support.',
                message_type='error',
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error updating subscription {subscription.id if 'subscription' in locals() else 'unknown'} for user {request.user.id}: {str(e)}")
            return api_response(
                message='Failed to verify payment. Please try again later.',
                message_type='error',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )