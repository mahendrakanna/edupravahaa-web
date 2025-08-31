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
from edu_platform.models import User, OTP, CourseSubscription, ClassSchedule
from edu_platform.utility.email_services import send_otp_email
from edu_platform.utility.sms_services import get_sms_service, ConsoleSMSService
from edu_platform.serializers.auth_serializers import (
    UserSerializer, RegisterSerializer, LoginSerializer,
    TeacherCreateSerializer, ChangePasswordSerializer,
    SendOTPSerializer, VerifyOTPSerializer,
    ForgotPasswordSerializer, AdminCreateSerializer, AssignedCourseSerializer
)
import logging
import phonenumbers

logger = logging.getLogger(__name__)

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
                        'otp_expires_in_seconds': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'debug_otp': openapi.Schema(type=openapi.TYPE_STRING, description="OTP code (debug mode only)")
                    }
                )
            ),
            400: openapi.Response(
                description="Invalid input",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER, description="HTTP status code")
                    }
                )
            ),
            500: openapi.Response(
                description="Server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER, description="HTTP status code")
                    }
                )
            )
        }
    )
    
    def post(self, request):
        """Sends OTP via email or SMS with auto-detection of identifier type."""
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            error_message = 'Invalid input data.'
            if 'identifier' in serializer.errors:
                if isinstance(serializer.errors['identifier'], dict) and 'error' in serializer.errors['identifier']:
                    error_message = serializer.errors['identifier']['error']
                elif isinstance(serializer.errors['identifier'], list):
                    error_message = serializer.errors['identifier'][0]
            elif 'non_field_errors' in serializer.errors:
                error_message = serializer.errors['non_field_errors'][0]
            elif serializer.errors:
                error_message = list(serializer.errors.values())[0][0] if isinstance(list(serializer.errors.values())[0], list) else list(serializer.errors.values())[0]
            return Response({
                'error': error_message,
                'status': status.HTTP_400_BAD_REQUEST
            }, status=status.HTTP_400_BAD_REQUEST)
        
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
            return Response({
                'error': 'Failed to create OTP. Please try again.',
                'status': status.HTTP_500_INTERNAL_SERVER_ERROR
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        if identifier_type == 'email':
            # Use Twilio SendGrid for email
            
            email_sent = send_otp_email(identifier, otp.otp_code, purpose)
            
            # Handle email sending failure in production
            if not email_sent and not settings.DEBUG:
                return Response({
                    'error': 'Failed to send email. Please try again.',
                    'status': status.HTTP_500_INTERNAL_SERVER_ERROR
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            response_data = {
                'message': f'OTP sent to email {identifier}.',
                'otp_expires_in_seconds': int((otp.expires_at - timezone.now()).total_seconds())
            }
            return Response(response_data, status=status.HTTP_200_OK)
            
        else:  # phone
            # Send SMS using configured service
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
                    return Response({
                        'error': 'Failed to send SMS. Please try again.',
                        'status': status.HTTP_500_INTERNAL_SERVER_ERROR
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            except Exception as e:
                logger.error(f"SMS sending error: {str(e)}")
                if not settings.DEBUG:
                    return Response({
                        'error': 'SMS service unavailable.',
                        'status': status.HTTP_500_INTERNAL_SERVER_ERROR
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                using_console = True
            
            response_data = {
                'message': f'OTP sent to phone {identifier}.',
                'otp_expires_in_seconds': int((otp.expires_at - timezone.now()).total_seconds())
            }
            if settings.DEBUG and using_console:
                response_data['debug_otp'] = otp.otp_code
            return Response(response_data, status=status.HTTP_200_OK)


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
                        'identifier': openapi.Schema(type=openapi.TYPE_STRING),
                        'identifier_type': openapi.Schema(type=openapi.TYPE_STRING),
                        'verified': openapi.Schema(type=openapi.TYPE_BOOLEAN)
                    }
                )
            ),
            400: openapi.Response(
                description="Invalid OTP or input",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER, description="HTTP status code")
                    }
                )
            ),
            500: openapi.Response(
                description="Server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER, description="HTTP status code")
                    }
                )
            )
        }
    )
    def post(self, request):
        """Validates and marks OTP as verified."""
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            error_message = 'Invalid input data.'
            if 'identifier' in serializer.errors:
                if isinstance(serializer.errors['identifier'], dict) and 'error' in serializer.errors['identifier']:
                    error_message = serializer.errors['identifier']['error']
                elif isinstance(serializer.errors['identifier'], list):
                    error_message = serializer.errors['identifier'][0]
            elif 'non_field_errors' in serializer.errors:
                error_message = serializer.errors['non_field_errors'][0]
            elif serializer.errors:
                error_message = list(serializer.errors.values())[0][0] if isinstance(list(serializer.errors.values())[0], list) else list(serializer.errors.values())[0]
            return Response({
                'error': error_message,
                'status': status.HTTP_400_BAD_REQUEST
            }, status=status.HTTP_400_BAD_REQUEST)
        
        identifier = serializer.validated_data['identifier']
        otp_code = serializer.validated_data['otp_code']
        purpose = serializer.validated_data['purpose']
        identifier_type = serializer.initial_data['identifier_type']
        
        otp = serializer.validated_data.get('otp')
        if not otp:
            return Response({
                'error': 'Invalid OTP.',
                'status': status.HTTP_400_BAD_REQUEST
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            otp.is_verified = True
            otp.save()
        except Exception as e:
            logger.error(f"OTP verification error: {str(e)}")
            return Response({
                'error': 'Failed to verify OTP. Please try again.',
                'status': status.HTTP_500_INTERNAL_SERVER_ERROR
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({
            'message': f'{identifier_type.capitalize()} verified successfully.',
            'identifier': identifier,
            'identifier_type': identifier_type,
            'verified': True
        }, status=status.HTTP_200_OK)


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
                        'trial_info': openapi.Schema(
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
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER, description="HTTP status code")
                    }
                )
            ),
            500: openapi.Response(
                description="Server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER, description="HTTP status code")
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
            error_message = 'Invalid registration data.'
            if 'username' in serializer.errors and isinstance(serializer.errors['username'], list):
                error_message = serializer.errors['username'][0]
            elif 'email' in serializer.errors and isinstance(serializer.errors['email'], dict) and 'error' in serializer.errors['email']:
                error_message = serializer.errors['email']['error']
            elif 'phone_number' in serializer.errors and isinstance(serializer.errors['phone_number'], dict) and 'error' in serializer.errors['phone_number']:
                error_message = serializer.errors['phone_number']['error']
            elif 'non_field_errors' in serializer.errors:
                error_message = serializer.errors['non_field_errors'][0]
            elif serializer.errors:
                error_message = list(serializer.errors.values())[0][0] if isinstance(list(serializer.errors.values())[0], list) else list(serializer.errors.values())[0]
            return Response({
                'error': error_message,
                'status': status.HTTP_400_BAD_REQUEST
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = serializer.save()
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            return Response({
                'error': 'Failed to register user. Please try again.',
                'status': status.HTTP_500_INTERNAL_SERVER_ERROR
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        response_data = {
            'message': 'Registration successful! Please login to continue.',
        }
        if user.role == 'student' and user.trial_end_date:
            response_data['trial_info'] = {
                'trial_ends_at': user.trial_end_date.isoformat(),
                'trial_duration_seconds': user.trial_remaining_seconds
            }
        
        return Response(response_data, status=status.HTTP_201_CREATED)


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
                        'access': openapi.Schema(type=openapi.TYPE_STRING),
                        'refresh': openapi.Schema(type=openapi.TYPE_STRING),
                        'user_type': openapi.Schema(type=openapi.TYPE_STRING),
                        'is_trial': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'has_purchased': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'trial_ends_at': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                        'trial_remaining_seconds': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'assigned_courses': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_OBJECT))
                    }
                )
            ),
            400: openapi.Response(
                description="Invalid input or credentials",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER, description="HTTP status code")
                    }
                )
            ),
            403: openapi.Response(
                description="Account disabled",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER, description="HTTP status code")
                    }
                )
            ),
            500: openapi.Response(
                description="Server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER, description="HTTP status code")
                    }
                )
            )
        }
    )
    def post(self, request):
        """Authenticates user and returns JWT tokens with trial info for students and assigned courses for teachers."""
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            error_message = 'Invalid login credentials.'
            if 'identifier' in serializer.errors and isinstance(serializer.errors['identifier'], dict) and 'error' in serializer.errors['identifier']:
                error_message = serializer.errors['identifier']['error']
            elif 'identifier' in serializer.errors and isinstance(serializer.errors['identifier'], list):
                error_message = serializer.errors['identifier'][0]
            elif 'non_field_errors' in serializer.errors:
                error_message = serializer.errors['non_field_errors'][0]
            elif serializer.errors:
                error_message = list(serializer.errors.values())[0][0] if isinstance(list(serializer.errors.values())[0], list) else list(serializer.errors.values())[0]
            return Response({
                'error': error_message,
                'status': status.HTTP_400_BAD_REQUEST
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = serializer.validated_data['user']
            if not user.is_active:
                return Response({
                    'error': 'User account is disabled.',
                    'status': status.HTTP_403_FORBIDDEN
                }, status=status.HTTP_403_FORBIDDEN)
                
            # Update last_login
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])
            
            refresh = RefreshToken.for_user(user)
            
            response_data = {
                'message': 'Login successful.',
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user_type': user.role
            }

            # Include trial info for students
            if user.role == 'student':
                response_data['is_trial'] = not user.has_purchased_courses
                response_data['has_purchased'] = user.has_purchased_courses
                
                if not user.has_purchased_courses and user.trial_end_date:
                    response_data['trial_ends_at'] = user.trial_end_date.isoformat()
                    response_data['trial_remaining_seconds'] = user.trial_remaining_seconds
            
            # Include assigned courses for teachers
            if user.role == 'teacher':
                schedules = ClassSchedule.objects.filter(teacher=user)
                response_data['assigned_courses'] = AssignedCourseSerializer(schedules, many=True).data

            return Response(response_data, status=status.HTTP_200_OK)
        
        except Exception as e:
            # Log and handle unexpected errors
            logger.error(f"Login error: {str(e)}")
            return Response({
                'error': 'An unexpected error occurred during login. Please try again.',
                'status': status.HTTP_500_INTERNAL_SERVER_ERROR
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
                        'message': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            400: openapi.Response(
                description="Invalid token",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER, description="HTTP status code")
                    }
                )
            )
        }
    )
    def post(self, request):
        """Blacklists refresh token to log out user."""
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({
                'error': 'Refresh token is required.',
                'status': status.HTTP_400_BAD_REQUEST
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({
                'message': 'Logout successful.'
            }, status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            return Response({
                'error': 'Invalid refresh token.',
                'status': status.HTTP_400_BAD_REQUEST
            }, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(generics.RetrieveUpdateAPIView):
    """Manages retrieval and updates of user profile."""
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        responses={
            200: openapi.Response(
                description="Profile retrieved or updated successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'data': openapi.Schema(type=openapi.TYPE_OBJECT)
                    }
                )
            ),
            400: openapi.Response(
                description="Invalid input",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER, description="HTTP status code")
                    }
                )
            ),
            500: openapi.Response(
                description="Server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER, description="HTTP status code")
                    }
                )
            )
        }
    )
    def get(self, request, *args, **kwargs):
        """Retrieves authenticated user's profile."""
        serializer = self.get_serializer(self.get_object())
        return Response({
            'message': 'Profile retrieved successfully.',
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    
    def put(self, request, *args, **kwargs):
        """Updates authenticated user's profile."""
        serializer = self.get_serializer(self.get_object(), data=request.data, partial=True)
        if not serializer.is_valid():
            error_message = 'Invalid profile update data.'
            if 'email' in serializer.errors and isinstance(serializer.errors['email'], dict) and 'error' in serializer.errors['email']:
                error_message = serializer.errors['email']['error']
            elif 'phone_number' in serializer.errors and isinstance(serializer.errors['phone_number'], dict) and 'error' in serializer.errors['phone_number']:
                error_message = serializer.errors['phone_number']['error']
            elif 'non_field_errors' in serializer.errors:
                error_message = serializer.errors['non_field_errors'][0]
            elif serializer.errors:
                error_message = list(serializer.errors.values())[0][0] if isinstance(list(serializer.errors.values())[0], list) else list(serializer.errors.values())[0]
            return Response({
                'error': error_message,
                'status': status.HTTP_400_BAD_REQUEST
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            serializer.save()
            return Response({
                'message': 'Profile updated successfully.',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Profile update error: {str(e)}")
            return Response({
                'error': 'Failed to update profile. Please try again.',
                'status': status.HTTP_500_INTERNAL_SERVER_ERROR
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get_object(self):
        """Returns the authenticated user."""
        return self.request.user


class TeacherRegisterView(generics.CreateAPIView):
    """Registers a new teacher user by admin."""
    queryset = User.objects.all()
    serializer_class = TeacherCreateSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    
    @swagger_auto_schema(
        operation_description="Register a new teacher account by admin",
        responses={
            201: openapi.Response(
                description="Teacher registration successful",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'data': openapi.Schema(type=openapi.TYPE_OBJECT)
                    }
                )
            ),
            400: openapi.Response(
                description="Invalid input",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER, description="HTTP status code"),
                        'errors': openapi.Schema(type=openapi.TYPE_OBJECT, description="Detailed field errors")
                    }
                )
            ),
            500: openapi.Response(
                description="Server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER, description="HTTP status code")
                    }
                )
            )
        }
    )
    def post(self, request, *args, **kwargs):
        """Creates a teacher user and returns detailed profile data."""
        logger.debug(f"Received teacher registration request: {request.data}")
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            errors = serializer.errors
            error_message = 'Invalid teacher registration data.'
            detailed_errors = {}
            
            # Extract specific field errors
            for field, error in errors.items():
                if isinstance(error, list):
                    detailed_errors[field] = error[0]
                elif isinstance(error, dict) and 'error' in error:
                    detailed_errors[field] = error['error']
                else:
                    detailed_errors[field] = str(error)
            
            # Fallback to generic message if no specific field error
            if not detailed_errors:
                if 'non_field_errors' in errors:
                    error_message = errors['non_field_errors'][0]
                elif errors:
                    error_message = list(errors.values())[0][0] if isinstance(list(errors.values())[0], list) else list(errors.values())[0]
            
            logger.error(f"Teacher registration validation error: {detailed_errors or error_message}")
            return Response({
                'error': error_message,
                'status': status.HTTP_400_BAD_REQUEST,
                'errors': detailed_errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = serializer.save()
            logger.info(f"Teacher created successfully: {user.id}")
            return Response({
                'message': 'Teacher created successfully.',
                'data': UserSerializer(user, context={'request': request}).data
            }, status=status.HTTP_201_CREATED)
        except serializers.ValidationError as e:
            logger.error(f"Teacher registration validation error: {str(e)}")
            return Response({
                'error': str(e),
                'status': status.HTTP_400_BAD_REQUEST,
                'errors': {}
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Teacher registration error: {str(e)}")
            return Response({
                'error': f'Failed to register teacher: {str(e)}',
                'status': status.HTTP_500_INTERNAL_SERVER_ERROR
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminRegisterView(generics.CreateAPIView):
    """Registers a new admin user by any user (including unauthorized)."""
    queryset = User.objects.all()
    serializer_class = AdminCreateSerializer
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="Register a new admin account (accessible to all users, including unauthorized)",
        responses={
            201: openapi.Response(
                description="Admin registration successful",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'access': openapi.Schema(type=openapi.TYPE_STRING),
                        'refresh': openapi.Schema(type=openapi.TYPE_STRING),
                        'user': openapi.Schema(type=openapi.TYPE_OBJECT)
                    }
                )
            ),
            400: openapi.Response(
                description="Invalid input",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER, description="HTTP status code"),
                        'errors': openapi.Schema(type=openapi.TYPE_OBJECT, description="Detailed field errors")
                    }
                )
            ),
            500: openapi.Response(
                description="Server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER, description="HTTP status code")
                    }
                )
            )
        }
    )
    def post(self, request, *args, **kwargs):
        """Creates an admin user with JWT tokens."""
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            errors = serializer.errors
            error_message = 'Invalid admin registration data.'
            detailed_errors = {}
            
            # Extract specific field errors
            for field, error in errors.items():
                if isinstance(error, list):
                    detailed_errors[field] = error[0]
                elif isinstance(error, dict) and 'error' in error:
                    detailed_errors[field] = error['error']
                else:
                    detailed_errors[field] = str(error)
            
            # Fallback to generic message if no specific field error
            if not detailed_errors:
                if 'non_field_errors' in errors:
                    error_message = errors['non_field_errors'][0]
                elif errors:
                    error_message = list(errors.values())[0][0] if isinstance(list(errors.values())[0], list) else list(errors.values())[0]
            
            logger.error(f"Admin registration validation error: {detailed_errors or error_message}")
            return Response({
                'error': error_message,
                'status': status.HTTP_400_BAD_REQUEST,
                'errors': detailed_errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            response_data = {
                'message': 'Admin registration successful.',
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': user.role,
                    'first_name': user.first_name,
                    'last_name': user.last_name
                }
            }
            return Response(response_data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Admin registration error: {str(e)}")
            return Response({
                'error': 'Failed to register admin. Please try again.',
                'status': status.HTTP_500_INTERNAL_SERVER_ERROR
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ListTeachersView(generics.ListAPIView):
    """Lists all teacher users for admin."""
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    
    @swagger_auto_schema(
        responses={
            200: openapi.Response(
                description="Teachers retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'data': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_OBJECT))
                    }
                )
            ),
            500: openapi.Response(
                description="Server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER, description="HTTP status code")
                    }
                )
            )
        }
    )
    def get(self, request, *args, **kwargs):
        """Returns all teacher users."""
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'message': 'Teachers retrieved successfully.',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"List teachers error: {str(e)}")
            return Response({
                'error': 'Failed to retrieve teachers. Please try again.',
                'status': status.HTTP_500_INTERNAL_SERVER_ERROR
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get_queryset(self):
        """Returns all teacher users."""
        return User.objects.filter(role='teacher')


class ListStudentsView(generics.ListAPIView):
    """Lists all student users for admin."""
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    
    @swagger_auto_schema(
        responses={
            200: openapi.Response(
                description="Students retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'data': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_OBJECT))
                    }
                )
            ),
            500: openapi.Response(
                description="Server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER, description="HTTP status code")
                    }
                )
            )
        }
    )
    def get(self, request, *args, **kwargs):
        """Returns all student users."""
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                'message': 'Students retrieved successfully.',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"List students error: {str(e)}")
            return Response({
                'error': 'Failed to retrieve students. Please try again.',
                'status': status.HTTP_500_INTERNAL_SERVER_ERROR
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get_queryset(self):
        """Returns all student users."""
        return User.objects.filter(role='student')


class ChangePasswordView(generics.UpdateAPIView):
    """Changes authenticated user's password."""
    serializer_class = ChangePasswordSerializer
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        responses={
            200: openapi.Response(
                description="Password changed successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            400: openapi.Response(
                description="Invalid input",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER, description="HTTP status code")
                    }
                )
            ),
            500: openapi.Response(
                description="Server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER, description="HTTP status code")
                    }
                )
            )
        }
    )
    def update(self, request, *args, **kwargs):
        """Updates user's password."""
        # Validate password change data
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            error_message = 'Invalid password change data.'
            if 'old_password' in serializer.errors and isinstance(serializer.errors['old_password'], dict) and 'error' in serializer.errors['old_password']:
                error_message = serializer.errors['old_password']['error']
            elif 'new_password' in serializer.errors and isinstance(serializer.errors['new_password'], dict) and 'error' in serializer.errors['new_password']:
                error_message = serializer.errors['new_password']['error']
            elif 'non_field_errors' in serializer.errors:
                error_message = serializer.errors['non_field_errors'][0]
            elif serializer.errors:
                error_message = list(serializer.errors.values())[0][0] if isinstance(list(serializer.errors.values())[0], list) else list(serializer.errors.values())[0]
            return Response({
                'error': error_message,
                'status': status.HTTP_400_BAD_REQUEST
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            serializer.save()
            return Response({
                'message': 'Password changed successfully.'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Password change error: {str(e)}")
            return Response({
                'error': 'Failed to change password. Please try again.',
                'status': status.HTTP_500_INTERNAL_SERVER_ERROR
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get_object(self):
        """Returns the authenticated user."""
        return self.request.user


class ForgotPasswordView(generics.GenericAPIView):
    """Resets password using OTP."""
    permission_classes = [AllowAny]
    serializer_class = ForgotPasswordSerializer
    
    @swagger_auto_schema(
        request_body=ForgotPasswordSerializer,
        operation_description="Reset password using OTP",
        responses={
            200: openapi.Response(
                description="Password reset successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            400: openapi.Response(
                description="Invalid input or OTP",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER, description="HTTP status code")
                    }
                )
            ),
            500: openapi.Response(
                description="Server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER, description="HTTP status code")
                    }
                )
            )
        }
    )
    def post(self, request):
        """Resets user's password after OTP verification."""
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            error_message = 'Invalid password reset data.'
            if 'identifier' in serializer.errors and isinstance(serializer.errors['identifier'], dict) and 'error' in serializer.errors['identifier']:
                error_message = serializer.errors['identifier']['error']
            elif 'new_password' in serializer.errors and isinstance(serializer.errors['new_password'], dict) and 'error' in serializer.errors['new_password']:
                error_message = serializer.errors['new_password']['error']
            elif 'non_field_errors' in serializer.errors:
                error_message = serializer.errors['non_field_errors'][0]
            elif serializer.errors:
                error_message = list(serializer.errors.values())[0][0] if isinstance(list(serializer.errors.values())[0], list) else list(serializer.errors.values())[0]
            return Response({
                'error': error_message,
                'status': status.HTTP_400_BAD_REQUEST
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            serializer.save()
            return Response({
                'message': 'Password reset successfully.'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Password reset error: {str(e)}")
            return Response({
                'error': 'Failed to reset password. Please try again.',
                'status': status.HTTP_500_INTERNAL_SERVER_ERROR
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TrialStatusView(generics.GenericAPIView):
    """Retrieves trial status for authenticated student users."""
    permission_classes = [IsAuthenticated, IsStudent]
    
    @swagger_auto_schema(
        operation_description="Get trial status for frontend display",
        responses={
            200: openapi.Response(
                description="Trial status retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'is_trial': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'has_purchased': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'purchased_courses_count': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'trial_ends_at': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                        'remaining_seconds': openapi.Schema(type=openapi.TYPE_INTEGER)
                    }
                )
            ),
            403: openapi.Response(
                description="Unauthorized",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER, description="HTTP status code")
                    }
                )
            ),
            500: openapi.Response(
                description="Server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER, description="HTTP status code")
                    }
                )
            )
        }
    )
    def get(self, request):
        """Returns trial status and purchased courses count for students."""
        user = request.user
        
        # Non-students have no trial
        if user.role != 'student':
            return Response({
                'message': 'Trial status retrieved successfully.',
                'is_trial': False,
                'has_purchased': False,
                'purchased_courses_count': 0
            }, status=status.HTTP_200_OK)
        
        try:
            purchased_count = CourseSubscription.objects.filter(
                student=user,
                payment_status='completed'
            ).count()
            
            response_data = {
                'message': 'Trial status retrieved successfully.',
                'is_trial': not user.has_purchased_courses,
                'has_purchased': user.has_purchased_courses,
                'purchased_courses_count': purchased_count
            }
            
            if not user.has_purchased_courses and user.trial_end_date:
                response_data['trial_ends_at'] = user.trial_end_date.isoformat()
                response_data['remaining_seconds'] = user.trial_remaining_seconds
            
            return Response(response_data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Trial status error: {str(e)}")
            return Response({
                'error': 'Failed to retrieve trial status. Please try again.',
                'status': status.HTTP_500_INTERNAL_SERVER_ERROR
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)