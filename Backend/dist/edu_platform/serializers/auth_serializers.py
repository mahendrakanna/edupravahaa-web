from rest_framework import serializers
from django.contrib.auth import authenticate, get_user_model
from django.db.models import Q
from edu_platform.models import User, TeacherProfile, OTP, StudentProfile, Course, ClassSchedule
from edu_platform.serializers.course_serializers import CourseSerializer
import re
from django.utils import timezone
from datetime import datetime, timedelta
import logging

# Set up logging
logger = logging.getLogger(__name__)

User = get_user_model()


def validate_identifier_utility(value, identifier_type=None):
    """Validates and detects identifier type (email or phone)."""
    if not identifier_type:
        if '@' in value and re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', value):
            identifier_type = 'email'
        elif re.match(r'^\+?\d{10,15}$', value):
            identifier_type = 'phone'
        else:
            raise serializers.ValidationError({
                'error': 'Invalid identifier. Must be a valid email or phone number (10-15 digits).'
            })
    else:
        if identifier_type == 'email' and not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', value):
            raise serializers.ValidationError({
                'error': 'Invalid email format.'
            })
        elif identifier_type == 'phone' and not re.match(r'^\+?\d{10,15}$', value):
            raise serializers.ValidationError({
                'error': 'Invalid phone number. Must be 10-15 digits, optionally starting with +.'
            })
    return value, identifier_type


def validate_password_utility(value):
    if not any(c.isupper() for c in value):
        raise serializers.ValidationError({
            'error': 'Password must contain at least one uppercase letter.'
        })
    if not any(c.isdigit() for c in value):
        raise serializers.ValidationError({
            'error': 'Password must contain at least one digit.'
        })
    if not any(c in '!@#$%^&*()' for c in value):
        raise serializers.ValidationError({
            'error': 'Password must contain at least one special character (!@#$%^&*()).'
        })
    return value


def check_user_existence_utility(email=None, phone_number=None):
    if email and User.objects.filter(email=email).exists():
        raise serializers.ValidationError({
            'error': 'This email is already registered.'
        })
    if phone_number and User.objects.filter(phone_number=phone_number).exists():
        raise serializers.ValidationError({
            'error': 'This phone number is already registered.'
        })

class TeacherProfileSerializer(serializers.ModelSerializer):
    """Serializes teacher profile data."""
    
    class Meta:
        model = TeacherProfile
        fields = ['qualification', 'experience_years', 'specialization', 'bio', 
                  'profile_picture', 'linkedin_url', 'resume', 'is_verified', 
                  'teaching_languages']
        read_only_fields = ['is_verified']

    def validate_experience_years(self, value):
        """Ensures experience years are within valid range."""
        if value < 0 or value > 50:
            raise serializers.ValidationError({
                'error': 'Experience years must be between 0 and 50.'
            })
        return value

    def validate_specialization(self, value):
        """Ensures specialization is a non-empty list."""
        if not isinstance(value, list) or not value:
            raise serializers.ValidationError({
                'error': 'Specialization must be a non-empty list of subjects.'
            })
        return value

    def validate_teaching_languages(self, value):
        """Ensures teaching languages is a list."""
        if not isinstance(value, list):
            raise serializers.ValidationError({
                'error': 'Teaching languages must be a list.'
            })
        return value

    def validate_linkedin_url(self, value):
        """Ensures LinkedIn URL is valid if provided."""
        if value and not re.match(r'^https?://(www\.)?linkedin\.com/.*$', value):
            raise serializers.ValidationError({
                'error': 'Invalid LinkedIn URL.'
            })
        return value

class AssignedCourseSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)
    
    class Meta:
        model = ClassSchedule
        fields = ['course']

class UserSerializer(serializers.ModelSerializer):
    """Serializes basic user data for retrieval and updates."""
    profile = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'phone_number', 'first_name', 
                  'last_name', 'role', 'email_verified', 'phone_verified', 
                  'date_joined', 'profile']
        read_only_fields = ['id', 'date_joined', 'email_verified', 'phone_verified']

    def validate_email(self, value):
        check_user_existence_utility(email=value)
        return value
    
    def validate_phone_number(self, value):
        check_user_existence_utility(phone_number=value)
        return value

    def get_profile(self, obj):
        logger.debug(f"Serializing profile for user {obj.id}, role: {obj.role}")
        try:
            if obj.is_teacher:
                profile = TeacherProfile.objects.get(user=obj)
                return TeacherProfileSerializer(profile, context=self.context).data
            elif obj.is_student:
                profile = StudentProfile.objects.get(user=obj)
                return StudentProfileSerializer(profile, context=self.context).data
            return None
        except Exception as e:
            logger.error(f"Error serializing profile for user {obj.id}: {str(e)}")
            raise serializers.ValidationError({
                'error': f'Failed to serialize profile: {str(e)}'
            })

