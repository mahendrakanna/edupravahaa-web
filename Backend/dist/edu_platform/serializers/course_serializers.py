from rest_framework import serializers
from edu_platform.models import Course, CourseSubscription, ClassSchedule, CourseEnrollment


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
        # Ensure partial updates are allowed for PUT requests
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
        """Aggregates unique batches from all ClassSchedules for the course."""
        schedules = ClassSchedule.objects.filter(course=obj)
        all_batches = set()
        for schedule in schedules:
            all_batches.update(schedule.batches)
        return list(all_batches)

    def get_schedule(self, obj):
        """Aggregates all schedule entries from all ClassSchedules for the course."""
        schedules = ClassSchedule.objects.filter(course=obj)
        all_schedules = []
        for schedule in schedules:
            all_schedules.extend(schedule.schedule)
        return all_schedules


class PurchasedCoursesSerializer(serializers.ModelSerializer):
    """Serializes purchased course subscriptions for students."""
    course = CourseSerializer(read_only=True)
    batch = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CourseSubscription
        fields = [
            'id', 'course', 'batch', 'purchased_at', 'payment_status'
        ]

    def get_batch(self, obj):
        """Gets the batch from the first enrollment."""
        enrollment = obj.enrollments.first()
        return enrollment.batch if enrollment else None