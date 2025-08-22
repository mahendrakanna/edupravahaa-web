from rest_framework import serializers
from edu_platform.models import Course, CourseSubscription


class CourseSerializer(serializers.ModelSerializer):
    """Serializes course data for retrieval and updates."""
    class Meta:
        model = Course
        fields = [
            'id', 'name', 'slug', 'description', 'category',
            'thumbnail', 'duration_hours', 'base_price', 'advantages', 
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']
        

class PurchasedCoursesSerializer(serializers.ModelSerializer):
    """Serializes purchased course subscriptions for students."""
    course = CourseSerializer(read_only=True)
    
    class Meta:
        model = CourseSubscription
        fields = [
            'id', 'course', 'purchased_at', 'payment_status'
        ]