class RegisterSerializer(serializers.Serializer):
    """Handles student user registration with email and phone verification."""
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    phone_number = serializers.CharField(max_length=15)
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, required=True)

    def validate_email(self, value):
        """Ensures email is not already registered."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError({
                'error': 'This email is already registered.'
            })
        return value
    
    def validate_phone_number(self, value):
        """Ensures phone number is valid and not already registered."""
        if not re.match(r'^\+?\d{10,15}$', value):
            raise serializers.ValidationError({
                'error': 'Invalid phone number. Must be 10-15 digits, optionally starting with +.'
            })
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError({
                'error': 'This phone number is already registered.'
            })
        return value
    
    def validate(self, attrs):
        """Verifies email and phone OTPs and password match."""
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({
                'error': 'Passwords do not match.'
            })
        
        email = attrs['email']
        phone_number = attrs['phone_number']

        # Check for verified OTPs for email and phone
        if not OTP.objects.filter(
            identifier=email,
            otp_type='email',
            purpose='registration',
            is_verified=True,
            expires_at__gt=timezone.now()
        ).exists():
            raise serializers.ValidationError({
                'error': 'Email OTP not verified or expired.'
            })

        if not OTP.objects.filter(
            identifier=phone_number,
            otp_type='phone',
            purpose='registration',
            is_verified=True,
            expires_at__gt=timezone.now()
        ).exists():
            raise serializers.ValidationError({
                'error': 'Phone OTP not verified or expired.'
            })

        return attrs
    
    def create(self, validated_data):
        """Creates a student user and deletes used OTPs."""
        validated_data.pop('confirm_password')
        password = validated_data.pop('password')
        
        user = User.objects.create_user(
            **validated_data,
            role='student',
            email_verified=True,
            phone_verified=True
        )
        user.set_password(password)
        user.save()
        StudentProfile.objects.create(user=user)
        
        # Delete used OTPs to prevent reuse
        OTP.objects.filter(
            identifier=validated_data['email'],
            otp_type='email',
            purpose='registration'
        ).delete()
        
        OTP.objects.filter(
            identifier=validated_data['phone_number'],
            otp_type='phone',
            purpose='registration'
        ).delete()
        
        return user


class TeacherCreateSerializer(serializers.ModelSerializer):
    """Handles teacher user creation by admin."""
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, required=True)
    name = serializers.CharField(max_length=150, required=True, allow_blank=False)
    course_assignments = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        allow_empty=True
    )
    phone = serializers.CharField(source='phone_number', max_length=15, required=True, allow_blank=False)

    class Meta:
        model = User
        fields = ['name', 'course_assignments', 'email', 'phone', 'password', 
                  'confirm_password']
    
    def validate_name(self, value):
        """Ensures name is not blank."""
        if not value.strip():
            raise serializers.ValidationError({
                'error': 'Name is required and cannot be blank.'
            })
        return value
    
    def validate_course_assignments(self, value):
        """Validates each course assignment."""
        logger.debug(f"Validating course_assignments: {value}")
        if not isinstance(value, list):
            raise serializers.ValidationError({
                'error': 'Course assignments must be a list.'
            })
        course_ids = []
        for assignment in value:
            if not isinstance(assignment, dict):
                raise serializers.ValidationError({
                    'error': 'Each assignment must be a dictionary.'
                })
            required_keys = ['course_id', 'batches']
            if not all(key in assignment for key in required_keys):
                raise serializers.ValidationError({
                    'error': f"Each assignment must have {required_keys}."
                })
            course_id = assignment['course_id']
            if not isinstance(course_id, int):
                raise serializers.ValidationError({
                    'error': 'course_id must be an integer.'
                })
            if course_id in course_ids:
                raise serializers.ValidationError({
                    'error': 'Duplicate course_id in assignments.'
                })
            course_ids.append(course_id)
            batches = assignment['batches']
            if not isinstance(batches, list) or not batches:
                raise serializers.ValidationError({
                    'error': 'batches must be a non-empty list.'
                })
            valid_batches = ['weekdays', 'weekends']
            if not all(b in valid_batches for b in batches):
                raise serializers.ValidationError({
                    'error': f"batches must be from {valid_batches}."
                })
            # Validate fields based on batches
            if 'weekdays' in batches:
                wk_req = ['weekdays_start_date', 'weekdays_days', 'weekdays_start', 'weekdays_end']
                if not all(key in assignment for key in wk_req):
                    raise serializers.ValidationError({
                        'error': f"For weekdays, require {wk_req}."
                    })
                days = assignment['weekdays_days']
                if not isinstance(days, list) or not days:
                    raise serializers.ValidationError({
                        'error': 'weekdays_days must be non-empty list.'
                    })
                valid_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
                if not all(d in valid_days for d in days):
                    raise serializers.ValidationError({
                        'error': f"weekdays_days must be from {valid_days}."
                    })
                # Validate times
                try:
                    start = datetime.strptime(assignment['weekdays_start'], '%I:%M %p').time()
                    end = datetime.strptime(assignment['weekdays_end'], '%I:%M %p').time()
                    if start >= end:
                        raise ValueError
                except ValueError:
                    raise serializers.ValidationError({
                        'error': 'Invalid weekdays times or format (HH:MM AM/PM). End > start.'
                    })
                # Convert weekdays_start_date to date object
                try:
                    assignment['weekdays_start_date'] = datetime.strptime(
                        assignment['weekdays_start_date'], '%Y-%m-%d'
                    ).date()
                except ValueError:
                    raise serializers.ValidationError({
                        'error': 'Invalid weekdays_start_date format (YYYY-MM-DD).'
                    })
            if 'weekends' in batches:
                we_req = ['weekend_start_date']
                if not all(key in assignment for key in we_req):
                    raise serializers.ValidationError({
                        'error': f"For weekends, require {we_req}."
                    })
                # Saturday and Sunday optional, but at least one
                has_sat = 'saturday_start' in assignment and 'saturday_end' in assignment
                has_sun = 'sunday_start' in assignment and 'sunday_end' in assignment
                if not (has_sat or has_sun):
                    raise serializers.ValidationError({
                        'error': 'For weekends, provide at least Saturday or Sunday times.'
                    })
                if has_sat:
                    try:
                        start = datetime.strptime(assignment['saturday_start'], '%I:%M %p').time()
                        end = datetime.strptime(assignment['saturday_end'], '%I:%M %p').time()
                        if start >= end:
                            raise ValueError
                    except ValueError:
                        raise serializers.ValidationError({
                            'error': 'Invalid Saturday times or format. End > start.'
                        })
                if has_sun:
                    try:
                        start = datetime.strptime(assignment['sunday_start'], '%I:%M %p').time()
                        end = datetime.strptime(assignment['sunday_end'], '%I:%M %p').time()
                        if start >= end:
                            raise ValueError
                    except ValueError:
                        raise serializers.ValidationError({
                            'error': 'Invalid Sunday times or format. End > start.'
                        })
                # Convert weekend_start_date to date object
                try:
                    assignment['weekend_start_date'] = datetime.strptime(
                        assignment['weekend_start_date'], '%Y-%m-%d'
                    ).date()
                except ValueError:
                    raise serializers.ValidationError({
                        'error': 'Invalid weekend_start_date format (YYYY-MM-DD).'
                    })
        # Check courses exist
        courses = Course.objects.filter(id__in=course_ids, is_active=True)
        if len(courses) != len(course_ids):
            raise serializers.ValidationError({
                'error': 'One or more courses do not exist or are not active.'
            })
        return value
    
    def validate_email(self, value):
        """Ensures email is not blank and not already registered."""
        logger.debug(f"Validating email: {value}")
        if not value.strip():
            raise serializers.ValidationError({
                'error': 'Email is required and cannot be blank.'
            })
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError({
                'error': 'This email is already registered.'
            })
        return value
    
    def validate_phone(self, value):
        """Ensures phone number is valid and not already registered."""
        logger.debug(f"Validating phone: {value}")
        if not value.strip():
            raise serializers.ValidationError({
                'error': 'Phone number is required and cannot be blank.'
            })
        if not re.match(r'^\+?\d{10,15}$', value):
            raise serializers.ValidationError({
                'error': 'Invalid phone number. Must be 10-15 digits, optionally starting with +.'
            })
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError({
                'error': 'This phone number is already registered.'
            })
        return value
    
    def validate_password(self, value):
        """Validates password strength."""
        logger.debug("Validating password")
        return validate_password_utility(value)
    
    def validate(self, attrs):
        """Ensures passwords match."""
        logger.debug(f"Validating attrs: {attrs}")
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({
                'error': 'Passwords do not match.'
            })
        return attrs
    
    def to_representation(self, instance):
        """Customizes the response to include full user and profile data."""
        logger.debug(f"Serializing teacher response for user {instance.id}")
        try:
            representation = UserSerializer(instance, context=self.context).data
            return representation
        except Exception as e:
            logger.error(f"Error in to_representation for user {instance.id}: {str(e)}")
            raise serializers.ValidationError({
                'error': f'Failed to serialize teacher response: {str(e)}'
            })

    def create(self, validated_data):
        """Creates a pre-verified teacher user and associated ClassSchedule objects."""
        logger.debug(f"Creating teacher with validated data: {validated_data}")
        try:
            name = validated_data.pop('name')
            course_assignments = validated_data.pop('course_assignments', [])
            phone = validated_data.pop('phone_number')
            validated_data['phone_number'] = phone
            validated_data['username'] = name
            validated_data['first_name'] = name
            validated_data.pop('confirm_password')
            password = validated_data.pop('password')
            
            # Create the user
            logger.info(f"Creating user with email: {validated_data['email']}")
            user = User.objects.create_user(
                **validated_data,
                role='teacher',
                email_verified=True,
                phone_verified=True
            )
            user.set_password(password)
            user.save()
            
            # Create the teacher profile
            logger.info(f"Creating teacher profile for user: {user.id}")
            TeacherProfile.objects.create(
                user=user,
                qualification='',
                specialization=[],
                teaching_languages=[],
            )
            
            # Create ClassSchedule for each assignment
            for assignment in course_assignments:
                course_id = assignment['course_id']
                batches = assignment['batches']
                course = Course.objects.get(id=course_id)
                schedule = []
                
                if 'weekdays' in batches:
                    time_str = f"{assignment['weekdays_start']} to {assignment['weekdays_end']}"
                    schedule.append({
                        "type": "weekdays",
                        "startDate": assignment['weekdays_start_date'].isoformat(),  # Now a date object
                        "days": assignment['weekdays_days'],
                        "time": time_str
                    })
                
                if 'weekends' in batches:
                    if 'saturday_start' in assignment:
                        time_str = f"{assignment['saturday_start']} to {assignment['saturday_end']}"
                        schedule.append({
                            "type": "weekends",
                            "startDate": assignment['weekend_start_date'].isoformat(),  # Now a date object
                            "days": ["Saturday"],
                            "time": time_str
                        })
                    if 'sunday_start' in assignment:
                        time_str = f"{assignment['sunday_start']} to {assignment['sunday_end']}"
                        schedule.append({
                            "type": "weekends",
                            "startDate": assignment['weekend_start_date'].isoformat(),  # Now a date object
                            "days": ["Sunday"],
                            "time": time_str
                        })
                
                logger.info(f"Creating ClassSchedule for course {course.name}")
                ClassSchedule.objects.create(
                    teacher=user,
                    course=course,
                    batches=batches,
                    schedule=schedule
                )
            
            logger.info(f"Teacher created successfully: {user.id}")
            return user
        except Exception as e:
            logger.error(f"Teacher creation error: {str(e)}")
            raise serializers.ValidationError({
                'error': f'Failed to create teacher: {str(e)}'
            })


class AdminCreateSerializer(serializers.ModelSerializer):
    """Handles admin user creation by any user."""
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, required=True)
    phone_number = serializers.CharField(max_length=15, required=False, allow_blank=True, allow_null=True)
    username = serializers.CharField(max_length=150, required=True, allow_blank=False)
    email = serializers.EmailField(required=True, allow_blank=False)

    class Meta:
        model = User
        fields = ['username', 'email', 'phone_number', 'password', 
                  'confirm_password', 'first_name', 'last_name']
    
    def validate_username(self, value):
        """Ensures username is not blank."""
        if not value.strip():
            raise serializers.ValidationError({
                'error': 'Username is required and cannot be blank.'
            })
        return value
    
    def validate_email(self, value):
        """Ensures email is not blank and not already registered."""
        if not value.strip():
            raise serializers.ValidationError({
                'error': 'Email is required and cannot be blank.'
            })
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError({
                'error': 'This email is already registered.'
            })
        return value
    
    def validate_phone_number(self, value):
        """Ensures phone number is valid and not already registered if provided."""
        if value:
            if not re.match(r'^\+?\d{10,15}$', value):
                raise serializers.ValidationError({
                    'error': 'Invalid phone number. Must be 10-15 digits, optionally starting with +.'
                })
            if User.objects.filter(phone_number=value).exists():
                raise serializers.ValidationError({
                    'error': 'This phone number is already registered.'
                })
        return value
    
    def validate_password(self, value):
        """Validates password strength."""
        return validate_password_utility(value)
    
    def validate(self, attrs):
        """Ensures passwords match."""
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({
                'error': 'Passwords do not match.'
            })
        return attrs
    
    def create(self, validated_data):
        """Creates a pre-verified admin user."""
        validated_data.pop('confirm_password')
        password = validated_data.pop('password')
        user = User.objects.create_superuser(
            **validated_data,
        )
        user.set_password(password)
        user.save()
        return user


class ChangePasswordSerializer(serializers.Serializer):
    """Manages password changes with validation."""
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
    confirm_password = serializers.CharField(required=True, min_length=8)
    
    def validate_old_password(self, value):
        """Verifies the old password is correct."""
        user = self.context.get('request').user
        if not user.check_password(value):
            raise serializers.ValidationError({
                'error': 'Old password is incorrect.'
            })
        return value
    
    def validate_new_password(self, value):
        return validate_password_utility(value)
    
    def validate(self, attrs):
        """Ensures new password and confirm password match."""
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({
                'error': 'New passwords do not match.'
            })
        return attrs
    
    def save(self):
        """Updates the user's password."""
        user = self.context.get('request').user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    """Handles user login with email, phone, or username."""
    identifier = serializers.CharField()
    password = serializers.CharField(write_only=True)
    
    def validate_identifier(self, value):
        identifier_type = self.initial_data.get('identifier_type')
        value, identifier_type = validate_identifier_utility(value, identifier_type)
        self.initial_data['identifier_type'] = identifier_type
        return value
    
    def validate(self, attrs):
        """Authenticates user credentials."""
        identifier = attrs.get('identifier')
        password = attrs.get('password')
        
        if not identifier or not password:
            raise serializers.ValidationError({
                'error': 'Must include "identifier" and "password".'
            })

        user = None
        try:
            user_obj = User.objects.get(Q(email=identifier) | Q(phone_number=identifier) | Q(username=identifier))
            user = authenticate(username=user_obj.email, password=password)
        except User.DoesNotExist:
            raise serializers.ValidationError({
                'error': 'Invalid identifier. Please provide a valid email, phone number, or username.'
            })

        if not user:
            raise serializers.ValidationError({
                'error': 'Invalid credentials.'
            })
        
        if not user.is_active:
            raise serializers.ValidationError({
                'error': 'User account is disabled.'
            })
        
        attrs['user'] = user
        return attrs


