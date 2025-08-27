from rest_framework import serializers
from django.contrib.auth import authenticate, get_user_model
from django.db.models import Q
from edu_platform.models import User, TeacherProfile, OTP
import re
from django.utils import timezone

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
        if not re.match(r'^\+?\d{10,15}$', phone_number):
            raise serializers.ValidationError({
                'error': 'Invalid phone number. Must be 10-15 digits, optionally starting with +.'
            })
        else:
            raise serializers.ValidationError({
                'error': 'This phone number is already registered.'
            })
        
class UserSerializer(serializers.ModelSerializer):
    """Serializes basic user data for retrieval and updates."""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'phone_number', 'first_name', 
                  'last_name', 'role', 'email_verified', 'phone_verified', 
                  'date_joined']
        read_only_fields = ['id', 'date_joined', 'email_verified', 'phone_verified']

    def validate_email(self, value):
        check_user_existence_utility(email=value)
        return value
    def validate_phone_number(self, value):
        check_user_existence_utility(phone_number=value)
        return value

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

    class Meta:
        model = User
        fields = ['username', 'email', 'phone_number', 'password', 
                  'confirm_password', 'first_name', 'last_name']
    
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
        """Ensures passwords match and only admins can create teachers."""
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({
                'error': 'Passwords do not match.'
            })
        if not self.context['request'].user.is_superuser:
            raise serializers.ValidationError({
                'error': 'Only admins can create teacher accounts.'
            })
        return attrs
    
    def create(self, validated_data):
        """Creates a pre-verified teacher user."""
        validated_data.pop('confirm_password')
        password = validated_data.pop('password')
        user = User.objects.create_user(
            **validated_data,
            role='teacher',
            email_verified=True,
            phone_verified=True
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