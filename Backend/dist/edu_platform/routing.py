"""Configures WebSocket routing for the edu_platform app."""

from django.urls import re_path
from edu_platform.consumers.classroom import ClassRoomConsumer

websocket_urlpatterns = [
    re_path(r'ws/class/(?P<class_id>\d+)/$', ClassRoomConsumer.as_asgi()),
]