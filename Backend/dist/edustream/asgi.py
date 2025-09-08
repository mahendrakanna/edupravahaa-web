"""
ASGI config for edustream project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os
import logging
import django
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application
from edu_platform.routing import websocket_urlpatterns

logger = logging.getLogger(__name__)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'edustream.settings')
# Ensure Django apps/settings are loaded
django.setup()  

# Import AFTER Django setup
from edu_platform.jwt_middleware import JwtAuthMiddlewareStack  

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
