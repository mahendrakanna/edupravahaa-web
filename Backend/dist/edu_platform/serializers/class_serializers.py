from rest_framework import serializers
from django.utils import timezone
from datetime import datetime
from edu_platform.models import ClassSchedule, Course


class ClassScheduleSerializer(serializers.ModelSerializer):
    """Serializes ClassSchedule objects for retrieval and updates."""
    course = serializers.CharField(source='course.name', read_only=True)
    course_id = serializers.IntegerField(write_only=True, required=True)
    teacher = serializers.CharField(source='teacher.email', read_only=True)
    batches = serializers.ListField(child=serializers.CharField(), required=True)
    schedule = serializers.ListField(child=serializers.DictField(), required=True)

    class Meta:
        model = ClassSchedule
        fields = ['id', 'course', 'course_id', 'teacher', 'batches', 'schedule']

    def validate_course_id(self, value):
        """Ensures the course exists and is active."""
        try:
            course = Course.objects.get(id=value, is_active=True)
            return value
        except Course.DoesNotExist:
            raise serializers.ValidationError({
                'error': 'Course not found or inactive.'
            })

    def validate_batches(self, value):
        """Ensures batches is a non-empty list of valid choices."""
        if not isinstance(value, list) or not value:
            raise serializers.ValidationError({
                'error': 'Batches must be a non-empty list.'
            })
        valid_batches = ['weekdays', 'weekends']
        if not all(b in valid_batches for b in value):
            raise serializers.ValidationError({
                'error': f"Batches must be from {valid_batches}."
            })
        return value

    def validate_schedule(self, value):
        """Ensures schedule is a list of valid dicts."""
        if not isinstance(value, list):
            raise serializers.ValidationError({
                'error': 'Schedule must be a list.'
            })
        valid_types = ['weekdays', 'weekends']
        valid_weekday_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        valid_weekend_days = ['Saturday', 'Sunday']
        for entry in value:
            if not isinstance(entry, dict) or not all(k in entry for k in ['type', 'startDate', 'endDate', 'days', 'time']):
                raise serializers.ValidationError({
                    'error': 'Each schedule entry must have type, startDate, endDate, days, time.'
                })
            if entry['type'] not in valid_types:
                raise serializers.ValidationError({
                    'error': f"Type must be from {valid_types}."
                })
            if not isinstance(entry['days'], list) or not entry['days']:
                raise serializers.ValidationError({
                    'error': 'Days must be non-empty list.'
                })
            if entry['type'] == 'weekdays':
                if not all(d in valid_weekday_days for d in entry['days']):
                    raise serializers.ValidationError({
                        'error': f"Days for weekdays must be from {valid_weekday_days}."
                    })
            elif entry['type'] == 'weekends':
                if not all(d in valid_weekend_days for d in entry['days']):
                    raise serializers.ValidationError({
                        'error': f"Days for weekends must be from {valid_weekend_days}."
                    })
            try:
                start_str, end_str = entry['time'].split(' to ')
                start = datetime.strptime(start_str.strip(), '%I:%M %p').time()
                end = datetime.strptime(end_str.strip(), '%I:%M %p').time()
                if start >= end:
                    raise ValueError
            except ValueError:
                raise serializers.ValidationError({
                    'error': 'Invalid time format (HH:MM AM/PM to HH:MM AM/PM). End > start.'
                })
            try:
                datetime.strptime(entry['startDate'], '%Y-%m-%d')
                datetime.strptime(entry['endDate'], '%Y-%m-%d')
            except ValueError:
                raise serializers.ValidationError({
                    'error': 'Invalid startDate or endDate  format (YYYY-MM-DD).'
                })
        return value

    def create(self, validated_data):
        """Creates a ClassSchedule instance."""
        course_id = validated_data.pop('course_id')
        course = Course.objects.get(id=course_id)
        validated_data['course'] = course
        validated_data['teacher'] = self.context['request'].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """Updates a ClassSchedule instance."""
        course_id = validated_data.pop('course_id', None)
        if course_id is not None:
            course = Course.objects.get(id=course_id)
            instance.course = course
        instance.batches = validated_data.get('batches', instance.batches)
        instance.schedule = validated_data.get('schedule', instance.schedule)
        instance.save()
        return instance