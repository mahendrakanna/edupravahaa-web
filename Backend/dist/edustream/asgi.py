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
from socketio import ASGIApp

logger = logging.getLogger(__name__)

# Set DJANGO_SETTINGS_MODULE and initialize Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'edustream.settings')

# Initialize Django settings
django.setup()

# Import Django-dependent modules after setup
from edu_platform.routing import websocket_urlpatterns
from edu_platform.jwt_middleware import JwtAuthMiddlewareStack
from edustream.socketio_app import sio

django_asgi_app = get_asgi_application()
socketio_app = ASGIApp(sio)
channels_app = AllowedHostsOriginValidator(
    JwtAuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    )
)

async def application(scope, receive, send):
    if scope['type'] == 'http':
        # Route /socket.io/ HTTP requests (for polling) to Socket.IO
        if scope['path'].startswith('/socket.io/'):
            await socketio_app(scope, receive, send)
        else:
            # Route all other HTTP requests to Django
            await django_asgi_app(scope, receive, send)
    elif scope['type'] == 'websocket':
        # Route /socket.io/ WebSocket requests to Socket.IO
        if scope['path'].startswith('/socket.io/'):
            await socketio_app(scope, receive, send)
        else:
            # Route other WebSocket requests to Channels
            await channels_app(scope, receive, send)
    else:
        # Handle other protocols (e.g., lifespan) with Django
        await django_asgi_app(scope, receive, send)