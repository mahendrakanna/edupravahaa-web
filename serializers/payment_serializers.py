from rest_framework import serializers
from edu_platform.models import Course, CourseSubscription


class CreateOrderSerializer(serializers.Serializer):
    """Validates course purchase order creation."""
    course_id = serializers.IntegerField()

    def validate_course_id(self, value):
        """Ensures course exists and is active."""
        # Check if course exists and is active
        try:
            course = Course.objects.get(id=value, is_active=True)
        except Course.DoesNotExist:
            raise serializers.ValidationError("Course not found or inactive")
        
        # Check for existing completed subscription
        if CourseSubscription.objects.filter(
            student=self.context['request'].user,
            course=course,
            payment_status='completed'
        ).exists():
            raise serializers.ValidationError("Already subscribed to this course")
        
        return value

    def validate(self, attrs):
        """Ensures user is verified before creating order."""
        # Check user verification status
        if not self.context['request'].user.is_verified:
            errors = []
            if not self.context['request'].user.email_verified:
                errors.append("Email not verified")
            if not self.context['request'].user.phone_verified:
                errors.append("Phone not verified")
            raise serializers.ValidationError(errors)
        
        return attrs


class VerifyPaymentSerializer(serializers.Serializer):
    """Validates payment verification data."""
    razorpay_order_id = serializers.CharField()
    razorpay_payment_id = serializers.CharField()
    razorpay_signature = serializers.CharField()
    subscription_id = serializers.IntegerField()

    def validate(self, attrs):
        """Ensures subscription exists and is pending."""
        # Verify subscription details
        try:
            subscription = CourseSubscription.objects.get(
                id=attrs['subscription_id'],
                order_id=attrs['razorpay_order_id'],
                student=self.context['request'].user,
                payment_status='pending'
            )
        except CourseSubscription.DoesNotExist:
            raise serializers.ValidationError("Subscription not found or already processed")
        
        attrs['subscription'] = subscription
        return attrs