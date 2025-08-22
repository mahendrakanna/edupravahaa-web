from django.apps import AppConfig
import threading
import time
import logging

logger = logging.getLogger(__name__)

class EduPlatformConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'edu_platform'
    def ready(self):
        # Start background thread for trial cleanup
        # Only start if not in migration or other management commands
        import sys
        if 'runserver' in sys.argv:
            self.start_cleanup_thread()
    
    def start_cleanup_thread(self):
        """Start a background thread to cleanup expired trials"""
        def cleanup_loop():
            # Wait 10 seconds for Django to fully start
            time.sleep(10)
            
            while True:
                try:
                    from django.conf import settings
                    from django.utils import timezone
                    from django.db import connection
                    
                    # Ensure database connection is active
                    connection.ensure_connection()
                    
                    # Import here to avoid circular imports
                    from .models import User
                    
                    # Check trial mode for interval
                    if settings.TRIAL_SETTINGS.get('TEST_MODE', False):
                        interval = 30  # 30 seconds in test mode
                    else:
                        interval = 3600  # 1 hour in production
                    
                    # Find and delete expired trials
                    expired_users = User.objects.filter(
                        role='student',
                        has_purchased_courses=False,
                        trial_end_date__isnull=False,
                        trial_end_date__lt=timezone.now()
                    )
                    
                    deleted_emails = []
                    for user in expired_users:
                        deleted_emails.append(user.email)
                        user.delete()
                    
                    if deleted_emails:
                        logger.info(f"[AUTO-CLEANUP] Deleted {len(deleted_emails)} expired trials: {', '.join(deleted_emails)}")
                        print(f"[AUTO-CLEANUP] Deleted {len(deleted_emails)} expired trials: {', '.join(deleted_emails)}")
                    
                    # Wait for next interval
                    time.sleep(interval)
                    
                except Exception as e:
                    logger.error(f"Error in cleanup thread: {e}")
                    time.sleep(60)  # Wait a minute before retrying
        
        # Start thread as daemon so it stops when main process stops
        thread = threading.Thread(target=cleanup_loop, daemon=True, name="TrialCleanup")
        thread.start()
        print("[STARTUP] Background trial cleanup thread started (checking every 30 seconds in test mode)")
        logger.info("Started background trial cleanup thread")
