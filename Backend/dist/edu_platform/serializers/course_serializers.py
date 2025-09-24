# from rest_framework import serializers
# from edu_platform.models import Course, CourseSubscription, ClassSchedule, ClassSession, CourseEnrollment
# from django.utils.dateformat import format as date_format
# from django.utils import timezone
# from datetime import date

# class CourseSerializer(serializers.ModelSerializer):
#     """Serializes course data for retrieval and updates."""
#     batches = serializers.SerializerMethodField()
#     schedule = serializers.SerializerMethodField()

#     class Meta:
#         model = Course
#         fields = [
#             'id', 'name', 'slug', 'description', 'category', 'level', 'thumbnail',
#             'duration_hours', 'base_price', 'advantages', 'batches', 'schedule',
#             'is_active', 'created_at', 'updated_at'
#         ]

#     def get_batches(self, obj):
#         request = self.context.get('request')
#         today = date.today()
#         if request and request.user.role == 'teacher':
#             return list(obj.class_schedules.filter(teacher=request.user).values_list('batch', flat=True).distinct())
#         elif request and request.user.role == 'student':
#             # For MyCoursesView, only include the enrolled batch
#             if 'view' in self.context and self.context['view'].__class__.__name__ == 'MyCoursesView':
#                 enrollment = CourseEnrollment.objects.filter(
#                     student=request.user,
#                     course=obj,
#                     subscription__payment_status='completed'
#                 ).first()
#                 if enrollment:
#                     return [enrollment.batch]
#                 return []
#             # For CourseListView, include only upcoming batches (exclude ongoing)
#             return list(obj.class_schedules.filter(batch_start_date__gt=today).values_list('batch', flat=True).distinct())
#         # For admins or others, return all batches
#         return list(obj.class_schedules.values_list('batch', flat=True).distinct())

#     def get_schedule(self, obj):
#         request = self.context.get('request')
#         today = date.today()
#         if request and request.user.role == 'teacher':
#             class_schedules = obj.class_schedules.filter(teacher=request.user).order_by('batch_start_date')
#         elif request and request.user.role == 'student':
#             # For MyCoursesView, only include schedule for the enrolled batch
#             if 'view' in self.context and self.context['view'].__class__.__name__ == 'MyCoursesView':
#                 enrollment = CourseEnrollment.objects.filter(
#                     student=request.user,
#                     course=obj,
#                     subscription__payment_status='completed'
#                 ).first()
#                 if enrollment:
#                     class_schedules = obj.class_schedules.filter(batch=enrollment.batch).order_by('batch_start_date')
#                 else:
#                     class_schedules = obj.class_schedules.none()
#             else:
#                 # For CourseListView, include only upcoming batches (exclude ongoing)
#                 class_schedules = obj.class_schedules.filter(batch_start_date__gt=today).order_by('batch_start_date')
#         else:
#             class_schedules = obj.class_schedules.all().order_by('batch_start_date')

#         schedules = []
#         for cs in class_schedules:
#             sessions = cs.sessions.order_by('session_date', 'start_time')
#             if not sessions.exists():
#                 continue

#             if cs.batch == 'weekdays':
#                 first_session = sessions[0]
#                 start_str = first_session.start_time.strftime('%I:%M %p')
#                 end_str = first_session.end_time.strftime('%I:%M %p')
#                 days = sorted(set(s.session_date.strftime('%A') for s in sessions))
#                 schedules.append({
#                     'days': days,
#                     'time': f"{start_str} to {end_str}",
#                     'type': cs.batch,
#                     'batchStartDate': cs.batch_start_date.isoformat(),
#                     'batchEndDate': cs.batch_end_date.isoformat()
#                 })
#             elif cs.batch == 'weekends':
#                 saturday_sessions = [s for s in sessions if s.session_date.strftime('%A').lower() == 'saturday']
#                 sunday_sessions = [s for s in sessions if s.session_date.strftime('%A').lower() == 'sunday']
                
#                 saturday_time = None
#                 sunday_time = None
                
#                 if saturday_sessions:
#                     first_saturday = saturday_sessions[0]
#                     saturday_time = f"{first_saturday.start_time.strftime('%I:%M %p')} to {first_saturday.end_time.strftime('%I:%M %p')}"
                
#                 if sunday_sessions:
#                     first_sunday = sunday_sessions[0]
#                     sunday_time = f"{first_sunday.start_time.strftime('%I:%M %p')} to {first_sunday.end_time.strftime('%I:%M %p')}"
                
