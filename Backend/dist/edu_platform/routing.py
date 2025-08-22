"""Configures WebSocket routing for the classes app."""
from django.urls import re_path
from edu_platform.consumers import webrtc_consumers

websocket_urlpatterns = [
    # WebSocket endpoint for WebRTC signaling

    # Connects WebRTC signaling consumer for a specific room ID.
    re_path(r'ws/signal/(?P<room_id>\w+)/$', webrtc_consumers.WebRTCSignalingConsumer.as_asgi()),
]