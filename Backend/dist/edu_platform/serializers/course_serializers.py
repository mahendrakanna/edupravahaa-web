from rest_framework import serializers
from edu_platform.models import Course, CourseSubscription, ClassSchedule, CourseEnrollment
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
            raise serializers.ValidationError({
                'error': 'Duration must be a positive integer.'
            })
        return value

    def validate_base_price(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError({
                'error': 'Base price cannot be negative.'
            })
        return value

    def validate_advantages(self, value):
        if value is not None and not isinstance(value, list):
            raise serializers.ValidationError({
                'error': 'Advantages must be a list.'
            })
        return value

    def validate_level(self, value):
        if value is not None and value not in dict(Course.LEVEL_CHOICES).keys():
            raise serializers.ValidationError({
                'error': f"Level must be one of: {', '.join(dict(Course.LEVEL_CHOICES).keys())}."
            })
        return value

    def get_batches(self, obj):
        """Returns batches for the course, filtered by context if provided."""
        batches = self.context.get('batches')
        if batches:
            return [batch for batch in batches if batch in ['weekdays', 'weekends']]
        
        schedules = ClassSchedule.objects.filter(course=obj)
        all_batches = set()
        for schedule in schedules:
            all_batches.update(schedule.batches)
        return list(all_batches)

    def get_schedule(self, obj):
        """Returns schedule entries for the course, filtered by assigned/enrolled batches if provided."""
        batches = self.context.get('batches')
        schedules = ClassSchedule.objects.filter(course=obj)
        all_schedules = []
        
        for schedule in schedules:
            for s in schedule.schedule:
                if not batches or (batches and s.get('type') in batches):
                    if s not in all_schedules:
                        all_schedules.append(s)
        
        return all_schedules

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
            enrollment = CourseEnrollment.objects.filter(subscription=obj).first()
            batch = enrollment.batch if enrollment else None
        elif user and user.role == 'teacher':
            schedules = ClassSchedule.objects.filter(course=obj, teacher=user)
            batches = set()
            for schedule in schedules:
                batches.update(schedule.batches)
            batches = list(batches) if batches else None
        
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