class SendOTPSerializer(serializers.Serializer):
    """Sends OTP to email or phone with auto-detection."""
    identifier = serializers.CharField(help_text="Email address or phone number")
    identifier_type = serializers.ChoiceField(choices=['email', 'phone'], required=False, 
                                             help_text="Optional - will be auto-detected if not provided")
    purpose = serializers.ChoiceField(choices=['registration', 'password_reset'])

    def validate_identifier(self, value):
        identifier_type = self.initial_data.get('identifier_type')
        value, identifier_type = validate_identifier_utility(value, identifier_type)
        self.initial_data['identifier_type'] = identifier_type
        return value

    def validate(self, attrs):
        """Ensures user exists for password reset and not for registration."""
        identifier = attrs['identifier']
        purpose = attrs['purpose']
        identifier_type = self.initial_data['identifier_type']
        
        if purpose == 'password_reset':
            if identifier_type == 'email' and not User.objects.filter(email=identifier).exists():
                raise serializers.ValidationError({
                    'error': 'No user found with this email address.'
                })
            elif identifier_type == 'phone' and not User.objects.filter(phone_number=identifier).exists():
                raise serializers.ValidationError({
                    'error': 'No user found with this phone number.'
                })
        elif purpose == 'registration':
            if identifier_type == 'email' and User.objects.filter(email=identifier).exists():
                raise serializers.ValidationError({
                    'error': 'This email is already registered.'
                })
            elif identifier_type == 'phone' and User.objects.filter(phone_number=identifier).exists():
                raise serializers.ValidationError({
                    'error': 'This phone number is already registered.'
                })
        
        return attrs


