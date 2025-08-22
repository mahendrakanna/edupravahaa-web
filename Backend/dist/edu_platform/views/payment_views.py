from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.utils import timezone
from edu_platform.models import Course, CourseSubscription
from edu_platform.permissions.auth_permissions import IsStudent
from edu_platform.serializers.payment_serializers import CreateOrderSerializer, VerifyPaymentSerializer
import razorpay
import logging

# Initialize Razorpay client
client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

# Set up logging
logger = logging.getLogger(__name__)

class CreateOrderView(views.APIView):
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
                        'order_id': openapi.Schema(type=openapi.TYPE_STRING),
                        'amount': openapi.Schema(type=openapi.TYPE_NUMBER),
                        'currency': openapi.Schema(type=openapi.TYPE_STRING),
                        'key': openapi.Schema(type=openapi.TYPE_STRING),
                        'subscription_id': openapi.Schema(type=openapi.TYPE_INTEGER)
                    }
                )
            ),
            400: "Bad Request",
            403: "Forbidden",
            404: "Course Not Found"
        }
    )
    def post(self, request):
        """Generates Razorpay order and creates/updates subscription."""
        # Validate request data
        serializer = CreateOrderSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        course_id = serializer.validated_data['course_id']
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
        try:
            order_data = {
                'amount': amount,
                'currency': 'INR',
                'payment_capture': '1',
                'notes': {
                    'course_id': str(course.id),
                    'student_id': str(request.user.id),
                    'student_email': request.user.email
                }
            }
            order = client.order.create(data=order_data)
            
            # Update or create subscription
            if subscription:
                # Update existing subscription with new order_id
                subscription.order_id = order['id']
                subscription.purchased_at = timezone.now()
                subscription.save(update_fields=['order_id', 'purchased_at'])
                logger.info(f"Updated subscription {subscription.id} with new order_id {order['id']}")
            else:
                # Create new subscription
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
            
            return Response({
                'order_id': order['id'],
                'amount': order['amount'],
                'currency': order['currency'],
                'key': settings.RAZORPAY_KEY_ID,
                'subscription_id': subscription.id
            }, status=status.HTTP_200_OK)
            
        except razorpay.errors.BadRequestError as e:
            logger.error(f"Razorpay error creating order: {str(e)}")
            return Response({"error": f"Payment gateway error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception(f"Unexpected error creating order: {str(e)}")
            return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class VerifyPaymentView(views.APIView):
    """Verifies Razorpay payment and updates subscription."""
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
                        'subscription_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'course_name': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            400: "Bad Request",
            404: "Subscription Not Found"
        }
    )
    
    def post(self, request):
        """Verifies payment signature and updates subscription status."""
        # Validate request data
        serializer = VerifyPaymentSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        payment_id = serializer.validated_data['razorpay_payment_id']
        order_id = serializer.validated_data['razorpay_order_id']
        signature = serializer.validated_data['razorpay_signature']
        subscription = serializer.validated_data['subscription']
        
        # Handle idempotency for completed payments
        if subscription.payment_status == 'completed':
            logger.info(f"Payment already verified for subscription {subscription.id}, user {request.user.id}")
            return Response({
                "message": "Payment already verified",
                "subscription_id": subscription.id,
                "course_name": subscription.course.name
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
                return Response({"error": "Invalid payment signature"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Update subscription details
        try:
            subscription.payment_id = payment_id
            subscription.payment_status = 'completed'
            subscription.payment_response = params_dict
            subscription.payment_completed_at = timezone.now()
            subscription.save()
            
            logger.info(f"Payment verified for subscription {subscription.id}, user {request.user.id}, course {subscription.course.name}")
            return Response({
                "message": "Payment verified successfully",
                "subscription_id": subscription.id,
                "course_name": subscription.course.name
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.exception(f"Error updating subscription {subscription.id} for user {request.user.id}: {str(e)}")
            return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)