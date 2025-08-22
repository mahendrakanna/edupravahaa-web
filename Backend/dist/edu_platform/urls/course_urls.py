from django.urls import path
from edu_platform.views.course_views import (
    CourseListView, AdminCourseCreateView, AdminCourseUpdateView, MyCoursesView
)


urlpatterns = [
    # Public course endpoints. Lists active courses with search and category filtering.
    path('', CourseListView.as_view(), name='course_list'),
    
    # Admin-only endpoint to create and update a new course
    path('admin/create/course/', AdminCourseCreateView.as_view(), name='admin_course_create'),
    path('admin/update/<int:id>/', AdminCourseUpdateView.as_view(), name='admin_course_update'),
    
    # Lists purchased courses for the authenticated student
    path('my_courses/', MyCoursesView.as_view(), name='my_courses'),

]