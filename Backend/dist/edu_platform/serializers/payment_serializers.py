from rest_framework import serializers
from edu_platform.models import Course, CourseSubscription, ClassSchedule


def validate_batch_for_course(value, course):
    """Shared utility to validate batch availability for a course."""
    schedules = ClassSchedule.objects.filter(course=course)
    if not schedules.exists():
        raise serializers.ValidationError({
            'error': f"No schedules are available for the course '{course.name}'. Please contact support."
        })
    available_batches = set(schedule.batch for schedule in schedules)
    if value not in available_batches:
        raise serializers.ValidationError({
            'error': f"The batch '{value}' is not available for the course '{course.name}'. Available batches are: {', '.join(available_batches)}."
        })
    return value


class CreateOrderSerializer(serializers.Serializer):
    """Validates course purchase order creation."""
    course_id = serializers.IntegerField()
    batch = serializers.CharField(max_length=100)

    def validate_course_id(self, value):
        """Ensures course exists and is active."""
        try:
            course = Course.objects.get(id=value, is_active=True)
        except Course.DoesNotExist:
            raise serializers.ValidationError({"error": "The selected course does not exist or is not active."})
        
        # Check for existing completed subscription
        if CourseSubscription.objects.filter(
            student=self.context['request'].user,
            course=course,
            payment_status='completed'
        ).exists():
            raise serializers.ValidationError({"error": "You are already enrolled in this course."})
        
        return value

    def validate_batch(self, value):
        """Ensures the selected batch is available for the course."""
        course_id = self.initial_data.get('course_id')
        try:
            course = Course.objects.get(id=course_id, is_active=True)
            return validate_batch_for_course(value, course)
        except Course.DoesNotExist:
            raise serializers.ValidationError({"error": "The selected course does not exist or is not active."})

    def validate(self, attrs):
        """Ensures user is verified before creating order."""
        if not self.context['request'].user.is_verified:
            errors = []
            if not self.context['request'].user.email_verified:
                errors.append("Your email is not verified.")
            if not self.context['request'].user.phone_verified:
                errors.append("Your phone number is not verified.")
            raise serializers.ValidationError({"error": " ".join(errors)})
        
        return attrs


class VerifyPaymentSerializer(serializers.Serializer):
    """Validates payment verification data."""
    razorpay_order_id = serializers.CharField(required=True)
    razorpay_payment_id = serializers.CharField(required=True)
    razorpay_signature = serializers.CharField(required=True)
    subscription_id = serializers.IntegerField(required=True)

    def validate(self, attrs):
        """Ensures subscription exists and is pending."""
        try:
            subscription = CourseSubscription.objects.get(
                id=attrs['subscription_id'],
                order_id=attrs['razorpay_order_id'],
                student=self.context['request'].user,
                payment_status='pending'
            )
        except CourseSubscription.DoesNotExist:
            raise serializers.ValidationError({"error": "The subscription was not found or has already been processed."})
        
        attrs['subscription'] = subscription
        return attrs