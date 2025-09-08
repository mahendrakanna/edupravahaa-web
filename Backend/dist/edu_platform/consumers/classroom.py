import json
import logging
import os
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from edu_platform.models import ClassSchedule, CourseSubscription
from django.core.exceptions import PermissionDenied
import redis.asyncio as redis

logger = logging.getLogger(__name__)
User = get_user_model()

class ClassRoomConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Lazy imports to avoid AppRegistryNotReady
        from edu_platform.models import ClassSchedule, CourseSubscription
        from django.contrib.auth import get_user_model
        User = get_user_model()  # ✅ Lazy import
        user = self.scope['user']

        self.class_id = self.scope['url_route']['kwargs']['class_id']
        self.group_name = f'class_{self.class_id}'
        user = self.scope['user']

        # Log connection attempt
        logger.debug(f"WebSocket connection attempt: class_id={self.class_id}, user={user}")

        # Check authentication
        if user.is_anonymous or not user.is_authenticated:
            logger.warning(f"Unauthorized connection: class_id={self.class_id}, user={user}")
            await self.close(code=4001)  # Unauthorized
            return

        # Verify eligibility
        logger.debug("Starting eligibility check")
        eligible = await self.is_eligible(user)
        logger.debug(f"Eligibility result: {eligible}")
        if not eligible:
            logger.warning(f"Forbidden: user={user.email} not eligible for class_id={self.class_id}")
            await self.close(code=4003)  # Forbidden
            return

        # Add user to Redis set
        redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        await redis_client.sadd(f'class:{self.class_id}:participants', user.id)

        # Add to WebSocket group
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        logger.debug("Group add complete")

        await self.accept()
        logger.debug("WebSocket accepted")

        # Notify group of join
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
        if hasattr(self, 'group_name'):
            # Remove from Redis
            redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            await redis_client.srem(f'class:{self.class_id}:participants', self.scope['user'].id)

            # Remove from group
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

            # Notify group of leave
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'chat_message',
                    'message': f'{self.scope["user"].email} left the class',
                    'sender': 'system',
                }
            )
            logger.info(f"User {self.scope['user'].email} disconnected from class {self.class_id}, code={close_code}")

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
                signaling_data = data['data']
                logger.info(f"Signaling relay: sender={self.scope['user'].email}, type={signaling_data.get('type', 'unknown')}, target={data.get('target', 'group')}")
                # Broadcast to group (or specific target if 1:1)
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        'type': 'signaling_message',
                        'data': signaling_data,
                        'sender': self.scope['user'].email,
                        'target': data.get('target', 'group'),  # For future 1:1 targeting
                    }
                )

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            pass

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat',
            'message': event['message'],
            'sender': event['sender'],
            'is_emoji': event.get('is_emoji', False),
        }))

    async def signaling_message(self, event):
        # Enhanced for WebRTC: Log SDP/ICE details with safety checks
        data = event['data']
        if data.get('type') in ['offer', 'answer']:
            logger.debug(f"SDP {data['type']}: from {event['sender']}, candidate_count={len(data.get('candidates', [])) if 'candidates' in data else 'N/A'}")
        elif data.get('candidate') or (isinstance(data, dict) and 'candidate' in data):
            candidate_str = str(data.get('candidate', '')) if isinstance(data.get('candidate'), (str, dict)) else str(data)
            logger.debug(f"ICE Candidate: from {event['sender']}, candidate={candidate_str[:50]}...")
        
        await self.send(text_data=json.dumps({
            'type': 'signaling',
            'data': data,
            'sender': event['sender'],
        }))

    @database_sync_to_async
    def is_eligible(self, user):
        # Lazy imports
        from edu_platform.models import ClassSchedule, CourseSubscription

        try:
            class_schedule = ClassSchedule.objects.get(id=self.class_id)
            if user.is_teacher:
                return class_schedule.teacher_id == user.id
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