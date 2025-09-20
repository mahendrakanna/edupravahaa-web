from rest_framework import serializers
from django.utils import timezone
from datetime import datetime, timedelta
from edu_platform.models import User, ClassSchedule, Course, ClassSession, CourseEnrollment
import logging
import uuid

logger = logging.getLogger(__name__)


def parse_time_string(value):
    """Parses 12-hour time strings like '4:00 PM' into a 24-hour time object."""
    try:
        return datetime.strptime(value, "%I:%M %p").time()
    except Exception:
        raise serializers.ValidationError(f"Invalid time format: '{value}'. Use format like '4:00 PM'.")


class ClassSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClassSession
        fields = ['id', 'session_date', 'start_time', 'end_time', 'recording_url', 'is_active']
        read_only_fields = ['is_active']


class BatchDetailSerializer(serializers.ModelSerializer):
    """Serializer for batch details with nested class sessions."""
    batch_name = serializers.CharField(source='batch', read_only=True)
    batch_start_date = serializers.DateField(read_only=True)
    batch_end_date = serializers.DateField(read_only=True)
    classes = ClassSessionSerializer(source='sessions', many=True, read_only=True)

    class Meta:
        model = ClassSchedule
        fields = ['batch_name', 'batch_start_date', 'batch_end_date', 'classes']

class CourseSessionSerializer(serializers.ModelSerializer):
    """Serializer for courses with nested batches and sessions."""
    course_name = serializers.CharField(source='name', read_only=True)
    batches = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ['course_name', 'batches']

    def get_batches(self, obj):
        """Get batches (ClassSchedules) for the course, filtered by user role."""
        request = self.context.get('request')
        if request.user.is_admin:
            schedules = ClassSchedule.objects.filter(course=obj)
        elif request.user.is_teacher:
            schedules = ClassSchedule.objects.filter(course=obj, teacher=request.user)
        elif request.user.is_student:
            schedules = ClassSchedule.objects.filter(
                course=obj,
                batch__in=CourseEnrollment.objects.filter(
                    student=request.user,
                    course=obj,
                    subscription__payment_status='completed'
                ).values('batch')
            )
        else:
            schedules = ClassSchedule.objects.none()

        return BatchDetailSerializer(schedules.order_by('batch', 'batch_start_date'), many=True, context={'request': request}).data


