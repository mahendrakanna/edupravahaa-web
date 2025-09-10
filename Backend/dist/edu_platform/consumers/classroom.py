import json
import logging
import os
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.exceptions import PermissionDenied
import redis.asyncio as redis
import asyncio  # For timeout

logger = logging.getLogger(__name__)

class ClassRoomConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Lazy imports to avoid AppRegistryNotReady
        from edu_platform.models import ClassSchedule, CourseSubscription
        from django.contrib.auth import get_user_model
        User = get_user_model()  # ✅ Lazy import
        user = self.scope['user']

        self.class_id = self.scope['url_route']['kwargs']['class_id']
        self.group_name = f'class_{self.class_id}'

        # Log connection attempt
        logger.debug(f"WebSocket connection attempt: class_id={self.class_id}, user={user}")

        # Check authentication
        if not user.is_authenticated:
            logger.warning(f"Unauthorized connection attempt: class_id={self.class_id}")
            await self.close(code=4001)
            return

        # Verify eligibility
        logger.debug("Starting eligibility check")
        eligible = await self.is_eligible(user)
        logger.debug(f"Eligibility result: {eligible}")
        if not eligible:
            logger.warning(f"Forbidden connection attempt: user={user.email}, class_id={self.class_id}")
            await self.close(code=4003)
            return

        # Connect to Redis and add user (with timeout to prevent hang)
        logger.debug("Starting Redis connection")
        self.redis_client = redis.Redis(
            host=os.environ.get('REDIS_HOST', 'localhost'),
            port=6379,
            db=0,
            decode_responses=True
        )
        try:
            await asyncio.wait_for(self.redis_client.sadd(f'class:{self.class_id}:participants', user.id), timeout=5.0)
            logger.debug("Redis sadd complete")
        except asyncio.TimeoutError:
            logger.error(f"Redis timeout for class_id={self.class_id}")
            await self.close(code=4002)  # Custom code for Redis failure
            return
        except Exception as e:
            logger.error(f"Redis error: {e}")
            await self.close(code=4002)
            return

        # Add user to WebSocket group
        logger.debug("Starting group add")
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        logger.debug("Group add complete")

        await self.accept()
        logger.debug("WebSocket accepted")

        # Notify group
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'chat_message',
                'message': f'{user.email} joined the class',
                'sender': 'system',
            }
        )
        logger.info(f"User {user.email} connected to class {self.class_id}")

    async def disconnect(self, close_code):
        user = self.scope['user']

        if hasattr(self, 'group_name') and hasattr(self, 'redis_client'):
            # Remove from Redis
            try:
                await self.redis_client.srem(f'class:{self.class_id}:participants', user.id)
                await self.redis_client.close()
            except Exception as e:
                logger.error(f"Redis cleanup error: {e}")

            # Remove from group
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

            # Notify group
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'chat_message',
                    'message': f'{user.email} left the class',
                    'sender': 'system',
                }
            )
            logger.info(f"User {user.email} disconnected from class {self.class_id}, code={close_code}")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            logger.debug(f"Received message: class_id={self.class_id}, type={message_type}")

            if message_type == 'chat':
                message = data.get('message', '').strip()
                if not message or len(message) > 500:
                    logger.warning(f"Invalid chat message: {message}")
                    return
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        'type': 'chat_message',
                        'message': message,
                        'sender': self.scope['user'].email,
                    }
                )

            elif message_type == 'emoji':
                emoji = data.get('emoji', '').strip()
                allowed_emojis = ['🙋', '👍', '👏', '😊']
                if emoji not in allowed_emojis:
                    logger.warning(f"Invalid emoji: {emoji}")
                    return
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        'type': 'chat_message',
                        'message': emoji,
                        'sender': self.scope['user'].email,
                        'is_emoji': True,
                    }
                )

            elif message_type == 'signaling':
                if not data.get('data'):
                    logger.warning(f"Invalid signaling data: {data}")
                    return
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        'type': 'signaling_message',
                        'data': data['data'],
                        'sender': self.scope['user'].email,
                    }
                )

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat',
            'message': event['message'],
            'sender': event['sender'],
            'is_emoji': event.get('is_emoji', False),
        }))

    async def signaling_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'signaling',
            'data': event['data'],
            'sender': event['sender'],
        }))

    @database_sync_to_async
    def is_eligible(self, user):
        # Lazy imports
        from edu_platform.models import ClassSchedule, CourseSubscription

        try:
            class_schedule = ClassSchedule.objects.get(id=self.class_id)
            if user.is_teacher:
                return ClassSchedule.objects.filter(id=self.class_id, teacher=user).exists()
            elif user.is_student:
                return CourseSubscription.objects.filter(
                    student=user,
                    course=class_schedule.course,
                    payment_status='completed',
                    is_active=True
                ).exists()
            return False
        except ClassSchedule.DoesNotExist:
            logger.error(f"ClassSchedule not found: id={self.class_id}")
            return False