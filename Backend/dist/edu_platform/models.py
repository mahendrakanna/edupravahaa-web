from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.conf import settings
from datetime import timedelta, datetime, date
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
import random
import uuid


#--------Auth models---------#
class User(AbstractUser):
    """Custom user model for managing user roles, verification, and trial periods."""
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('teacher', 'Teacher'),
        ('student', 'Student'),
    )
    
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')
    username = models.CharField(max_length=150, blank=True, null=True, unique=True)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(null=True, blank=True)

    trial_end_date = models.DateTimeField(null=True, blank=True)
    has_purchased_courses = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        db_table = 'users'
        
    def __str__(self):
        """Returns a string with email and role."""
        return f"{self.email} - {self.role}"

    def save(self, *args, **kwargs):
        """Sets admin role for superusers and trial period for new students."""
        if self.is_superuser and self.role != 'admin':
            self.role = 'admin'

        if not self.pk and not self.trial_end_date and self.role == 'student':
            trial_settings = getattr(settings, 'TRIAL_SETTINGS', {})
            if trial_settings.get('TEST_MODE', True):
                duration = timedelta(minutes=trial_settings.get('TRIAL_DURATION_MINUTES', 5))
            else:
                duration = timedelta(days=trial_settings.get('TRIAL_DURATION_MINUTES', 5))
            
            self.trial_end_date = timezone.now() + duration
        
        if self.phone_number == '':
            self.phone_number = None
        
        super().save(*args, **kwargs)
    
    @property
    def is_admin(self):
        """Checks if user is an admin."""
        return self.role == 'admin'
    
    @property
    def is_teacher(self):
        """Checks if user is a teacher."""
        return self.role == 'teacher'
    
    @property
    def is_student(self):
        """Checks if user is a student."""
        return self.role == 'student'
    
    @property
    def is_verified(self):
        """Checks if email and phone are verified."""
        return self.email_verified and self.phone_verified

    @property
    def is_trial_expired(self):
        """Checks if trial period has expired for a student."""
        if self.has_purchased_courses or self.role != 'student':
            return False
        
        if not self.trial_end_date:
            return False
        
        return timezone.now() > self.trial_end_date

    @property
    def trial_remaining_seconds(self):
        """Calculates remaining seconds in trial period for a student."""
        if self.has_purchased_courses or self.role != 'student':
            return None
        
        if not self.trial_end_date:
            return 0
        
        time_remaining = self.trial_end_date - timezone.now()
        
        if time_remaining.total_seconds() <= 0:
            return 0
        
        return int(time_remaining.total_seconds())


class TeacherProfile(models.Model):
    """Stores professional details for teachers."""
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='teacher_profile',
        limit_choices_to={'role': 'teacher'}
    )
    qualification = models.CharField(max_length=200)
    experience_years = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(50)])
    specialization = models.JSONField(default=list, help_text="List of subjects/areas of expertise")
    bio = models.TextField(blank=True, help_text="Brief professional biography")
    profile_picture = models.ImageField(upload_to='teacher_profiles/', null=True, blank=True)
    linkedin_url = models.URLField(blank=True)
    resume = models.FileField(upload_to='teacher_resumes/', null=True, blank=True)
    is_verified = models.BooleanField(default=False, help_text="Verified by admin")
    teaching_languages = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'teacher_profiles'
        verbose_name = 'Teacher Profile'
        verbose_name_plural = 'Teacher Profiles'
    
    def __str__(self):
        """Returns teacher's full name or email."""
        return f"Teacher: {self.user.get_full_name() or self.user.email}"


