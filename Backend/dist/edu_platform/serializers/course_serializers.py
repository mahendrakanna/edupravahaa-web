from rest_framework import serializers
from edu_platform.models import Course, CourseSubscription


class CourseSerializer(serializers.ModelSerializer):
    """Serializes course data for retrieval and updates."""
    class Meta:
        model = Course
        fields = [
            'id', 'name', 'slug', 'description', 'category', 'level',
            'thumbnail', 'duration_hours', 'base_price', 'advantages',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']
        # Allow partial updates for PUT requests
        extra_kwargs = {
            'description': {'required': False},
            'category': {'required': False},
            'level': {'required': False},
            'thumbnail': {'required': False},
            'duration_hours': {'required': False},
            'base_price': {'required': False},
            'advantages': {'required': False},
            'is_active': {'required': False}
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


class PurchasedCoursesSerializer(serializers.ModelSerializer):
    """Serializes purchased course subscriptions for students."""
    course = CourseSerializer(read_only=True)

    class Meta:
        model = CourseSubscription
        fields = [
            'id', 'course', 'purchased_at', 'payment_status'
        ]