# edu_platform/views/dashboard_views.py
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from django.utils import timezone
from django.db.models import Sum, F, ExpressionWrapper, DurationField
from datetime import timedelta, datetime, time, date
import calendar
import logging
import traceback

from edu_platform.models import ClassSession, CourseEnrollment
from edu_platform.views.course_views import api_response  # your helper

logger = logging.getLogger(__name__)


class TeacherDashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get teacher dashboard stats and weekly teaching trends",
        responses={
            200: openapi.Response(
                description="Teacher dashboard data retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "stats": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "totalTeachingHours": openapi.Schema(type=openapi.TYPE_NUMBER),
                                "activeStudents": openapi.Schema(type=openapi.TYPE_INTEGER),
                                "upcomingClasses": openapi.Schema(type=openapi.TYPE_INTEGER),
                                "nextClass": openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        "course": openapi.Schema(type=openapi.TYPE_STRING),
                                        "date": openapi.Schema(type=openapi.TYPE_STRING, format="date"),
                                        "time": openapi.Schema(type=openapi.TYPE_STRING),
                                    },
                                    nullable=True,
                                ),
                                "missingClasses": openapi.Schema(type=openapi.TYPE_INTEGER),
                            }
                        ),
                        "weeklyTrends": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Items(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "day": openapi.Schema(type=openapi.TYPE_STRING),
                                    "hours": openapi.Schema(type=openapi.TYPE_NUMBER),
                                }
                            )
                        ),
                    }
                )
            ),
            403: openapi.Response(description="Permission denied"),
            500: openapi.Response(description="Server error"),
        }
    )
    def get(self, request):
        teacher = request.user

        # Ensure only teacher role calls this endpoint
        if not getattr(teacher, "is_teacher", False):
            return api_response(
                message="Only teachers can access this dashboard.",
                message_type="error",
                status_code=status.HTTP_403_FORBIDDEN
            )

        try:
            now = timezone.now()

            # ---------- totalTeachingHours ----------
            # Completed session heuristic: end_time < now AND is_active == True (class ran)
            duration_expr = ExpressionWrapper(F('end_time') - F('start_time'), output_field=DurationField())
            completed_qs = ClassSession.objects.filter(
                schedule__teacher=teacher,
                end_time__lte=now,
                is_active=True
            ).annotate(duration=duration_expr)

            total_duration = completed_qs.aggregate(total=Sum('duration'))['total'] or timedelta()
            total_hours = round(total_duration.total_seconds() / 3600.0, 2)

            # ---------- activeStudents ----------
            # Count distinct students enrolled (CourseEnrollment) for teacher's courses
            active_students = CourseEnrollment.objects.filter(
                course__class_schedules__teacher=teacher
            ).values('student').distinct().count()

            # ---------- upcomingClasses ----------
            upcoming_qs = ClassSession.objects.filter(
                schedule__teacher=teacher,
                start_time__gt=now,
                is_active=True
            ).order_by('start_time')
            upcoming_count = upcoming_qs.count()

            # ---------- nextClass ----------
            next_class_obj = upcoming_qs.first()
            next_class = None
            if next_class_obj:
                # Use localtime for display
                local_start = timezone.localtime(next_class_obj.start_time)
                next_class = {
                    "course": next_class_obj.schedule.course.name,
                    "date": local_start.date().isoformat(),
                    "time": local_start.strftime('%I:%M %p')
                }

            # ---------- missingClasses ----------
            # Missed heuristic: end_time < now AND is_active == False (class marked inactive/cancelled)
            missing_count = ClassSession.objects.filter(
                schedule__teacher=teacher,
                end_time__lt=now,
                is_active=False
            ).count()

            # ---------- weeklyTrends ----------
            # Build Sunday -> Saturday for current week
            today_local = timezone.localdate()
            # find most recent Sunday
            weekday = today_local.weekday()  # Monday=0 .. Sunday=6
            days_since_sunday = (weekday + 1) % 7
            sunday = today_local - timedelta(days=days_since_sunday)
            # start datetime at localtz midnight of sunday
            tz = timezone.get_current_timezone()
            start_of_week = timezone.make_aware(datetime.combine(sunday, time.min), tz)
            end_of_week = start_of_week + timedelta(days=7)

            week_qs = ClassSession.objects.filter(
                schedule__teacher=teacher,
                start_time__gte=start_of_week,
                start_time__lt=end_of_week,
                is_active=True,
                end_time__lte=now  # only count sessions that finished
            ).annotate(duration=ExpressionWrapper(F('end_time') - F('start_time'), output_field=DurationField()))

            # aggregate per date
            day_hours_map = {day: 0.0 for day in ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"]}
            for s in week_qs:
                local_day = timezone.localtime(s.start_time).strftime('%A')
                dur = s.duration.total_seconds() / 3600.0 if s.duration else 0.0
                day_hours_map[local_day] = round(day_hours_map.get(local_day, 0.0) + dur, 2)

            weekly_trends = [{"day": d, "hours": day_hours_map.get(d, 0.0)} for d in ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"]]

            # ---------- Build payload ----------
            payload = {
                "stats": {
                    "totalTeachingHours": total_hours,
                    "activeStudents": active_students,
                    "upcomingClasses": upcoming_count,
                    "nextClass": next_class,
                    "missingClasses": missing_count
                },
                "weeklyTrends": weekly_trends
            }

            return api_response(
                message="Teacher dashboard retrieved successfully.",
                message_type="success",
                data=payload,
                status_code=status.HTTP_200_OK
            )

        except Exception as e:
            # log & expose stacktrace in server logs for debugging
            logger.error(f"Dashboard error for teacher {getattr(teacher, 'email', teacher)}: {str(e)}")
            traceback.print_exc()
            return api_response(
                message="Failed to retrieve dashboard. Please try again.",
                message_type="error",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
