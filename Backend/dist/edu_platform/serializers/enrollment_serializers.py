from rest_framework import serializers
from edu_platform.models import CourseEnrollment, CourseSubscription, ClassSchedule, ClassSession
from .payment_serializers import validate_batch_for_course


class CourseEnrollmentSerializer(serializers.ModelSerializer):
    """Serializes CourseEnrollment data for student batch selection."""
    course = serializers.CharField(source='course.name', read_only=True)
    subscription_id = serializers.IntegerField(source='subscription.id', write_only=True)

    class Meta:
        model = CourseEnrollment
        fields = [
            'id', 'course', 'subscription_id', 'batch', 'start_date', 'end_date',
            'start_time', 'end_time', 'saturday_start_time', 'saturday_end_time',
            'sunday_start_time', 'sunday_end_time', 'enrolled_at'
        ]
        read_only_fields = [
            'id', 'course', 'enrolled_at', 'start_date', 'end_date',
            'start_time', 'end_time', 'saturday_start_time', 'saturday_end_time',
            'sunday_start_time', 'sunday_end_time'
        ]

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
        """Updates the batch and related fields for an existing enrollment."""
        validated_data.pop('subscription_id', None)
        instance.batch = validated_data.get('batch', instance.batch)

        # Update time fields if batch changes
        if 'batch' in validated_data:
            schedule = ClassSchedule.objects.filter(
                course=instance.course,
                batch=validated_data['batch']
            ).first()
            if schedule:
                instance.start_date = schedule.batch_start_date
                instance.end_date = schedule.batch_end_date
                if validated_data['batch'] == 'weekdays':
                    session = ClassSession.objects.filter(schedule=schedule).order_by('start_time').first()
                    instance.start_time = session.start_time.time() if session else None
                    instance.end_time = session.end_time.time() if session else None
                    instance.saturday_start_time = None
                    instance.saturday_end_time = None
                    instance.sunday_start_time = None
                    instance.sunday_end_time = None
                elif validated_data['batch'] == 'weekends':
                    saturday_session = ClassSession.objects.filter(
                        schedule=schedule, session_date__week_day=6
                    ).order_by('start_time').first()
                    sunday_session = ClassSession.objects.filter(
                        schedule=schedule, session_date__week_day=0
                    ).order_by('start_time').first()
                    instance.start_time = saturday_session.start_time.time() if saturday_session else None
                    instance.end_time = saturday_session.end_time.time() if saturday_session else None
                    instance.saturday_start_time = saturday_session.start_time.time() if saturday_session else None
                    instance.saturday_end_time = saturday_session.end_time.time() if saturday_session else None
                    instance.sunday_start_time = sunday_session.start_time.time() if sunday_session else None
                    instance.sunday_end_time = sunday_session.end_time.time() if sunday_session else None
        instance.save()
        return instance

    def create(self, validated_data):
        """Disables creation via this serializer."""
        raise serializers.ValidationError({
            'error': 'Enrollment creation is handled via payment process.'
        })