class ClassScheduleAssignmentSerializer(serializers.Serializer):
    """Validates batch assignment for existing teachers."""
    teacher_id = serializers.IntegerField(
        error_messages={'required': 'Teacher ID is required for batch assignment.'}
    )
    course_id = serializers.IntegerField(
        error_messages={'required': 'Course ID is required for batch assignment.'}
    )
    batches = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=False,
        error_messages={'required': 'Batches are required for batch assignment.'}
    )
    weekdays_start_date = serializers.DateField(
        required=False,
        error_messages={'required': 'Weekdays start date is required for weekdays batch.'}
    )
    weekdays_end_date = serializers.DateField(
        required=False,
        error_messages={'required': 'Weekdays end date is required for weekdays batch.'}
    )
    weekdays_days = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
        error_messages={'required': 'Weekdays days are required for weekdays batch.'}
    )
    weekdays_start = serializers.CharField(
        max_length=8,
        required=False,
        error_messages={'required': 'Weekdays start time is required for weekdays batch.'}
    )
    weekdays_end = serializers.CharField(
        max_length=8,
        required=False,
        error_messages={'required': 'Weekdays end time is required for weekdays batch.'}
    )
    weekend_start_date = serializers.DateField(
        required=False,
        error_messages={'required': 'Weekend start date is required for weekends batch.'}
    )
    weekend_end_date = serializers.DateField(
        required=False,
        error_messages={'required': 'Weekend end date is required for weekends batch.'}
    )
    saturday_start = serializers.CharField(
        max_length=8,
        required=False,
        error_messages={'required': 'Saturday start time is required if Saturday end is provided.'}
    )
    saturday_end = serializers.CharField(
        max_length=8,
        required=False,
        error_messages={'required': 'Saturday end time is required if Saturday start is provided.'}
    )
    sunday_start = serializers.CharField(
        max_length=8,
        required=False,
        error_messages={'required': 'Sunday start time is required if Sunday end is provided.'}
    )
    sunday_end = serializers.CharField(
        max_length=8,
        required=False,
        error_messages={'required': 'Sunday end time is required if Sunday start is provided.'}
    )

    def validate_teacher_id(self, value):
        """Ensures the teacher exists and is a teacher."""
        try:
            teacher = User.objects.get(id=value, role='teacher')
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError({"error": f"Teacher with ID {value} not found or not a teacher."})

    def validate_course_id(self, value):
        """Ensures the course exists and is active."""
        try:
            course = Course.objects.get(id=value, is_active=True)
            return value
        except Course.DoesNotExist:
            raise serializers.ValidationError({"error": f"Course with ID {value} not found or inactive."})

    def validate_batches(self, value):
        """Ensures batches are valid and unique."""
        valid_batches = ['weekdays', 'weekends']
        if not all(batch in valid_batches for batch in value):
            raise serializers.ValidationError({
                'error': f"Batches must be one or more of: {', '.join(valid_batches)}."
            })
        if len(value) != len(set(value)):
            raise serializers.ValidationError({"error": "Duplicate batches are not allowed."})
        return value

    def validate(self, attrs):
        """Ensures required fields based on batches."""
        batches = attrs.get('batches', [])
        errors = {}

        if 'weekdays' in batches:
            required_fields = ['weekdays_start_date', 'weekdays_end_date', 'weekdays_start', 'weekdays_end']
            for field in required_fields:
                if field not in attrs or not attrs[field]:
                    errors[field] = f"{field} is required for 'weekdays' batch."
            if 'weekdays_start_date' in attrs and 'weekdays_end_date' in attrs:
                if attrs['weekdays_start_date'] > attrs['weekdays_end_date']:
                    errors['weekdays_end_date'] = "End date must be after start date."
            if 'weekdays_days' in attrs:
                valid_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
                if not all(day in valid_days for day in attrs['weekdays_days']):
                    errors['weekdays_days'] = f"Weekdays must be from: {', '.join(valid_days)}."

        if 'weekends' in batches:
            required_fields = ['weekend_start_date', 'weekend_end_date']
            for field in required_fields:
                if field not in attrs or not attrs[field]:
                    errors[field] = f"{field} is required for 'weekends' batch."
            if 'weekend_start_date' in attrs and 'weekend_end_date' in attrs:
                if attrs['weekend_start_date'] > attrs['weekend_end_date']:
                    errors['weekend_end_date'] = "End date must be after start date."
            has_sat = attrs.get('saturday_start') and attrs.get('saturday_end')
            has_sun = attrs.get('sunday_start') and attrs.get('sunday_end')
            if not (has_sat or has_sun):
                errors['weekend_times'] = "At least Saturday or Sunday timings must be provided."

        if errors:
            raise serializers.ValidationError(errors)

        return attrs

    def validate_session_conflicts(self, teacher, course_id, schedules):
        """Checks for overlapping sessions with existing teacher schedules."""
        for schedule in schedules:
            start_date = schedule['start_date']
            end_date = schedule['end_date']
            days = schedule['days']
            start_time_str = schedule['start_time']
            end_time_str = schedule['end_time']
            try:
                start_time = parse_time_string(start_time_str)
                end_time = parse_time_string(end_time_str)
                if start_time >= end_time:
                    raise ValueError("End time must be after start time.")
            except ValueError as e:
                raise serializers.ValidationError({
                    'error': f"Invalid time format or logic for {schedule['type']}: {str(e)}."
                })

            current_date = start_date
            while current_date <= end_date:
                day_name = current_date.strftime('%A')
                if day_name in days:
                    session_start = timezone.make_aware(datetime.combine(current_date, start_time))
                    session_end = timezone.make_aware(datetime.combine(current_date, end_time))
                    overlapping_sessions = ClassSession.objects.filter(
                        schedule__teacher=teacher,
                        session_date=current_date,
                        start_time__lt=session_end,
                        end_time__gt=session_start
                    )
                    if overlapping_sessions.exists():
                        conflict_session = overlapping_sessions.first()
                        raise serializers.ValidationError({
                            'error': f"Teacher has a conflicting session on {current_date.strftime('%Y-%m-%d')} from {start_time_str} to {end_time_str} (existing: {conflict_session.start_time} to {conflict_session.end_time}). Timing must differ on the same date."
                        })
                current_date += timedelta(days=1)