class VerifyOTPSerializer(serializers.Serializer):
    """Verifies OTP with auto-detection of identifier type."""
    identifier = serializers.CharField(help_text="Email address or phone number")
    identifier_type = serializers.ChoiceField(choices=['email', 'phone'], required=False,
                                             help_text="Optional - will be auto-detected if not provided")
    otp_code = serializers.CharField(max_length=4)
    purpose = serializers.ChoiceField(choices=['registration', 'password_reset'])

    def validate_identifier(self, value):
        identifier_type = self.initial_data.get('identifier_type')
        value, identifier_type = validate_identifier_utility(value, identifier_type)
        self.initial_data['identifier_type'] = identifier_type
        return value

    def validate(self, attrs):
        """Verifies OTP exists and is not expired."""
        identifier = attrs['identifier']
        otp_code = attrs['otp_code']
        purpose = attrs['purpose']
        identifier_type = self.initial_data['identifier_type']
        
        otp = OTP.objects.filter(
            identifier=identifier,
            otp_type=identifier_type,
            purpose=purpose,
            otp_code=otp_code
        ).order_by('-created_at').first()
        
        if not otp:
            raise serializers.ValidationError({
                'error': 'Invalid OTP.'
            })
        if otp.is_expired:
            raise serializers.ValidationError({
                'error': 'OTP has expired.'
            })
        
        attrs['otp'] = otp
        return attrs


