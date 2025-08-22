"""
Email service for sending OTPs using Django's SMTP backend.
"""

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)


def send_otp_email(email, otp_code, purpose='registration'):
    """Sends OTP email with HTML and plain text versions."""
    # Set email subject based on purpose
    subject = f'Your OTP for {purpose.replace("_", " ").title()}'
    
    # Create HTML content for styled email
    html_message = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background-color: #4CAF50; color: white; padding: 20px; text-align: center;">
            <h1>EduStream</h1>
        </div>
        <div style="padding: 20px; background-color: #f9f9f9;">
            <h2>Verification Code</h2>
            <p>Hello,</p>
            <p>Your OTP verification code is:</p>
            <div style="background-color: #fff; padding: 20px; text-align: center; font-size: 32px; font-weight: bold; letter-spacing: 5px; margin: 20px 0; border: 2px dashed #4CAF50;">
                {otp_code}
            </div>
            <p style="color: #666;">This code will expire in 10 minutes.</p>
            <p style="color: #666;">Please do not share this code with anyone.</p>
            <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
            <p style="color: #999; font-size: 12px;">If you didn't request this code, please ignore this email.</p>
        </div>
        <div style="background-color: #333; color: white; padding: 10px; text-align: center; font-size: 12px;">
            © 2024 EduStream. All rights reserved.
        </div>
    </div>
    """
    
    # Create plain text version for fallback
    plain_message = f"""
        Hello,

        Your OTP verification code is: {otp_code}

        This code will expire in 10 minutes. Please do not share this code with anyone.

        If you didn't request this code, please ignore this email.

        Best regards,
        EduStream Team
    """
    
    try:
        # Send email using Django's SMTP backend
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"OTP email sent successfully to {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        # Fallback to console output in debug mode
        if settings.DEBUG:
            # In debug mode, print to console as fallback
            print(f"\n{'='*50}")
            print(f"Email to: {email}")
            print(f"Subject: {subject}")
            print(f"OTP Code: {otp_code}")
            print(f"{'='*50}\n")
            return True  # Return True in debug mode
        return False