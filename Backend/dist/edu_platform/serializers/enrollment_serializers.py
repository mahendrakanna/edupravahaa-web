from rest_framework import serializers
from edu_platform.models import CourseEnrollment, CourseSubscription, ClassSchedule
from .payment_serializers import validate_batch_for_course


class CourseEnrollmentSerializer(serializers.ModelSerializer):
    """Serializes CourseEnrollment data for student batch selection."""
    course = serializers.CharField(source='course.name', read_only=True)
    subscription_id = serializers.IntegerField(source='subscription.id', write_only=True)

    class Meta:
        model = CourseEnrollment
        fields = ['id', 'course', 'subscription_id', 'batch', 'enrolled_at']
        read_only_fields = ['id', 'course', 'enrolled_at']

    def validate_subscription_id(self, value):
        """Ensures the subscription exists, is completed, and belongs to the student."""
        try:
            subscription = CourseSubscription.objects.get(
                id=value,
                student=self.context['request'].user,
                payment_status='completed',
                is_active=True
            )
            return value
        except CourseSubscription.DoesNotExist:
            raise serializers.ValidationError({
                'error': 'Subscription not found, not completed, or inactive.'
            })

    def validate_batch(self, value):
        """Ensures the batch is available for the course."""
        subscription_id = self.initial_data.get('subscription_id')
        try:
            subscription = CourseSubscription.objects.get(
                id=subscription_id,
                student=self.context['request'].user
            )
            course = subscription.course
            return validate_batch_for_course(value, course)
        except CourseSubscription.DoesNotExist:
            raise serializers.ValidationError({
                'error': 'Subscription not found.'
            })

    def update(self, instance, validated_data):
        """Updates the batch for an existing enrollment."""
        validated_data.pop('subscription_id', None)
        instance.batch = validated_data.get('batch', instance.batch)
        instance.save()
        return instance

    def create(self, validated_data):
        """Disables creation via this serializer."""
        raise serializers.ValidationError({
            'error': 'Enrollment creation is handled via payment process.'
        })