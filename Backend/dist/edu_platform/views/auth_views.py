from rest_framework import generics, status, views
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import serializers
from django.contrib.auth import login
from django.core.mail import send_mail
from django.conf import settings
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.utils import timezone
from edu_platform.permissions.auth_permissions import IsAdmin, IsTeacher, IsStudent
from edu_platform.models import User, OTP, CourseSubscription, ClassSchedule, ClassSession, StudentProfile, TeacherProfile
from edu_platform.utility.email_services import send_otp_email
from edu_platform.utility.sms_services import get_sms_service, ConsoleSMSService
from edu_platform.serializers.auth_serializers import (
    UserSerializer, RegisterSerializer, LoginSerializer, 
    TeacherCreateSerializer, ChangePasswordSerializer,
    SendOTPSerializer, VerifyOTPSerializer, ProfileUpdateSerializer,
    ForgotPasswordSerializer, AdminCreateSerializer, StudentProfileSerializer, TeacherProfileSerializer
)
import logging
import phonenumbers

logger = logging.getLogger(__name__)

def api_response(message, message_type, data=None, status_code=200):
    """Standardizes API response structure."""
    response_data = {
        'message': message,
        'message_type': message_type
    }
    if data is not None:
        response_data['data'] = data
    return Response(response_data, status=status_code)

def get_serializer_error_message(errors):
    """Extracts a clean error message from serializer errors."""
    if isinstance(errors, dict):
        for field, error in errors.items():
            if field == 'non_field_errors':
                # Handle non-field errors (e.g., from validate method)
                if isinstance(error, list) and error:
                    if isinstance(error[0], dict) and 'message' in error[0]:
                        return {'message': error[0]['message'], 'message_type': 'error'}
                    return {'message': str(error[0]), 'message_type': 'error'}
            else:
                # Handle field-specific errors
                if isinstance(error, list) and error:
                    if isinstance(error[0], dict) and 'message' in error[0]:
                        return {'message': error[0]['message'], 'message_type': 'error'}
                    error_msg = str(error[0])
                    # Customize default DRF messages to include field name
                    field_name = field.replace('_', ' ').title()
                    if error_msg == 'This field may not be blank.':
                        return {'message': f"{field_name} cannot be empty.", 'message_type': 'error'}
                    if error_msg == 'This field is required.':
                        return {'message': f"{field_name} is required.", 'message_type': 'error'}
                    if error_msg == 'Ensure this field has at least 8 characters.':
                        return {'message': f"{field_name} must be at least 8 characters long.", 'message_type': 'error'}
                    return {'message': error_msg, 'message_type': 'error'}
                elif isinstance(error, dict) and 'message' in error:
                    return {'message': error['message'], 'message_type': 'error'}
                return {'message': str(error), 'message_type': 'error'}
    elif isinstance(errors, list) and errors:
        if isinstance(errors[0], dict) and 'message' in errors[0]:
            return {'message': errors[0]['message'], 'message_type': 'error'}
        return {'message': str(errors[0]), 'message_type': 'error'}
    return {'message': 'Invalid input provided.', 'message_type': 'error'}