class StudentProfile(models.Model):
    """Stores additional details for students."""
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='student_profile',
        limit_choices_to={'role': 'student'}
    )
    profile_picture = models.ImageField(upload_to='student_profiles/', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'student_profiles'
        verbose_name = 'Student Profile'
        verbose_name_plural = 'Student Profiles'
    
    def __str__(self):
        """Returns student's full name or email."""
        return f"Student: {self.user.get_full_name() or self.user.email}"


class OTP(models.Model):
    """Manages one-time passwords for email or phone verification."""
    OTP_TYPE_CHOICES = (
        ('email', 'Email'),
        ('phone', 'Phone'),
    )
    
    PURPOSE_CHOICES = (
        ('registration', 'Registration'),
        ('password_reset', 'Password Reset'),
        ('profile_update', 'Profile Update'),
    )
    
    identifier = models.CharField(max_length=255)  # email or phone number
    otp_type = models.CharField(max_length=10, choices=OTP_TYPE_CHOICES)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    otp_code = models.CharField(max_length=4)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        db_table = 'otps'
        indexes = [
            models.Index(fields=['identifier', 'otp_type', 'purpose']),
        ]
    
    def save(self, *args, **kwargs):
        """Generates OTP code and expiry time if not set."""
        if not self.otp_code:
            self.otp_code = str(random.randint(1000, 9999))
        if not self.expires_at:
            otp_expiry_minutes = getattr(settings, 'OTP_EXPIRY_MINUTES', 5)
            self.expires_at = timezone.now() + timedelta(minutes=otp_expiry_minutes)
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        """Checks if OTP has expired."""
        return timezone.now() > self.expires_at
    
    def __str__(self):
        """Returns identifier, OTP type, and purpose."""
        return f"{self.identifier} - {self.otp_type} - {self.purpose}"


#--------Course models---------#
class Course(models.Model):
    """Manages pre-defined courses created by admins for class scheduling."""
    SLOT_CHOICES = (
        ('morning', 'Morning'),
        ('afternoon', 'Afternoon'),
        ('evening', 'Evening'),
    )
    
    LEVEL_CHOICES = (
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    )
    
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField()
    category = models.CharField(max_length=100)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='beginner')
    thumbnail = models.ImageField(upload_to='course_thumbnails/', blank=True, null=True)
    duration_hours = models.IntegerField(help_text="Total course duration in hours", default=30)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    advantages = models.JSONField(default=list, help_text="List of course advantages/features")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'courses'
        ordering = ['category', 'name']
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['slug']),
        ]
        
    def __str__(self):
        """Returns course name and category."""
        return f"{self.name} ({self.category})"
    
    def save(self, *args, **kwargs):
        """Generates slug from course name if not provided."""
        # Auto-generate slug if not set
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


#--------Subscription models---------#
class CourseSubscription(models.Model):
    """Tracks student course purchases with lifetime access."""
    PAYMENT_STATUS = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    )
    
    PAYMENT_METHOD_CHOICES = (
        ('razorpay', 'Razorpay'),
        ('stripe', 'Stripe'),
        ('paypal', 'PayPal'),
        ('bank_transfer', 'Bank Transfer'),
        ('free', 'Free'),
        ('other', 'Other'),
    )
    
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='course_subscriptions'
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.PROTECT,
        related_name='subscriptions'
    )
    
    # Payment details
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    payment_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    order_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHOD_CHOICES, default='other')

    # batch details 
    batch = models.CharField(max_length=100, help_text="Selected batch (e.g., weekdays or weekends)")
    start_date = models.DateField(null=True, blank=True, help_text="Start date of the batch")
    end_date = models.DateField(null=True, blank=True, help_text="End date of the batch")
    start_time = models.TimeField(null=True, blank=True, help_text="Start time of the batch")
    end_time = models.TimeField(null=True, blank=True, help_text="End time of the batch")
    saturday_start_time = models.TimeField(null=True, blank=True, help_text="Start time for Saturday (weekends only)")
    saturday_end_time = models.TimeField(null=True, blank=True, help_text="End time for Saturday (weekends only)")
    sunday_start_time = models.TimeField(null=True, blank=True, help_text="Start time for Sunday (weekends only)")
    sunday_end_time = models.TimeField(null=True, blank=True,  help_text="End time for Sunday (weekends only)")
    
    # Additional payment info
    currency = models.CharField(max_length=3, default='INR')
    # Store full payment gateway response
    payment_response = models.JSONField(null=True, blank=True)  
    
    # Timestamps
    purchased_at = models.DateTimeField(auto_now_add=True)
    payment_completed_at = models.DateTimeField(null=True, blank=True)
    
    # Access control
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'course_subscriptions'
        unique_together = ['student', 'course']
        ordering = ['-purchased_at']
        indexes = [
            models.Index(fields=['student', 'course']),
            models.Index(fields=['order_id']),
        ]
    
    def __str__(self):
        return f"{self.student.email} - {self.course.name} ({self.batch}) - ({self.start_date}) - ({self.end_date})"


