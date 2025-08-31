from django.contrib import admin
from .models import User, OTP, Course, CourseSubscription, TeacherProfile, StudentProfile, ClassSchedule, CourseEnrollment
# Register your models here.
admin.site.register(User)
admin.site.register(TeacherProfile)
admin.site.register(StudentProfile)
admin.site.register(OTP)
admin.site.register(Course)
admin.site.register(CourseSubscription)
admin.site.register(ClassSchedule)
admin.site.register(CourseEnrollment)