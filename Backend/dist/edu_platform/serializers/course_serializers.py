from rest_framework import serializers
from edu_platform.models import Course, CourseSubscription, ClassSchedule, ClassSession, CourseEnrollment
from django.utils.dateformat import format as date_format
from django.utils import timezone
from datetime import date

class CourseSerializer(serializers.ModelSerializer):
    """Serializes course data for retrieval and updates."""
    batches = serializers.SerializerMethodField()
    schedule = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            'id', 'name', 'slug', 'description', 'category', 'level', 'thumbnail',
            'duration_hours', 'base_price', 'advantages', 'batches', 'schedule',
            'is_active', 'created_at', 'updated_at'
        ]

    def get_batches(self, obj):
        request = self.context.get('request')
        today = date.today()
        if request and request.user.role == 'teacher':
            return list(obj.class_schedules.filter(teacher=request.user).values_list('batch', flat=True).distinct())
        elif request and request.user.role == 'student':
            # For MyCoursesView, only include the enrolled batch
            if 'view' in self.context and self.context['view'].__class__.__name__ == 'MyCoursesView':
                enrollment = CourseEnrollment.objects.filter(
                    student=request.user,
                    course=obj,
                    subscription__payment_status='completed'
                ).first()
                if enrollment:
                    return [enrollment.batch]
                return []
            # For CourseListView, include upcoming batches
            return list(obj.class_schedules.filter(batch_start_date__gte=today).values_list('batch', flat=True).distinct())
        # For admins or others, return all batches
        return list(obj.class_schedules.values_list('batch', flat=True).distinct())

    def get_schedule(self, obj):
        request = self.context.get('request')
        today = date.today()
        if request and request.user.role == 'teacher':
            class_schedules = obj.class_schedules.filter(teacher=request.user).order_by('batch_start_date')
        elif request and request.user.role == 'student':
            # For MyCoursesView, only include schedule for the enrolled batch
            if 'view' in self.context and self.context['view'].__class__.__name__ == 'MyCoursesView':
                enrollment = CourseEnrollment.objects.filter(
                    student=request.user,
                    course=obj,
                    subscription__payment_status='completed'
                ).first()
                if enrollment:
                    class_schedules = obj.class_schedules.filter(batch=enrollment.batch).order_by('batch_start_date')
                else:
                    class_schedules = obj.class_schedules.none()
            else:
                # For CourseListView, include upcoming batches
                class_schedules = obj.class_schedules.filter(batch_start_date__gte=today).order_by('batch_start_date')
        else:
            class_schedules = obj.class_schedules.all().order_by('batch_start_date')

        schedules = []
        for cs in class_schedules:
            sessions = cs.sessions.order_by('session_date', 'start_time')
            if not sessions.exists():
                continue

            if cs.batch == 'weekdays':
                first_session = sessions.first()
                start_str = first_session.start_time.strftime('%I:%M %p')
                end_str = first_session.end_time.strftime('%I:%M %p')
                days = sorted(set(s.session_date.strftime('%A') for s in sessions))
                schedules.append({
                    'days': days,
                    'time': f"{start_str} to {end_str}",
                    'type': cs.batch,
                    'batchStartDate': cs.batch_start_date.isoformat(),
                    'batchEndDate': cs.batch_end_date.isoformat()
                })
            elif cs.batch == 'weekends':
                day_time_groups = {}
                for session in sessions:
                    day = session.session_date.strftime('%A')
                    start_str = session.start_time.strftime('%I:%M %p')
                    end_str = session.end_time.strftime('%I:%M %p')
                    time_key = f"{start_str} to {end_str}"
                    key = (day, time_key)
                    if key not in day_time_groups:
                        day_time_groups[key] = []
                    day_time_groups[key].append(session)

                for (day, time_key), _ in day_time_groups.items():
                    schedules.append({
                        'days': [day],
                        'time': time_key,
                        'type': cs.batch,
                        'batchStartDate': cs.batch_start_date.isoformat(),
                        'batchEndDate': cs.batch_end_date.isoformat()
                    })

        return schedules

class MyCoursesSerializer(serializers.Serializer):
    def to_representation(self, instance):
        if isinstance(instance, CourseSubscription):
            return {
                'id': instance.id,
                'course': CourseSerializer(instance.course, context=self.context).data,
                'purchased_at': instance.purchased_at,
                'payment_status': instance.payment_status
            }
        elif isinstance(instance, Course):
            return {
                'id': instance.id,
                'course': CourseSerializer(instance, context=self.context).data,
                'purchased_at': None,
                'payment_status': None
            }
        return super().to_representation(instance)