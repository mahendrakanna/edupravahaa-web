"""
ASGI config for edustream project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os
import logging
import django
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from channels.auth import AuthMiddlewareStack

logger = logging.getLogger(__name__)

# Set Django settings module BEFORE importing anything else
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'edustream.settings')

# Initialize Django settings
django.setup()

# Now import app-specific modules (they can access settings)
from edu_platform.routing import websocket_urlpatterns
from edu_platform.jwt_middleware import JwtAuthMiddlewareStack  # Custom JWT stack

django_asgi_app = get_asgi_application()

logger.info("ASGI application starting with custom JWT middleware")

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        JwtAuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        )
    ),
})
