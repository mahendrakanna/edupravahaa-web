"""
SMS service integration for sending OTPs using Twilio or console output.
"""

from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class TwilioSMSService:
    """Sends SMS using Twilio API."""
    
    def __init__(self):
        # Initialize Twilio client
        try:
            from twilio.rest import Client
            self.account_sid = settings.TWILIO_ACCOUNT_SID
            self.auth_token = settings.TWILIO_AUTH_TOKEN
            self.from_number = settings.TWILIO_PHONE_NUMBER
            self.client = Client(self.account_sid, self.auth_token)
        except ImportError:
            logger.error("Twilio not installed. Run: pip install twilio")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Twilio: {str(e)}")
            raise
    
    def send_sms(self, phone_number, message):
        """Sends SMS to the specified phone number."""
        try:
            # Send SMS via Twilio
            message = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=phone_number
            )
            logger.info(f"SMS sent successfully to {phone_number}. SID: {message.sid}")
            return True
        except Exception as e:
            logger.error(f"Failed to send SMS to {phone_number}: {str(e)}")
            return False


class ConsoleSMSService:
    """Mocks SMS service by printing to console for development."""
    
    def send_sms(self, phone_number, message):
        """Prints SMS content to console."""
        # Output SMS details to console
        print(f"\n{'='*50}")
        print(f"SMS to: {phone_number}")
        print(f"Message: {message}")
        print(f"{'='*50}\n")
        logger.info(f"SMS printed to console for {phone_number}")
        return True


def get_sms_service():
    """Returns the configured SMS service (Twilio or console)."""
    # Check for Twilio configuration
    if hasattr(settings, 'TWILIO_ACCOUNT_SID') and settings.TWILIO_ACCOUNT_SID:
        try:
            return TwilioSMSService()
        except Exception as e:
            # Fallback to console service on Twilio failure
            logger.warning(f"Failed to initialize Twilio, falling back to console: {str(e)}")
            return ConsoleSMSService()
    # Default to console service in development
    return ConsoleSMSService()