#                 # Only include if at least one day has sessions
#                 if saturday_time or sunday_time:
#                     schedule_entry = {
#                         'days': [],
#                         'type': cs.batch,
#                         'batchStartDate': cs.batch_start_date.isoformat(),
#                         'batchEndDate': cs.batch_end_date.isoformat()
#                     }
#                     if saturday_time:
#                         schedule_entry['days'].append('saturday')
#                         schedule_entry['saturday_time'] = saturday_time
#                     if sunday_time:
#                         schedule_entry['days'].append('sunday')
#                         schedule_entry['sunday_time'] = sunday_time
#                     schedules.append(schedule_entry)

#         return schedules


# class MyCoursesSerializer(serializers.Serializer):
#     def to_representation(self, instance):
#         if isinstance(instance, CourseSubscription):
#             # Fetch the specific CourseEnrollment for the subscription
#             enrollment = CourseEnrollment.objects.filter(
#                 subscription=instance,
#                 student=instance.student,
#                 course=instance.course,
#                 batch=instance.batch
#             ).first()
#             context = self.context.copy()
#             context['enrollment'] = enrollment
            
#             return {
#                 'id': instance.id,
#                 'course': CourseSerializer(instance.course, context=context).data,
#                 'purchased_at': instance.purchased_at,
#                 'payment_status': instance.payment_status
#             }
#         elif isinstance(instance, Course):
#             return {
#                 'id': instance.id,
#                 'course': CourseSerializer(instance, context=self.context).data,
#                 'purchased_at': None,
#                 'payment_status': None
#             }
#         return super().to_representation(instance)




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
            # For CourseListView, include only upcoming batches (exclude ongoing)
            return list(obj.class_schedules.filter(batch_start_date__gt=today).values_list('batch', flat=True).distinct())
        # For admins or others, return all batches
        return list(obj.class_schedules.values_list('batch', flat=True).distinct())

    def get_schedule(self, obj):
        request = self.context.get('request')
        today = date.today()
        schedules = []

        if request and request.user.role == 'teacher':
            # For teachers, return all assigned batches' schedules from ClassSchedule
            class_schedules = obj.class_schedules.filter(teacher=request.user).order_by('batch_start_date')
            for cs in class_schedules:
                sessions = cs.sessions.order_by('session_date', 'start_time')
                if not sessions.exists():
                    continue

                if cs.batch == 'weekdays':
                    first_session = sessions[0]
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
                    saturday_sessions = [s for s in sessions if s.session_date.strftime('%A').lower() == 'saturday']
                    sunday_sessions = [s for s in sessions if s.session_date.strftime('%A').lower() == 'sunday']
                    
                    saturday_time = None
                    sunday_time = None
                    
                    if saturday_sessions:
                        first_saturday = saturday_sessions[0]
                        saturday_time = f"{first_saturday.start_time.strftime('%I:%M %p')} to {first_saturday.end_time.strftime('%I:%M %p')}"
                    
                    if sunday_sessions:
                        first_sunday = sunday_sessions[0]
                        sunday_time = f"{first_sunday.start_time.strftime('%I:%M %p')} to {first_sunday.end_time.strftime('%I:%M %p')}"
                    
                    if saturday_time or sunday_time:
                        schedule_entry = {
                            'days': [],
                            'type': cs.batch,
                            'batchStartDate': cs.batch_start_date.isoformat(),
                            'batchEndDate': cs.batch_end_date.isoformat()
                        }
                        if saturday_time:
                            schedule_entry['days'].append('saturday')
                            schedule_entry['saturday_time'] = saturday_time
                        if sunday_time:
                            schedule_entry['days'].append('sunday')
                            schedule_entry['sunday_time'] = sunday_time
                        schedules.append(schedule_entry)

        elif request and request.user.role == 'student':
            # For MyCoursesView, use enrollment data for the specific batch schedule
            if 'view' in self.context and self.context['view'].__class__.__name__ == 'MyCoursesView':
                enrollment = CourseEnrollment.objects.filter(
                    student=request.user,
                    course=obj,
                    subscription__payment_status='completed'
                ).first()
                if enrollment:
                    schedule_entry = {
                        'type': enrollment.batch,
                        'batchStartDate': enrollment.start_date.isoformat() if enrollment.start_date else None,
                        'batchEndDate': enrollment.end_date.isoformat() if enrollment.end_date else None
                    }
                    if enrollment.batch == 'weekdays':
                        if enrollment.start_time and enrollment.end_time:
                            start_str = enrollment.start_time.strftime('%I:%M %p')
                            end_str = enrollment.end_time.strftime('%I:%M %p')
                            # Assuming weekdays are standard (Mon-Fri), adjust if specific days are stored elsewhere
                            schedule_entry['days'] = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
                            schedule_entry['time'] = f"{start_str} to {end_str}"
                    elif enrollment.batch == 'weekends':
                        schedule_entry['days'] = []
                        if enrollment.saturday_start_time and enrollment.saturday_end_time:
                            schedule_entry['days'].append('saturday')
                            schedule_entry['saturday_time'] = f"{enrollment.saturday_start_time.strftime('%I:%M %p')} to {enrollment.saturday_end_time.strftime('%I:%M %p')}"
                        if enrollment.sunday_start_time and enrollment.sunday_end_time:
                            schedule_entry['days'].append('sunday')
                            schedule_entry['sunday_time'] = f"{enrollment.sunday_start_time.strftime('%I:%M %p')} to {enrollment.sunday_end_time.strftime('%I:%M %p')}"
                    if schedule_entry['days']:  # Only append if there's a valid schedule
                        schedules.append(schedule_entry)
            else:
                # For CourseListView, include only upcoming batches (exclude ongoing)
                class_schedules = obj.class_schedules.filter(batch_start_date__gt=today).order_by('batch_start_date')
                for cs in class_schedules:
                    sessions = cs.sessions.order_by('session_date', 'start_time')
                    if not sessions.exists():
                        continue

                    if cs.batch == 'weekdays':
                        first_session = sessions[0]
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
                        saturday_sessions = [s for s in sessions if s.session_date.strftime('%A').lower() == 'saturday']
                        sunday_sessions = [s for s in sessions if s.session_date.strftime('%A').lower() == 'sunday']
                        
                        saturday_time = None
                        sunday_time = None
                        
                        if saturday_sessions:
                            first_saturday = saturday_sessions[0]
                            saturday_time = f"{first_saturday.start_time.strftime('%I:%M %p')} to {first_saturday.end_time.strftime('%I:%M %p')}"
                        
                        if sunday_sessions:
                            first_sunday = sunday_sessions[0]
                            sunday_time = f"{first_sunday.start_time.strftime('%I:%M %p')} to {first_sunday.end_time.strftime('%I:%M %p')}"
                        
                        if saturday_time or sunday_time:
                            schedule_entry = {
                                'days': [],
                                'type': cs.batch,
                                'batchStartDate': cs.batch_start_date.isoformat(),
                                'batchEndDate': cs.batch_end_date.isoformat()
                            }
                            if saturday_time:
                                schedule_entry['days'].append('saturday')
                                schedule_entry['saturday_time'] = saturday_time
                            if sunday_time:
                                schedule_entry['days'].append('sunday')
                                schedule_entry['sunday_time'] = sunday_time
                            schedules.append(schedule_entry)
        else:
            # For admins or others, return all schedules
            class_schedules = obj.class_schedules.all().order_by('batch_start_date')
            for cs in class_schedules:
                sessions = cs.sessions.order_by('session_date', 'start_time')
                if not sessions.exists():
                    continue

                if cs.batch == 'weekdays':
                    first_session = sessions[0]
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
                    saturday_sessions = [s for s in sessions if s.session_date.strftime('%A').lower() == 'saturday']
                    sunday_sessions = [s for s in sessions if s.session_date.strftime('%A').lower() == 'sunday']
                    
                    saturday_time = None
                    sunday_time = None
                    
                    if saturday_sessions:
                        first_saturday = saturday_sessions[0]
                        saturday_time = f"{first_saturday.start_time.strftime('%I:%M %p')} to {first_saturday.end_time.strftime('%I:%M %p')}"
                    
                    if sunday_sessions:
                        first_sunday = sunday_sessions[0]
                        sunday_time = f"{first_sunday.start_time.strftime('%I:%M %p')} to {first_sunday.end_time.strftime('%I:%M %p')}"
                    
                    if saturday_time or sunday_time:
                        schedule_entry = {
                            'days': [],
                            'type': cs.batch,
                            'batchStartDate': cs.batch_start_date.isoformat(),
                            'batchEndDate': cs.batch_end_date.isoformat()
                        }
                        if saturday_time:
                            schedule_entry['days'].append('saturday')
                            schedule_entry['saturday_time'] = saturday_time
                        if sunday_time:
                            schedule_entry['days'].append('sunday')
                            schedule_entry['sunday_time'] = sunday_time
                        schedules.append(schedule_entry)

        return schedules

class MyCoursesSerializer(serializers.Serializer):
    def to_representation(self, instance):
        if isinstance(instance, CourseSubscription):
            # Fetch the specific CourseEnrollment for the subscription
            enrollment = CourseEnrollment.objects.filter(
                subscription=instance,
                student=instance.student,
                course=instance.course,
                batch=instance.batch
            ).first()
            context = self.context.copy()
            context['enrollment'] = enrollment
            
            return {
                'id': instance.id,
                'course': CourseSerializer(instance.course, context=context).data,
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