class ForgotPasswordSerializer(serializers.Serializer):
    """Resets password using OTP verification."""
    identifier = serializers.CharField()
    otp_code = serializers.CharField(max_length=4)
    new_password = serializers.CharField(min_length=8)
    confirm_password = serializers.CharField(min_length=8)

    def validate_identifier(self, value):
        identifier_type = self.initial_data.get('identifier_type')
        value, identifier_type = validate_identifier_utility(value, identifier_type)
        self.initial_data['identifier_type'] = identifier_type
        return value
    
    def validate_new_password(self, value):
        return validate_password_utility(value)
    
    def validate(self, attrs):
        """Verifies passwords match and OTP is valid."""
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({
                'error': 'Passwords do not match.'
            })
        
        identifier = attrs['identifier']
        otp_code = attrs['otp_code']
        
        # Determine identifier type
        identifier_type = 'email' if '@' in identifier else 'phone'
        
        # Verify user exists
        user = None
        try:
            if identifier_type == 'email':
                user = User.objects.get(email=identifier)
            else:
                user = User.objects.get(phone_number=identifier)
        except User.DoesNotExist:
            raise serializers.ValidationError({
                'error': 'No user found with this identifier.'
            })
        
        # Verify OTP
        otp = OTP.objects.filter(
            identifier=identifier,
            otp_type=identifier_type,
            purpose='password_reset',
            otp_code=otp_code
        ).order_by('-created_at').first()
        
        if not otp:
            raise serializers.ValidationError({
                'error': 'Invalid OTP.'
            })
        if otp.is_expired:
            raise serializers.ValidationError({
                'error': 'OTP has expired.'
            })
        
        attrs['user'] = user
        attrs['otp'] = otp
        return attrs

    def save(self):
        """Updates the user's password and marks OTP as verified."""
        user = self.validated_data['user']
        otp = self.validated_data['otp']
        user.set_password(self.validated_data['new_password'])
        user.save()
        otp.is_verified = True
        otp.save()
        return user


class StudentProfileSerializer(serializers.ModelSerializer):
    """Serializes student profile data."""
    class Meta:
        model = StudentProfile
        fields = ['profile_picture']