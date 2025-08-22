import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ClassSchedule, ClassAttendance
from payments.models import CourseSubscription

class WebRTCSignalingConsumer(AsyncWebsocketConsumer):
    """Handles WebRTC signaling for real-time class communication."""
    
    async def connect(self):
        """Establishes WebSocket connection and verifies user access."""
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'webrtc_{self.room_id}'
        self.user = self.scope['user']
        
        # Reject unauthenticated users
        if not self.user.is_authenticated:
            await self.close()
            return
        
        # Verify room access
        has_access = await self.check_room_access()
        if not has_access:
            await self.close()
            return
        
        # Add user to room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        # Accept WebSocket connection
        await self.accept()
        
        # Notify group of user joining
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_joined',
                'user_id': str(self.user.id),
                'username': self.user.get_full_name() or self.user.username,
                'role': self.user.role
            }
        )
    
    async def disconnect(self, close_code):
        """Handles WebSocket disconnection and notifies group."""
        # Remove user from room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
        # Notify group of user leaving
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_left',
                'user_id': str(self.user.id)
            }
        )
    
    async def receive(self, text_data):
        """Processes incoming WebRTC signaling messages."""
        data = json.loads(text_data)
        message_type = data.get('type')
        
        # Handle WebRTC offer
        if message_type == 'offer':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'webrtc_offer',
                    'offer': data['offer'],
                    'sender_id': str(self.user.id),
                    'target_id': data.get('target_id')
                }
            )
        
        # Handle WebRTC answer
        elif message_type == 'answer':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'webrtc_answer',
                    'answer': data['answer'],
                    'sender_id': str(self.user.id),
                    'target_id': data.get('target_id')
                }
            )
        
        # Handle ICE candidate exchange
        elif message_type == 'ice-candidate':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'webrtc_ice_candidate',
                    'candidate': data['candidate'],
                    'sender_id': str(self.user.id),
                    'target_id': data.get('target_id')
                }
            )
        
        # Handle session end by teacher
        elif message_type == 'end-session' and self.user.is_teacher:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'session_ended'
                }
            )
    
    async def user_joined(self, event):
        """Notifies client of a user joining the room."""
        await self.send(text_data=json.dumps({
            'type': 'user-joined',
            'user_id': event['user_id'],
            'username': event['username'],
            'role': event['role']
        }))
    
    async def user_left(self, event):
        """Notifies client of a user leaving the room."""
        await self.send(text_data=json.dumps({
            'type': 'user-left',
            'user_id': event['user_id']
        }))
    
    async def webrtc_offer(self, event):
        """Relays WebRTC offer to target user or all users."""
        # Send offer to target user or broadcast if no target
        if not event.get('target_id') or event['target_id'] == str(self.user.id):
            await self.send(text_data=json.dumps({
                'type': 'offer',
                'offer': event['offer'],
                'sender_id': event['sender_id']
            }))
    
    async def webrtc_answer(self, event):
        """Relays WebRTC answer to target user."""
        # Send answer only to target user
        if event['target_id'] == str(self.user.id):
            await self.send(text_data=json.dumps({
                'type': 'answer',
                'answer': event['answer'],
                'sender_id': event['sender_id']
            }))
    
    async def webrtc_ice_candidate(self, event):
        """Relays ICE candidate to target user or all users."""
        # Send ICE candidate to target user or broadcast if no target
        if not event.get('target_id') or event['target_id'] == str(self.user.id):
            await self.send(text_data=json.dumps({
                'type': 'ice-candidate',
                'candidate': event['candidate'],
                'sender_id': event['sender_id']
            }))
    
    async def session_ended(self, event):
        """Notifies client of session termination."""
        await self.send(text_data=json.dumps({
            'type': 'session-ended'
        }))
    
    @database_sync_to_async
    def check_room_access(self):
        """Verifies user access to the meeting room."""
        # Allow teachers to access their own class rooms
        if self.user.is_teacher:
            return ClassSchedule.objects.filter(
                meeting_room_id=self.room_id,
                teacher=self.user
            ).exists()
        
        # Allow students with valid course subscription
        if self.user.is_student:
            class_schedule = ClassSchedule.objects.filter(
                meeting_room_id=self.room_id
            ).first()
            
            if class_schedule:
                return CourseSubscription.objects.filter(
                    student=self.user,
                    course=class_schedule.course,
                    payment_status='completed'
                ).exists()
        
        # Allow admins to access any room
        return self.user.is_admin