class ClassScheduleSerializer(serializers.ModelSerializer):
    """Serializes ClassSchedule objects for retrieval and updates."""
    course = serializers.CharField(source='course.name', read_only=True)
    course_id = serializers.IntegerField(
        write_only=True,
        required=True,
        error_messages={'required': 'Course ID is required.'}
    )
    teacher = serializers.CharField(source='teacher.email', read_only=True)
    batch = serializers.CharField(
        required=True,
        error_messages={'required': 'Batch field is required (e.g., "weekdays" or "weekends").'}
    )
    sessions = ClassSessionSerializer(many=True, read_only=True)
    # For single batch creation (date/time fields)
    weekdays_start_date = serializers.DateField(required=False)
    weekdays_end_date = serializers.DateField(required=False)
    weekdays_days = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)
    weekdays_start = serializers.CharField(max_length=8, required=False)
    weekdays_end = serializers.CharField(max_length=8, required=False)
    weekend_start_date = serializers.DateField(required=False)
    weekend_end_date = serializers.DateField(required=False)
    saturday_start = serializers.CharField(max_length=8, required=False)
    saturday_end = serializers.CharField(max_length=8, required=False)
    sunday_start = serializers.CharField(max_length=8, required=False)
    sunday_end = serializers.CharField(max_length=8, required=False)
    # For adding multiple batches to existing teachers
    teacher_id = serializers.IntegerField(
        write_only=True,
        required=False,
        error_messages={'required': 'Teacher ID is required for batch assignment.'}
    )
    batch_assignment = ClassScheduleAssignmentSerializer(required=False)

    class Meta:
        model = ClassSchedule
        fields = [
            'id', 'course', 'course_id', 'teacher', 'teacher_id', 'batch',
            'sessions', 'weekdays_start_date', 'weekdays_end_date', 'weekdays_days',
            'weekdays_start', 'weekdays_end', 'weekend_start_date', 'weekend_end_date',
            'saturday_start', 'saturday_end', 'sunday_start', 'sunday_end', 'batch_assignment'
        ]

    def validate_course_id(self, value):
        """Ensures the course exists and is active."""
        try:
            course = Course.objects.get(id=value, is_active=True)
            return value
        except Course.DoesNotExist:
            raise serializers.ValidationError({'error': 'Course not found or inactive.'})

    def validate_batch(self, value):
        """Ensures batch is valid."""
        valid_batches = ['weekdays', 'weekends']
        if value not in valid_batches:
            raise serializers.ValidationError({
                'error': f"Batch must be one of: {', '.join(valid_batches)}."
            })
        return value

    def validate(self, attrs):
        """Validates date/time fields for single batch creation."""
        batch = attrs.get('batch')
        errors = {}

        if batch == 'weekdays':
            required_fields = ['weekdays_start_date', 'weekdays_end_date', 'weekdays_start', 'weekdays_end']
            for field in required_fields:
                if field not in attrs or not attrs[field]:
                    errors[field] = f"{field} is required for 'weekdays' batch."
            if 'weekdays_start_date' in attrs and 'weekdays_end_date' in attrs:
                if attrs['weekdays_start_date'] > attrs['weekdays_end_date']:
                    errors['weekdays_end_date'] = "End date must be after start date."
            if 'weekdays_days' in attrs:
                valid_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
                if not all(day in valid_days for day in attrs['weekdays_days']):
                    errors['weekdays_days'] = f"Weekdays must be from: {', '.join(valid_days)}."

        elif batch == 'weekends':
            required_fields = ['weekend_start_date', 'weekend_end_date']
            for field in required_fields:
                if field not in attrs or not attrs[field]:
                    errors[field] = f"{field} is required for 'weekends' batch."
            if 'weekend_start_date' in attrs and 'weekend_end_date' in attrs:
                if attrs['weekend_start_date'] > attrs['weekend_end_date']:
                    errors['weekend_end_date'] = "End date must be after start date."
            has_sat = attrs.get('saturday_start') and attrs.get('saturday_end')
            has_sun = attrs.get('sunday_start') and attrs.get('sunday_end')
            if not (has_sat or has_sun):
                errors['weekend_times'] = "At least Saturday or Sunday timings must be provided."

        if errors:
            raise serializers.ValidationError(errors)

        return attrs

    def create(self, validated_data):
        """Creates a ClassSchedule and associated ClassSession instances."""
        batch_assignment = validated_data.pop('batch_assignment', None)
        teacher_id = validated_data.pop('teacher_id', None)
        course_id = validated_data.pop('course_id')
        course = Course.objects.get(id=course_id)
        batch = validated_data.pop('batch', None)

        if batch_assignment:
            # Multiple batch assignment
            teacher = User.objects.get(id=batch_assignment['teacher_id'], role='teacher')
            batches = batch_assignment['batches']
            schedules = []

            if 'weekdays' in batches:
                start_date = batch_assignment['weekdays_start_date']
                end_date = batch_assignment['weekdays_end_date']
                days = batch_assignment['weekdays_days'] or ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
                start_time = batch_assignment['weekdays_start']
                end_time = batch_assignment['weekdays_end']
                schedules.append({
                    'type': 'weekdays',
                    'batch': 'weekdays',
                    'start_date': start_date,
                    'end_date': end_date,
                    'days': days,
                    'start_time': start_time,
                    'end_time': end_time
                })

            if 'weekends' in batches:
                start_date = batch_assignment['weekend_start_date']
                end_date = batch_assignment['weekend_end_date']
                weekend_days = {}
                if batch_assignment.get('saturday_start') and batch_assignment.get('saturday_end'):
                    weekend_days['Saturday'] = (batch_assignment['saturday_start'], batch_assignment['saturday_end'])
                if batch_assignment.get('sunday_start') and batch_assignment.get('sunday_end'):
                    weekend_days['Sunday'] = (batch_assignment['sunday_start'], batch_assignment['sunday_end'])
                for day, (start_time, end_time) in weekend_days.items():
                    schedules.append({
                        'type': 'weekends',
                        'batch': 'weekends',
                        'start_date': start_date,
                        'end_date': end_date,
                        'days': [day],
                        'start_time': start_time,
                        'end_time': end_time
                    })

            # Validate conflicts
            assignment_serializer = ClassScheduleAssignmentSerializer(data=batch_assignment)
            if not assignment_serializer.is_valid():
                raise serializers.ValidationError(assignment_serializer.errors)
            assignment_serializer.validate_session_conflicts(teacher, course_id, schedules)

            # Create schedules and sessions
            created_schedules = []
            for schedule in schedules:
                # Allow same batch as long as timings don’t conflict
                existing = ClassSchedule.objects.filter(course=course, teacher=teacher, batch=schedule['batch']).first()
                if existing:
                    logger.info(f"Teacher {teacher.email} already has a '{schedule['batch']}' batch, checking conflicts only.")

                class_schedule = ClassSchedule.objects.create(
                    course=course,
                    teacher=teacher,
                    batch=schedule['batch'],
                    batch_start_date=schedule['start_date'],
                    batch_end_date=schedule['end_date']
                )
                created_schedules.append(class_schedule)

                # Create sessions (recurring for all matching days)
                current_date = schedule['start_date']
                start_time = parse_time_string(schedule['start_time'])
                end_time = parse_time_string(schedule['end_time'])
                while current_date <= schedule['end_date']:
                    day_name = current_date.strftime('%A')
                    if day_name in schedule['days']:
                        session_start = timezone.make_aware(datetime.combine(current_date, start_time))
                        session_end = timezone.make_aware(datetime.combine(current_date, end_time))
                        ClassSession.objects.create(
                            schedule=class_schedule,
                            session_date=current_date,
                            start_time=session_start,
                            end_time=session_end
                        )
                    current_date += timedelta(days=1)

            return {'schedules': created_schedules}
        else:
            # Single batch creation
            if teacher_id:
                teacher = User.objects.get(id=teacher_id, role='teacher')
            else:
                teacher = self.context['request'].user
            if not teacher.role == 'teacher':
                raise serializers.ValidationError({'error': 'User must be a teacher.'})

            # Prepare schedule for validation
            schedules = []
            if batch == 'weekdays':
                start_date = validated_data['weekdays_start_date']
                end_date = validated_data['weekdays_end_date']
                days = validated_data['weekdays_days'] or ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
                start_time = validated_data['weekdays_start']
                end_time = validated_data['weekdays_end']
                schedules.append({
                    'type': 'weekdays',
                    'batch': batch,
                    'start_date': start_date,
                    'end_date': end_date,
                    'days': days,
                    'start_time': start_time,
                    'end_time': end_time
                })
            elif batch == 'weekends':
                start_date = validated_data['weekend_start_date']
                end_date = validated_data['weekend_end_date']
                weekend_days = {}
                if validated_data.get('saturday_start') and validated_data.get('saturday_end'):
                    weekend_days['Saturday'] = (validated_data['saturday_start'], validated_data['saturday_end'])
                if validated_data.get('sunday_start') and validated_data.get('sunday_end'):
                    weekend_days['Sunday'] = (validated_data['sunday_start'], validated_data['sunday_end'])
                for day, (start_time, end_time) in weekend_days.items():
                    schedules.append({
                        'type': 'weekends',
                        'batch': batch,
                        'start_date': start_date,
                        'end_date': end_date,
                        'days': [day],
                        'start_time': start_time,
                        'end_time': end_time
                    })

            # Validate conflicts
            assignment_data = {
                'teacher_id': teacher.id,
                'course_id': course_id,
                'batches': [batch],
                **{k: v for k, v in validated_data.items() if k in ['weekdays_start_date', 'weekdays_end_date', 'weekdays_days', 'weekdays_start', 'weekdays_end', 'weekend_start_date', 'weekend_end_date', 'saturday_start', 'saturday_end', 'sunday_start', 'sunday_end']}
            }
            assignment_serializer = ClassScheduleAssignmentSerializer(data=assignment_data)
            if not assignment_serializer.is_valid():
                raise serializers.ValidationError(assignment_serializer.errors)
            assignment_serializer.validate_session_conflicts(teacher, course_id, schedules)

            # Create ClassSchedule
            class_schedule = ClassSchedule.objects.create(
                course=course,
                teacher=teacher,
                batch=batch,
                batch_start_date=validated_data.get('weekdays_start_date') or validated_data.get('weekend_start_date'),
                batch_end_date=validated_data.get('weekdays_end_date') or validated_data.get('weekend_end_date')
            )

            # Create sessions (recurring for all matching days)
            for schedule in schedules:
                current_date = schedule['start_date']
                start_time = parse_time_string(schedule['start_time'])
                end_time = parse_time_string(schedule['end_time'])
                while current_date <= schedule['end_date']:
                    day_name = current_date.strftime('%A')
                    if day_name in schedule['days']:
                        session_start = timezone.make_aware(datetime.combine(current_date, start_time))
                        session_end = timezone.make_aware(datetime.combine(current_date, end_time))
                        ClassSession.objects.create(
                            schedule=class_schedule,
                            session_date=current_date,
                            start_time=session_start,
                            end_time=session_end
                        )
                    current_date += timedelta(days=1)

            return class_schedule