class SendOTPView(generics.GenericAPIView):
    """Sends OTP to email or phone for verification."""
    permission_classes = [AllowAny]
    serializer_class = SendOTPSerializer
    
    @swagger_auto_schema(
        request_body=SendOTPSerializer,
        operation_description="Send OTP to email or phone (auto-detects type)",
        responses={
            200: openapi.Response(
                description="OTP sent successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error']),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'otp_expires_in_seconds': openapi.Schema(type=openapi.TYPE_INTEGER),
                            }
                        )
                    }
                )
            ),
            400: openapi.Response(
                description="Invalid input",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'])
                    }
                )
            ),
            500: openapi.Response(
                description="Server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'])
                    }
                )
            )
        }
    )
    
    def post(self, request):
        """Sends OTP via email or SMS with auto-detection of identifier type."""
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            error_response = get_serializer_error_message(serializer.errors)
            return api_response(
                message=error_response['message'],
                message_type='error',
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        identifier = serializer.validated_data['identifier']
        purpose = serializer.validated_data['purpose']
        identifier_type = serializer.initial_data['identifier_type']
        
        try:
            otp = OTP.objects.create(
                identifier=identifier,
                otp_type=identifier_type,
                purpose=purpose
            )
        except Exception as e:
            logger.error(f"OTP creation error: {str(e)}")
            return api_response(
                message='Failed to create OTP. Please try again.',
                message_type='error',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        if identifier_type == 'email':
            # Use SMPT for email
            email_sent = send_otp_email(identifier, otp.otp_code, purpose)
            
            # Handle email sending failure in production
            if not email_sent and not settings.DEBUG:
                return api_response(
                    message='Failed to send email. Please try again.',
                    message_type='error',
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            data = {
                'otp_expires_in_seconds': int((otp.expires_at - timezone.now()).total_seconds())
            }

            return api_response(
                message=f'OTP sent to email {identifier}.',
                message_type='success',
                data=data,
                status_code=status.HTTP_200_OK
            )
            
        else:  # phone
            # Send SMS using Twilio service
            sms_sent = False
            using_console = False
            
            try:
                sms_service = get_sms_service()
                message = f'Your OTP for {purpose.replace("_", " ").title()} is: {otp.otp_code}\nValid for 10 minutes.'
                
                # Check if using console-based SMS service
                using_console = isinstance(sms_service, ConsoleSMSService)
                
                # Attempt to send SMS
                sms_sent = sms_service.send_sms(identifier, message)
                
                # Handle SMS failure in production
                if not sms_sent and not settings.DEBUG:
                    return api_response(
                        message='Failed to send SMS. Please try again.',
                        message_type='error',
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
            except Exception as e:
                logger.error(f"SMS sending error: {str(e)}")
                if not settings.DEBUG:
                    return api_response(
                        message='SMS service unavailable.',
                        message_type='error',
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
                using_console = True
            
            data = {
                'otp_expires_in_seconds': int((otp.expires_at - timezone.now()).total_seconds())
            }

            return api_response(
                message=f'OTP sent to phone {identifier}.',
                message_type='success',
                data=data,
                status_code=status.HTTP_200_OK
            )

class VerifyOTPView(generics.GenericAPIView):
    """Verifies OTP for email or phone."""
    permission_classes = [AllowAny]
    serializer_class = VerifyOTPSerializer
    
    @swagger_auto_schema(
        request_body=VerifyOTPSerializer,
        operation_description="Verify OTP (auto-detects identifier type)",
        responses={
            200: openapi.Response(
                description="OTP verified successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error']),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'identifier': openapi.Schema(type=openapi.TYPE_STRING),
                                'identifier_type': openapi.Schema(type=openapi.TYPE_STRING),
                                'verified': openapi.Schema(type=openapi.TYPE_BOOLEAN)
                            }
                        )
                    }
                )
            ),
            400: openapi.Response(
                description="Invalid OTP or input",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'])
                    }
                )
            ),
            500: openapi.Response(
                description="Server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'])
                    }
                )
            )
        }
    )
    def post(self, request):
        """Validates and marks OTP as verified."""
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            error_response = get_serializer_error_message(serializer.errors)
            return api_response(
                message=error_response['message'],
                message_type='error',
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        identifier = serializer.validated_data['identifier']
        otp_code = serializer.validated_data['otp_code']
        purpose = serializer.validated_data['purpose']
        identifier_type = serializer.initial_data['identifier_type']
        
        otp = serializer.validated_data.get('otp')
        if not otp:
            return api_response(
                message='Invalid OTP.',
                message_type='error',
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            otp.is_verified = True
            otp.save()
            if purpose == 'profile_update' and identifier_type == 'phone':
                user = User.objects.filter(phone_number=identifier).first()
                if user:
                    user.phone_verified = True
                    user.save()
        except Exception as e:
            logger.error(f"OTP verification error: {str(e)}")
            return api_response(
                message='Failed to verify OTP. Please try again.',
                message_type='error',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        data = {
            'identifier': identifier,
            'identifier_type': identifier_type,
            'verified': True
        }
        return api_response(
            message=f'{identifier_type.capitalize()} verified successfully.',
            message_type='success',
            data=data,
            status_code=status.HTTP_200_OK
        )

class RegisterView(generics.CreateAPIView):
    """Registers a new student user."""
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="Register a new student (requires email and phone OTP verification)",
        responses={
            201: openapi.Response(
                description="Registration successful",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error']),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'trial_ends_at': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                                'trial_duration_seconds': openapi.Schema(type=openapi.TYPE_INTEGER)
                            }
                        )
                    }
                )
            ),
            400: openapi.Response(
                description="Invalid input",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'])
                    }
                )
            ),
            500: openapi.Response(
                description="Server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'])
                    }
                )
            )
        }
    )
    
    def post(self, request, *args, **kwargs):
        """Creates a student user with trial information."""
        # Validate request data
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            error_response = get_serializer_error_message(serializer.errors)
            return api_response(
                message=error_response['message'],
                message_type='error',
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = serializer.save()
            data = {
                'trial_ends_at': user.trial_end_date.isoformat() if user.trial_end_date else None,
                'trial_duration_seconds': user.trial_remaining_seconds if user.trial_end_date else None
            }
            return api_response(
                message='Registration successful! Please login to continue.',
                message_type='success',
                data=data,
                status_code=status.HTTP_201_CREATED
            )
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            return api_response(
                message='Failed to register user. Please try again.',
                message_type='error',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LoginView(generics.GenericAPIView):
    """Handles user login with JWT token generation."""
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer
    
    @swagger_auto_schema(
        request_body=LoginSerializer,
        responses={
            200: openapi.Response(
                description="Successful login",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error']),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'access': openapi.Schema(type=openapi.TYPE_STRING),
                                'refresh': openapi.Schema(type=openapi.TYPE_STRING),
                                'user_type': openapi.Schema(type=openapi.TYPE_STRING),
                                'is_trial': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                'has_purchased': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                'trial_ends_at': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                                'trial_remaining_seconds': openapi.Schema(type=openapi.TYPE_INTEGER)
                            }
                        )
                    }
                )
            ),
            400: openapi.Response(
                description="Invalid input or credentials",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'])
                    }
                )
            ),
            403: openapi.Response(
                description="Account disabled",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'])
                    }
                )
            ),
            500: openapi.Response(
                description="Server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'])
                    }
                )
            )
        }
    )
    def post(self, request):
        """Authenticates user and returns JWT tokens."""
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            error_response = get_serializer_error_message(serializer.errors)
            return api_response(
                message=error_response['message'],
                message_type='error',
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = serializer.validated_data['user']
            if not user.is_active:
                return api_response(
                    message='User account is disabled.',
                    message_type='error',
                    status_code=status.HTTP_403_FORBIDDEN
                )
                
            # Update last_login
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])
            
            refresh = RefreshToken.for_user(user)
            
            data = {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user_type': user.role
            }

            # Include trial info for students
            if user.role == 'student':
                data['is_trial'] = not user.has_purchased_courses
                data['has_purchased'] = user.has_purchased_courses
                if not user.has_purchased_courses and user.trial_end_date:
                    data['trial_ends_at'] = user.trial_end_date.isoformat()
                    data['trial_remaining_seconds'] = user.trial_remaining_seconds

            return api_response(
                message='Login successful.',
                message_type='success',
                data=data,
                status_code=status.HTTP_200_OK
            )
        
        except Exception as e:
            # Log and handle unexpected errors
            logger.error(f"Login error: {str(e)}")
            return api_response(
                message='An unexpected error occurred during login. Please try again.',
                message_type='error',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class LogoutView(generics.GenericAPIView):
    """Logs out user by blacklisting refresh token."""
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['refresh'],
            properties={
                'refresh': openapi.Schema(type=openapi.TYPE_STRING, description='Refresh token')
            }
        ),
        responses={
            205: openapi.Response(
                description="Logout successful",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'])
                    }
                )
            ),
            400: openapi.Response(
                description="Invalid token",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'])
                    }
                )
            )
        }
    )
    def post(self, request):
        """Blacklists refresh token to log out user."""
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return api_response(
                message='Refresh token is required.',
                message_type='error',
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return api_response(
                message='Logout successful.',
                message_type='success',
                status_code=status.HTTP_205_RESET_CONTENT
            )
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            return api_response(
                message='Invalid refresh token.',
                message_type='error',
                status_code=status.HTTP_400_BAD_REQUEST
            )


class ProfileView(generics.RetrieveUpdateAPIView):
    """Manages retrieval and updates of user profile."""
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        """Returns the appropriate serializer based on the request method and user role."""
        if self.request.method == 'GET':
            user = self.request.user
            if user.is_student:
                return StudentProfileSerializer
            elif user.is_teacher:
                return TeacherProfileSerializer
            return UserSerializer
        return ProfileUpdateSerializer
    
    def get_object(self):
        """Returns the appropriate object based on user role."""
        user = self.request.user
        logger.debug(f"Fetching object for user {user.id}, role: {user.role}")
        if user.is_student:
            try:
                profile = StudentProfile.objects.get(user=user)
                logger.debug(f"Found StudentProfile for user {user.id}")
                return profile
            except StudentProfile.DoesNotExist:
                logger.error(f"Student profile not found for user {user.id}")
                raise serializers.ValidationError({
                    'message': 'Student profile not found.',
                    'message_type': 'error'
                })
        elif user.is_teacher:
            try:
                profile = TeacherProfile.objects.get(user=user)
                logger.debug(f"Found TeacherProfile for user {user.id}")
                return profile
            except TeacherProfile.DoesNotExist:
                logger.error(f"Teacher profile not found for user {user.id}")
                raise serializers.ValidationError({
                    'message': 'Teacher profile not found.',
                    'message_type': 'error'
                })
        logger.debug(f"Returning User object for user {user.id}")
        return user
    
    @swagger_auto_schema(
        responses={
            200: openapi.Response(
                description="Profile retrieved or updated successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error']),
                        'data': openapi.Schema(type=openapi.TYPE_OBJECT)
                    }
                )
            ),
            400: openapi.Response(
                description="Invalid input",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'])
                    }
                )
            ),
            404: openapi.Response(
                description="Profile not found",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'])
                    }
                )
            ),
            500: openapi.Response(
                description="Server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'])
                    }
                )
            )
        }
    )
    def get(self, request, *args, **kwargs):
        """Retrieves authenticated user's profile."""
        try:
            instance = self.get_object()
            serializer_class = self.get_serializer_class()
            logger.debug(f"Using serializer {serializer_class.__name__} for instance {type(instance).__name__}")
            serializer = serializer_class(instance, context={'request': request, 'is_nested': False})
            return api_response(
                message='Profile retrieved successfully.',
                message_type='success',
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )
        except serializers.ValidationError as e:
            return api_response(
                message=e.detail.get('message', 'Profile retrieval failed.'),
                message_type='error',
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Profile retrieval error for user {request.user.id}: {str(e)}")
            return api_response(
                message='Failed to retrieve profile. Please try again.',
                message_type='error',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def patch(self, request, *args, **kwargs):
        """Updates authenticated user's profile (partial update)."""
        user = self.request.user
        if not (user.is_student or user.is_teacher):
            return api_response(
                message='Only students and teachers can update their profiles.',
                message_type='error',
                status_code=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(user, data=request.data, partial=True)
        if not serializer.is_valid():
            error_response = get_serializer_error_message(serializer.errors)
            return api_response(
                message=error_response['message'],
                message_type='error',
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            updated_instance = serializer.save()
            # Check if phone update was attempted and failed
            if hasattr(updated_instance, 'phone_update_success') and not updated_instance.phone_update_success:
                return api_response(
                    message=updated_instance.phone_update_error['message'],
                    message_type='error',
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            return api_response(
                message='Profile updated successfully.',
                message_type='success',
                status_code=status.HTTP_200_OK
            )
        except serializers.ValidationError as e:
            return api_response(
                message=e.detail.get('message', 'Failed to update profile.'),
                message_type='error',
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Profile update error: {str(e)}")
            return api_response(
                message='Failed to update profile. Please try again.',
                message_type='error',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class TeacherRegisterView(generics.CreateAPIView):
    """Allows admin to register a teacher with course assignments and schedules."""
    serializer_class = TeacherCreateSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    @swagger_auto_schema(
        operation_description="Register a new teacher with course assignments and schedules (Admin only)",
        request_body=TeacherCreateSerializer,
        responses={
            201: openapi.Response(
                description="Teacher registered successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error']),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'email': openapi.Schema(type=openapi.TYPE_STRING),
                                'first_name': openapi.Schema(type=openapi.TYPE_STRING),
                                'last_name': openapi.Schema(type=openapi.TYPE_STRING),
                                'phone_number': openapi.Schema(type=openapi.TYPE_STRING),
                                'role': openapi.Schema(type=openapi.TYPE_STRING),
                                'schedules': openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Items(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            'course_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                            'batch': openapi.Schema(type=openapi.TYPE_STRING),
                                            'sessions': openapi.Schema(
                                                type=openapi.TYPE_ARRAY,
                                                items=openapi.Items(
                                                    type=openapi.TYPE_OBJECT,
                                                    properties={
                                                        'class_id': openapi.Schema(type=openapi.TYPE_STRING, format='uuid'),
                                                        'start_time': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                                                        'end_time': openapi.Schema(type=openapi.TYPE_STRING, format='date-time')
                                                    }
                                                )
                                            )
                                        }
                                    )
                                )
                            }
                        )
                    }
                )
            ),
            400: openapi.Response(
                description="Invalid input",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'])
                    }
                )
            ),
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="Forbidden"),
            500: openapi.Response(
                description="Server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'])
                    }
                )
            )
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            error_response = get_serializer_error_message(serializer.errors)
            logger.error(f"Teacher registration validation error: {error_response['message']}")
            return api_response(
                message=error_response['message'],
                message_type='error',
                status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            teacher = serializer.save()
            schedules = []
            for schedule in ClassSchedule.objects.filter(teacher=teacher):
                sessions = ClassSession.objects.filter(schedule=schedule).values('class_id', 'start_time', 'end_time')
                schedules.append({
                    'course_id': schedule.course.id,
                    'batch': schedule.batch,
                    'sessions': list(sessions)
                })

            data = {
                'id': teacher.id,
                'email': teacher.email,
                'first_name': teacher.first_name,
                'last_name': teacher.last_name,
                'phone_number': teacher.phone_number,
                'role': teacher.role,
                'schedules': schedules
            }
            return api_response(
                message='Teacher registered successfully.',
                message_type='success',
                status_code=status.HTTP_201_CREATED
            )
        except Exception as e:
            logger.error(f"Error registering teacher: {str(e)}")
            return api_response(
                message=f'Failed to register teacher: {str(e)}',
                message_type='error',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class AdminRegisterView(generics.CreateAPIView):
    """Registers a new admin user by any user."""
    queryset = User.objects.all()
    serializer_class = AdminCreateSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    
    @swagger_auto_schema(
        operation_description="Register a new admin account (restricted to admins)",
        responses={
            201: openapi.Response(
                description="Admin registration successful",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error']),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'access': openapi.Schema(type=openapi.TYPE_STRING),
                                'refresh': openapi.Schema(type=openapi.TYPE_STRING),
                                'user': openapi.Schema(type=openapi.TYPE_OBJECT)
                            }
                        )
                    }
                )
            ),
            400: openapi.Response(
                description="Invalid input",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'])
                    }
                )
            ),
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="Forbidden"),
            500: openapi.Response(
                description="Server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'])
                    }
                )
            )
        }
    )
    def post(self, request, *args, **kwargs):
        """Creates an admin user with JWT tokens."""
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            error_response = get_serializer_error_message(serializer.errors)
            logger.error(f"Admin registration validation error: {error_response['message']}")
            return api_response(
                message=error_response['message'],
                message_type='error',
                status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            user_data = UserSerializer(user, context={'request': request}).data
            data = {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': user_data
            }
            return api_response(
                message='Admin registered successfully.',
                message_type='success',
                data=data,
                status_code=status.HTTP_201_CREATED
            )
        except Exception as e:
            logger.error(f"Admin registration error: {str(e)}")
            return api_response(
                message='Failed to register admin. Please try again.',
                message_type='error',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ChangePasswordView(generics.GenericAPIView):
    serializer_class = ChangePasswordSerializer
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Change user password",
        request_body=ChangePasswordSerializer,
        responses={
            200: openapi.Response(
                description="Password changed successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'])
                    }
                )
            ),
            400: openapi.Response(
                description="Invalid input",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'])
                    }
                )
            ),
            401: openapi.Response(description="Unauthorized")
        }
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            error_response = get_serializer_error_message(serializer.errors)
            return api_response(
                message=error_response['message'],
                message_type='error',
                status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            serializer.save()
            return api_response(
                message='Password changed successfully.',
                message_type='success',
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Change password error: {str(e)}")
            return api_response(
                message='Failed to change password. Please try again.',
                message_type='error',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ForgotPasswordView(generics.GenericAPIView):
    serializer_class = ForgotPasswordSerializer
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="Reset user password using OTP",
        request_body=ForgotPasswordSerializer,
        responses={
            200: openapi.Response(
                description="Password reset successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'])
                    }
                )
            ),
            400: openapi.Response(
                description="Invalid input or OTP",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'])
                    }
                )
            ),
            500: openapi.Response(
                description="Server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'])
                    }
                )
            )
        }
    )

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            error_response = get_serializer_error_message(serializer.errors)
            return api_response(
                message=error_response['message'],
                message_type='error',
                status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            serializer.save()
            return api_response(
                message='Password reset successfully. Please login with your new password.',
                message_type='success',
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Password reset error: {str(e)}")
            return api_response(
                message='Failed to reset password. Please try again.',
                message_type='error',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ListTeachersView(generics.ListAPIView):
    serializer_class = TeacherProfileSerializer
    permission_classes = [IsAuthenticated]
    queryset = TeacherProfile.objects.all()

    @swagger_auto_schema(
        operation_description="List all teachers with their profiles",
        responses={
            200: openapi.Response(
                description="Teachers retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error']),
                        'data': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Items(type=openapi.TYPE_OBJECT)
                        )
                    }
                )
            ),
            401: openapi.Response(description="Unauthorized"),
            500: openapi.Response(
                description="Server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'])
                    }
                )
            )
        }
    )
    def get(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True, context={'request': request, 'is_nested': False})
            return api_response(
                message='Teachers retrieved successfully.',
                message_type='success',
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"List teachers error: {str(e)}")
            return api_response(
                message='Failed to retrieve teachers. Please try again.',
                message_type='error',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ListStudentsView(generics.ListAPIView):
    serializer_class = StudentProfileSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = StudentProfile.objects.all()

    @swagger_auto_schema(
        operation_description="List all students with their profiles (Admin only)",
        responses={
            200: openapi.Response(
                description="Students retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error']),
                        'data': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Items(type=openapi.TYPE_OBJECT)
                        )
                    }
                )
            ),
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="Forbidden"),
            500: openapi.Response(
                description="Server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'])
                    }
                )
            )
        }
    )
    def get(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True, context={'request': request, 'is_nested': False})
            return api_response(
                message='Students retrieved successfully.',
                message_type='success',
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"List students error: {str(e)}")
            return api_response(
                message='Failed to retrieve students. Please try again.',
                message_type='error',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class TrialStatusView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsStudent]
    
    @swagger_auto_schema(
        operation_description="Retrieve trial status for the authenticated student",
        responses={
            200: openapi.Response(
                description="Trial status retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error']),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'is_trial': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                'trial_ends_at': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                                'trial_remaining_seconds': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'has_purchased': openapi.Schema(type=openapi.TYPE_BOOLEAN)
                            }
                        )
                    }
                )
            ),
            401: openapi.Response(description="Unauthorized"),
            403: openapi.Response(description="Forbidden"),
            500: openapi.Response(
                description="Server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'message_type': openapi.Schema(type=openapi.TYPE_STRING, enum=['success', 'error'])
                    }
                )
            )
        }
    )

    def get(self, request):
        """Returns trial status and purchased courses count for students."""
        user = request.user

        try:

            purchased_count = CourseSubscription.objects.filter(
                student=user,
                payment_status='completed'
            ).count()

            data = {
                'is_trial': not user.has_purchased_courses,
                'has_purchased': user.has_purchased_courses,
                'purchased_count': purchased_count
            }
            
            if not user.has_purchased_courses and user.trial_end_date:
                data['trial_ends_at'] = user.trial_end_date.isoformat()
                data['trial_remaining_seconds'] = user.trial_remaining_seconds
            return api_response(
                message='Trial status retrieved successfully.',
                message_type='success',
                data=data,
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Trial status error for user {user.id}: {str(e)}")
            return api_response(
                message='Failed to retrieve trial status. Please try again.',
                message_type='error',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )