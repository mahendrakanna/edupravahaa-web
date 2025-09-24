from rest_framework import serializers
from edu_platform.models import Course, CourseSubscription, ClassSchedule, ClassSession
from datetime import datetime
from django.utils import timezone
from dateutil import parser
import uuid
import re
from django.db import IntegrityError

def validate_batch_for_course(value, course):
    """Shared utility to validate batch availability for a course."""
    schedules = ClassSchedule.objects.filter(course=course)
    if not schedules.exists():
        raise serializers.ValidationError({
            'message': f"No schedules are available for the course '{course.name}'. Please contact support.",
            'message_type': 'error'
        })
    available_batches = set(schedule.batch for schedule in schedules)
    if value not in available_batches:
        raise serializers.ValidationError({
            'message': f"The batch '{value}' is not available for the course '{course.name}'. Available batches are: {', '.join(available_batches)}.",
            'message_type': 'error'
        })
    return value

def parse_time_range(time_str):
    """Parses a time range string (e.g., '12:00 PM to 01:00 PM') into start and end times."""
    try:
        start_str, end_str = time_str.split(' to ')
        start_time = datetime.strptime(start_str.strip(), '%I:%M %p').time()
        end_time = datetime.strptime(end_str.strip(), '%I:%M %p').time()
        return start_time, end_time
    except ValueError:
        raise serializers.ValidationError({
            'message': f"Invalid time format: '{time_str}'. Expected format: 'HH:MM AM/PM to HH:MM AM/PM'.",
            'message_type': 'error'
        })

