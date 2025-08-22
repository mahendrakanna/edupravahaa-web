from django.contrib import admin
from .models import User, OTP, Course, CourseSubscription
# Register your models here.
admin.site.register(User)
admin.site.register(OTP)
admin.site.register(Course)
admin.site.register(CourseSubscription)
