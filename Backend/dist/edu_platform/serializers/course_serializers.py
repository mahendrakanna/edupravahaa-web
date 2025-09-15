from rest_framework import serializers
from edu_platform.models import Course, CourseSubscription, ClassSchedule, CourseEnrollment, ClassSession
from django.utils import timezone
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class CourseSerializer(serializers.ModelSerializer):
    """Serializes course data for retrieval and updates."""
    schedule = serializers.SerializerMethodField(read_only=True)
    batches = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Course
        fields = [
            'id', 'name', 'slug', 'description', 'category', 'level',
            'thumbnail', 'duration_hours', 'base_price', 'advantages',
            'batches', 'schedule', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at', 'batches', 'schedule']
        extra_kwargs = {
            'description': {'required': False},
            'category': {'required': False},
            'level': {'required': False},
            'thumbnail': {'required': False},
            'duration_hours': {'required': False},
            'base_price': {'required': False},
            'advantages': {'required': False},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.context.get('request') and self.context['request'].method in ['PUT', 'PATCH']:
            self.partial = True

    def validate_duration_hours(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError({'error': 'Duration must be a positive integer.'})
        return value

    def validate_base_price(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError({'error': 'Base price cannot be negative.'})
        return value

    def validate_advantages(self, value):
        if value is not None and not isinstance(value, list):
            raise serializers.ValidationError({'error': 'Advantages must be a list.'})
        return value

    def validate_level(self, value):
        if value is not None and value not in dict(Course.LEVEL_CHOICES).keys():
            raise serializers.ValidationError({
                'error': f"Level must be one of: {', '.join(dict(Course.LEVEL_CHOICES).keys())}."
            })
        return value

    def get_batches(self, obj):
        """Returns batches for the course that have not started, filtered by context if provided."""
        batches = self.context.get('batches')
        if batches:
            return [batch for batch in batches if batch in ['weekdays', 'weekends']]
        
        # Only include schedules that have not started (batch_start_date >= today)
        schedules = ClassSchedule.objects.filter(
            course=obj,
            batch_start_date__gte=timezone.now().date()
        )
        all_batches = set()
        for schedule in schedules:
            batch_type = 'weekdays' if 'weekday' in schedule.batch.lower() else 'weekends'
            all_batches.add(batch_type)
        return sorted(list(all_batches))

    def get_schedule(self, obj):
        """Returns schedule entries for the course, grouped by batch and time slot, for batches that have not started."""
        batches = self.context.get('batches')
        # Only include schedules that have not started (batch_start_date >= today)
        schedules = ClassSchedule.objects.filter(
            course=obj,
            batch_start_date__gte=timezone.now().date()
        )
        all_schedules = []
        
        for schedule in schedules:
            batch_type = 'weekdays' if 'weekday' in schedule.batch.lower() else 'weekends'
            if batches and batch_type not in batches:
                continue
            
            sessions = ClassSession.objects.filter(schedule=schedule).order_by('start_time')
            if not sessions.exists():
                continue
                
            # Group sessions by time slot
            schedule_entries = {}
            for session in sessions:
                time_key = (
                    session.start_time.strftime('%I:%M %p'),
                    session.end_time.strftime('%I:%M %p')
                )
                key = (time_key, batch_type)
                
                if key not in schedule_entries:
                    schedule_entries[key] = {
                        'days': [],
                        'batchStartDate': schedule.batch_start_date.strftime('%Y-%m-%d'),
                        'batchEndDate': schedule.batch_end_date.strftime('%Y-%m-%d'),
                        'time': f"{time_key[0]} to {time_key[1]}",
                        'type': batch_type
                    }
                day = session.start_time.strftime('%A')
                if day not in schedule_entries[key]['days']:
                    schedule_entries[key]['days'].append(day)
            
            # Sort days to match desired order (Monday to Sunday)
            for entry in schedule_entries.values():
                entry['days'] = sorted(
                    entry['days'],
                    key=lambda x: ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'].index(x)
                )
                if entry not in all_schedules:
                    all_schedules.append(entry)
        
        return sorted(all_schedules, key=lambda x: (x['batchStartDate'], x['type'], x['time']))


class MyCoursesSerializer(serializers.Serializer):
    """Serializes purchased courses for students or assigned courses for teachers."""
    id = serializers.IntegerField(read_only=True)
    course = serializers.SerializerMethodField(read_only=True)
    purchased_at = serializers.DateTimeField(read_only=True, allow_null=True)
    payment_status = serializers.CharField(read_only=True, allow_null=True)

    def get_course(self, obj):
        """Serializes the course with batch details based on user role."""
        request = self.context.get('request')
        user = request.user if request else None
        batch = None
        batches = None
        
        if user and user.role == 'student':
            # For students, get the enrolled batch from CourseEnrollment
            enrollment = CourseEnrollment.objects.filter(subscription=obj).first()
            batch = enrollment.batch if enrollment else None
            batches = [batch] if batch else []
        elif user and user.role == 'teacher':
            # For teachers, get all batches they are assigned to
            schedules = ClassSchedule.objects.filter(course=obj, teacher=user)
            batches = set()
            for schedule in schedules:
                batch_type = 'weekdays' if 'weekday' in schedule.batch.lower() else 'weekends'
                batches.add(batch_type)
            batches = sorted(list(batches)) if batches else None
        
        try:
            return CourseSerializer(
                obj if user.role == 'teacher' else obj.course,
                context={'batches': batches or (batch and [batch]), 'request': self.context.get('request')}
            ).data
        except Exception as e:
            logger.error(f"Error serializing course for {user.role} (course_id: {obj.id if user.role == 'teacher' else obj.course.id}): {str(e)}")
            raise serializers.ValidationError({
                'error': f'Failed to serialize course: {str(e)}'
            })

    def to_representation(self, instance):
        """Customizes the response format to match the desired structure."""
        representation = super().to_representation(instance)
        user = self.context.get('request').user if self.context.get('request') else None
        
        if user and user.role == 'teacher':
            # For teachers, set purchased_at and payment_status to null
            representation['purchased_at'] = None
            representation['payment_status'] = None
        elif user and user.role == 'student':
            # For students, ensure purchased_at and payment_status are from the subscription
            representation['purchased_at'] = instance.purchased_at
            representation['payment_status'] = instance.payment_status
        
        return representation