class CreateOrderSerializer(serializers.Serializer):
    """Validates course purchase order creation."""
    course_id = serializers.IntegerField()
    batch = serializers.CharField(max_length=100)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    time = serializers.CharField(max_length=100, required=False)
    saturday_time = serializers.CharField(max_length=100, required=False)
    sunday_time = serializers.CharField(max_length=100, required=False)

    def validate(self, attrs):
        """Validates batch, start_date, end_date, and time fields."""
        course_id = attrs['course_id']
        batch = attrs['batch']
        start_date = attrs['start_date']
        end_date = attrs['end_date']
        time = attrs.get('time')
        saturday_time = attrs.get('saturday_time')
        sunday_time = attrs.get('sunday_time')

        try:
            course = Course.objects.get(id=course_id, is_active=True)
        except Course.DoesNotExist:
            raise serializers.ValidationError({
                'message': "The selected course does not exist or is not active.",
                'message_type': 'error'
            })

        # Validate batch
        validate_batch_for_course(batch, course)

        # Validate start_date and end_date against ClassSchedule
        schedule = ClassSchedule.objects.filter(
            course=course,
            batch=batch,
            batch_start_date=start_date,
            batch_end_date=end_date
        ).first()
        if not schedule:
            raise serializers.ValidationError({
                'message': f"The provided start_date '{start_date}' and end_date '{end_date}' do not match any schedule for batch '{batch}' in course '{course.name}'.",
                'message_type': 'error'
            })

        # Batch-specific time validation
        if batch == 'weekdays':
            if not time:
                raise serializers.ValidationError({
                    'message': "The 'time' field is required for weekdays batch.",
                    'message_type': 'error'
                })
            if saturday_time or sunday_time:
                raise serializers.ValidationError({
                    'message': "The 'saturday_time' and 'sunday_time' fields should not be provided for weekdays batch.",
                    'message_type': 'error'
                })

            # Parse and validate time
            start_time, end_time = parse_time_range(time)
            session = ClassSession.objects.filter(
                schedule=schedule,
                start_time__time=start_time,
                end_time__time=end_time
            ).first()
            if not session:
                raise serializers.ValidationError({
                    'message': f"The provided time '{time}' does not match any session for batch '{batch}' in course '{course.name}'.",
                    'message_type': 'error'
                })
            attrs['start_time'] = start_time
            attrs['end_time'] = end_time
            attrs['saturday_start_time'] = None
            attrs['saturday_end_time'] = None
            attrs['sunday_start_time'] = None
            attrs['sunday_end_time'] = None

        elif batch == 'weekends':
            if not (saturday_time and sunday_time):
                raise serializers.ValidationError({
                    'message': "Both 'saturday_time' and 'sunday_time' fields are required for weekends batch.",
                    'message_type': 'error'
                })
            if time:
                raise serializers.ValidationError({
                    'message': "The 'time' field should not be provided for weekends batch.",
                    'message_type': 'error'
                })

            # Parse and validate Saturday time
            saturday_start_time, saturday_end_time = parse_time_range(saturday_time)
            saturday_session = ClassSession.objects.filter(
                schedule=schedule,
                start_time__time=saturday_start_time,
                end_time__time=saturday_end_time,
                session_date__week_day=7  # Saturday
            ).first()
            if not saturday_session:
                raise serializers.ValidationError({
                    'message': f"The provided saturday_time '{saturday_time}' does not match any Saturday session for batch '{batch}' in course '{course.name}'.",
                    'message_type': 'error'
                })

            # Parse and validate Sunday time
            sunday_start_time, sunday_end_time = parse_time_range(sunday_time)
            sunday_session = ClassSession.objects.filter(
                schedule=schedule,
                start_time__time=sunday_start_time,
                end_time__time=sunday_end_time,
                session_date__week_day=1  # Sunday
            ).first()
            if not sunday_session:
                raise serializers.ValidationError({
                    'message': f"The provided sunday_time '{sunday_time}' does not match any Sunday session for batch '{batch}' in course '{course.name}'.",
                    'message_type': 'error'
                })

            attrs['start_time'] = saturday_start_time  # Store Saturday time in start_time for consistency
            attrs['end_time'] = saturday_end_time
            attrs['saturday_start_time'] = saturday_start_time
            attrs['saturday_end_time'] = saturday_end_time
            attrs['sunday_start_time'] = sunday_start_time
            attrs['sunday_end_time'] = sunday_end_time
        else:
            raise serializers.ValidationError({
                'message': f"Invalid batch '{batch}'. Must be 'weekdays' or 'weekends'.",
                'message_type': 'error'
            })

        # Ensure user is verified
        if not self.context['request'].user.is_verified:
            errors = []
            if not self.context['request'].user.email_verified:
                errors.append("Your email is not verified.")
            if not self.context['request'].user.phone_verified:
                errors.append("Your phone number is not verified.")
            raise serializers.ValidationError({
                'message': " ".join(errors),
                'message_type': 'error'
            })

        return attrs

    def create(self):
        """Creates a CourseSubscription with the validated data."""
        try:
            course_id = self.validated_data['course_id']
            batch = self.validated_data['batch']
            start_date = self.validated_data['start_date']
            end_date = self.validated_data['end_date']
            start_time = self.validated_data.get('start_time')
            end_time = self.validated_data.get('end_time')
            saturday_start_time = self.validated_data.get('saturday_start_time')
            saturday_end_time = self.validated_data.get('saturday_end_time')
            sunday_start_time = self.validated_data.get('sunday_start_time')
            sunday_end_time = self.validated_data.get('sunday_end_time')
            course = Course.objects.get(id=course_id)

            subscription = CourseSubscription.objects.create(
                student=self.context['request'].user,
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
                order_id=f"ORDER-{uuid.uuid4()}",
                payment_method='razorpay',
                payment_status='pending',
                currency='INR'
            )
            return subscription
        except IntegrityError as e:
            if 'course_subscriptions_unique_student_course' in str(e):
                raise serializers.ValidationError({
                    'message': f"You are already subscribed to the course '{course.name}'.",
                    'message_type': 'error'
                })
            raise serializers.ValidationError({
                'message': "Failed to create order. Please try again later.",
                'message_type': 'error'
            })

class VerifyPaymentSerializer(serializers.Serializer):
    """Validates payment verification data and creates enrollment."""
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
            raise serializers.ValidationError({
                'message': 'The subscription was not found or has already been processed.',
                'message_type': 'error'
            })
        
        attrs['subscription'] = subscription
        return attrs