#--------Class models---------#
class ClassSchedule(models.Model):
    """Represents a specific schedule for a teacher-course pair."""
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='class_schedules',
        limit_choices_to={'role': 'teacher'}
    )
    course = models.ForeignKey(
        'Course',
        on_delete=models.CASCADE,
        related_name='class_schedules'
    )
    batch = models.CharField( max_length=20, choices=[("weekdays", "Weekdays"), ("weekends", "Weekends")])
    batch_start_date = models.DateField()
    batch_end_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'class_schedules'
        indexes = [
            models.Index(fields=["course", "teacher", "batch"]),
        ]
        ordering = ['batch_start_date']
        
    def __str__(self):
        return f"{self.course.name} - {self.teacher.email} - {self.batch} - Batch from - {self.batch_start_date} to {self.batch_end_date}"


class ClassSession(models.Model):
    schedule = models.ForeignKey(
        ClassSchedule,
        on_delete=models.CASCADE,
        related_name='sessions'
    )
    class_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    session_date = models.DateField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    recording = models.FileField(upload_to="recordings/", blank=True, null=True, help_text="Local class recording")
    is_active = models.BooleanField(default=True, help_text="Whether the class is live or accessible")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'class_sessions'
        indexes = [
            models.Index(fields=['class_id']),
            models.Index(fields=["schedule", "session_date", "start_time"]),
        ]
        ordering = ["created_at"]

    def __str__(self):
        return f"Class - {self.schedule.course.name} ({self.schedule.batch})- Timing - {self.start_time} - {self.end_time}"

    def clean(self):
        if self.start_time >= self.end_time:
            raise ValidationError("Start time must be before end time.")

        # Check overlapping sessions only for the same teacher
        overlapping_sessions = ClassSession.objects.filter(
            schedule__teacher=self.schedule.teacher,
            session_date=self.session_date,
            start_time__lt=self.end_time,
            end_time__gt=self.start_time,
        ).exclude(pk=self.pk)

        if overlapping_sessions.exists():
            raise ValidationError(
                f"Teacher {self.schedule.teacher.email} already has a class "
                f"at {self.start_time.strftime('%H:%M')}–{self.end_time.strftime('%H:%M')} "
                f"on {self.session_date}."
            )


#--------Enrollment models---------#
class CourseEnrollment(models.Model):
    """Tracks student enrollment in a specific course batch."""
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='enrollments',
        limit_choices_to={'role': 'student'}
    )
    course = models.ForeignKey(
        'Course',
        on_delete=models.PROTECT,
        related_name='enrollments'
    )
    batch = models.CharField(max_length=100, help_text="Selected batch (e.g., weekdays or weekends)")
    start_date = models.DateField(null=True, help_text="Start date of the batch")
    end_date = models.DateField(null=True, help_text="End date of the batch")
    start_time = models.TimeField(null=True, help_text="Start time of the batch")
    end_time = models.TimeField(null=True, help_text="End time of the batch")
    saturday_start_time = models.TimeField(null=True, help_text="Start time for Saturday (weekends only)")
    saturday_end_time = models.TimeField(null=True, help_text="End time for Saturday (weekends only)")
    sunday_start_time = models.TimeField(null=True, help_text="Start time for Sunday (weekends only)")
    sunday_end_time = models.TimeField(null=True, help_text="End time for Sunday (weekends only)")
    subscription = models.ForeignKey(
        CourseSubscription,
        on_delete=models.CASCADE,
        related_name='enrollments'
    )
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Amount paid by student")
    enrolled_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'course_enrollments'
        unique_together = ['student', 'course', 'batch']
        indexes = [
            models.Index(fields=['student', 'course']),
            models.Index(fields=['course', 'batch']),
        ]
    
    def __str__(self):
        """Returns student email, course name, and batch."""
        return f"{self.student.email} - {self.course.name} ({self.batch})"
        

class CoursePricing(models.Model):
    """Manages dynamic pricing for courses with discounts and validity periods."""
    course=models.ForeignKey(
        Course,on_delete=models.CASCADE,related_name='pricings'
    )
    original_price=models.DecimalField(max_digits=10,decimal_places=2)
    discount_percent=models.DecimalField(max_digits=10,decimal_places=2)
    final_price=models.DecimalField(max_digits=10,decimal_places=2)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table='course_pricings'
        ordering=['-created_at']
    def __str__(self):
        return f"{self.course.name} - {self.final_price}"