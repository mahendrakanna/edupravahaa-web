# edustream/socketio_app.py
import socketio
import os
import json
import redis.asyncio as aioredis
import logging
from nanoid import generate
from urllib.parse import parse_qs

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins=os.environ.get('ALLOW_ORIGIN', '*').strip('"'),
    logger=True,
    engineio_logger=True
)

redis_client = aioredis.Redis(
    host=os.environ.get('REDIS_HOST', 'localhost'),
    port=6379,
    db=0,
    decode_responses=True
)

async def test_redis():
    try:
        await redis_client.set('test_key', 'test_value')
        value = await redis_client.get('test_key')
        logger.info(f"Redis test: {value}")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")

import asyncio
asyncio.get_event_loop().create_task(test_redis())

class Rooms:
    @staticmethod
    async def create(room_data, user_id, class_id=None):
        id = room_data.get('id', '') if room_data.get('id', '').isalnum() else generate()
        if class_id:
            id = class_id
        await redis_client.hset(f'room:{id}', mapping={
            'name': room_data.get('name', f"Room by {room_data.get('created_by', id)}"),
            'created_by': room_data.get('created_by', ''),
            'opts': json.dumps(room_data.get('opts', {}))
        })
        await redis_client.sadd(f'class:{id}:participants', user_id)
        logger.debug(f"Room created: id={id}, user_id={user_id}")
        return id

    @staticmethod
    async def delete(id):
        await redis_client.delete(f'room:{id}')
        await redis_client.delete(f'class:{id}:participants')
        logger.debug(f"Room deleted: id={id}")

    @staticmethod
    async def get(id):
        data = await redis_client.hgetall(f'room:{id}')
        if not data:
            logger.debug(f"Room not found: id={id}")
            return None
        return {
            'id': id,
            'name': data.get('name'),
            'created_by': data.get('created_by'),
            'opts': json.loads(data.get('opts', '{}'))
        }

    @staticmethod
    async def size(id):
        size = await redis_client.scard(f'class:{id}:participants')
        logger.debug(f"Room size: id={id}, size={size}")
        return size

    @staticmethod
    async def add_user(id, user_id):
        await redis_client.sadd(f'class:{id}:participants', user_id)
        logger.debug(f"User added to room: room_id={id}, user_id={user_id}")

    @staticmethod
    async def remove_user(id, user_id):
        await redis_client.srem(f'class:{id}:participants', user_id)
        logger.debug(f"User removed from room: room_id={id}, user_id={user_id}")

    @staticmethod
    async def get_users(id):
        users = await redis_client.smembers(f'class:{id}:participants')
        logger.debug(f"Room users: room_id={id}, users={users}")
        return users

async def kick_out(user_id, room_id):
    logger.debug(f"Kick out: user_id={user_id}, room_id={room_id}")
    await sio.emit('action:terminate_peer_connection', {'userId': user_id}, room=room_id)
    await sio.emit('action:room_connection_terminated', {'roomId': room_id}, room=user_id)
    await Rooms.remove_user(room_id, user_id)

@sio.event
async def connect(sid, environ, auth=None):
    logger.debug(f"Connect: sid={sid}, auth={auth}, query={environ.get('QUERY_STRING', '')}")
    
    query = parse_qs(environ.get('QUERY_STRING', ''))
    session_id = query.get('sessionId', [None])[0] if query else None
    if session_id and not auth:
        logger.debug(f"Using sessionId from query: {session_id}")
        auth = {'sessionId': session_id}

    if not auth or not isinstance(auth, dict) or 'sessionId' not in auth:
        logger.debug(f"Connect skipped: Waiting for auth event, auth={auth}")
        return True

    session_id = auth.get('sessionId')
    if not session_id:
        logger.error(f"Connect failed: No sessionId in auth={auth}")
        raise socketio.exceptions.ConnectionRefusedError('sessionId required')

    logger.debug(f"Processing connect with sessionId={session_id}")
    await sio.save_session(sid, {'sessionId': session_id, 'user': None})
    sio.enter_room(sid, session_id)
    await redis_client.sadd('connected_sessions', session_id)
    
    current_room_id = auth.get('currentRoomId')
    if current_room_id:
        if await redis_client.sismember(f'class:{current_room_id}:participants', session_id):
            logger.debug(f"Joining room: sid={sid}, room={current_room_id}")
            sio.enter_room(sid, current_room_id)
        else:
            logger.debug(f"Room not found or user not in room: room={current_room_id}, session_id={session_id}")
            await sio.emit('action:room_connection_terminated', {'roomId': current_room_id}, to=sid)
    
    logger.info(f"Socket connected: sid={sid}, sessionId={session_id}")
    return True

@sio.event
async def disconnect(sid):
    logger.debug(f"Disconnect: sid={sid}")
    session = await sio.get_session(sid)
    if not session:
        logger.debug(f"No session found for sid={sid}")
        return
    user_id = session['sessionId']
    await redis_client.srem('connected_sessions', user_id)
    for room in list(sio.rooms(sid)):
        if room != sid and room != user_id:
            await kick_out(user_id, room)
            if await Rooms.size(room) == 0:
                logger.debug(f"Deleting empty room: {room}")
                await Rooms.delete(room)
    logger.info(f"Socket disconnected: sid={sid}, sessionId={user_id}")

@sio.on('request:create_room')
async def create_room(sid, data):
    logger.debug(f"Create room: sid={sid}, data={data}")
    session = await sio.get_session(sid)
    if not session or 'sessionId' not in session:
        logger.error(f"Create room failed: Not authenticated, sid={sid}")
        return {'name': 'Error', 'message': 'Not authenticated'}
    user_id = session['sessionId']
    room = data['room']
    try:
        class_id = room.get('id') or generate()
        id = await Rooms.create(room, user_id, class_id=class_id)
        room_data = await Rooms.get(id)
        if not room_data:
            logger.error(f"Create room failed: Creation failed, id={id}")
            return {'name': 'Error', 'message': 'Creation failed'}
        sio.enter_room(sid, id)
        await sio.emit('action:room_connection_established', {'room': room_data}, to=user_id)
        logger.info(f"Room created: id={id}, user_id={user_id}")
        return None
    except Exception as e:
        logger.error(f"Create room error: {e}")
        return {'name': 'Error', 'message': str(e)}

@sio.on('request:join_room')
async def join_room(sid, data):
    logger.debug(f"Join room: sid={sid}, data={data}")
    session = await sio.get_session(sid)
    if not session or 'sessionId' not in session:
        logger.error(f"Join room failed: Not authenticated, sid={sid}")
        return {'name': 'Error', 'message': 'Not authenticated'}
    user_id = session['sessionId']
    user_name = data['userName']
    room_id = data['roomId']
    try:
        room = await Rooms.get(room_id)
        if not room:
            room = {
                'id': room_id,
                'name': f"Room {room_id}",
                'created_by': user_name,
                'opts': {}
            }
            await Rooms.create(room, user_id, class_id=room_id)
            room = await Rooms.get(room_id)
        opts = room['opts']
        capacity = opts.get('capacity', 0)
        if capacity > 0 and await Rooms.size(room_id) >= capacity:
            logger.error(f"Join room failed: Room full, room_id={room_id}")
            return {'name': 'Error', 'message': 'Room is full'}
        
        # Handle participants as a regular generator
        participants = list(sio.manager.get_participants('/', room_id))
        logger.debug(f"Participants in room {room_id}: {participants}")
        users = await Rooms.get_users(room_id)
        logger.debug(f"Users in room {room_id}: {users}")
        missing = []
        for p in participants:
            p_sid = p[0] if isinstance(p, tuple) else p
            try:
                p_session = await sio.get_session(p_sid)
                if not p_session or not p_session.get('sessionId'):
                    logger.debug(f"Skipping invalid session for sid={p_sid} in room {room_id}")
                    continue
                if p_session['sessionId'] not in users:
                    missing.append(p_session['sessionId'])
            except Exception as e:
                logger.debug(f"Session not found for sid={p_sid} in room {room_id}: {e}")
                continue
        for m in missing:
            logger.debug(f"Kicking out missing user: {m} from room {room_id}")
            await kick_out(m, room_id)
        
        logger.debug(f"Emitting action:establish_peer_connection to room {room_id} for user_id={user_id}, userName={user_name}, skip_sid={sid}")
        await sio.emit('action:establish_peer_connection', {'userId': user_id, 'userName': user_name}, room=room_id, skip_sid=sid)
        sio.enter_room(sid, room_id)
        await sio.emit('action:room_connection_established', {'room': room}, to=sid)
        await Rooms.add_user(room_id, user_id)
        logger.info(f"User joined room: sid={sid}, user_id={user_id}, room_id={room_id}")
        return None
    except Exception as e:
        logger.error(f"Join room error: {e}")
        return {'name': 'Error', 'message': 'Something went wrong'}

@sio.on('request:leave_room')
async def leave_room(sid, data):
    logger.debug(f"Leave room: sid={sid}, data={data}")
    session = await sio.get_session(sid)
    if not session or 'sessionId' not in session:
        logger.error(f"Leave room failed: Not authenticated, sid={sid}")
        return {'name': 'Error', 'message': 'Not authenticated'}
    user_id = session['sessionId']
    room_id = data['roomId']
    try:
        sio.leave_room(sid, room_id)
        await kick_out(user_id, room_id)
        if await Rooms.size(room_id) == 0:
            logger.debug(f"Deleting empty room: {room_id}")
            await Rooms.delete(room_id)
        logger.info(f"User left room: sid={sid}, user_id={user_id}, room_id={room_id}")
        return None
    except Exception as e:
        logger.error(f"Leave room error: {e}")
        return {'name': 'Error', 'message': 'Something went wrong'}

@sio.on('request:send_message')
async def send_message(sid, data):
    logger.debug(f"Send message: sid={sid}, data={data}")
    session = await sio.get_session(sid)
    if not session or 'sessionId' not in session:
        logger.error(f"Send message failed: Not authenticated, sid={sid}")
        return {'name': 'Error', 'message': 'Not authenticated'}
    user_id = session['sessionId']
    room_id = data['roomId']
    msg_data = data['data']
    try:
        users = await Rooms.get_users(room_id)
        logger.debug(f"Broadcasting message to users in room {room_id}: {users}")
        for to in users:
            if to != user_id:
                if not await redis_client.sismember('connected_sessions', to):
                    logger.debug(f"Recipient {to} not connected, kicked from room {room_id}")
                    await kick_out(to, room_id)
                    continue
                logger.debug(f"Emitting message_received to {to} from {user_id}")
                await sio.emit('action:message_received', {'from': user_id, 'data': msg_data}, to=to)
        logger.info(f"Message broadcast: from={user_id}, room_id={room_id}")
        return None
    except Exception as e:
        logger.error(f"Send message error: {e}")
        return {'name': 'Error', 'message': 'Something went wrong'}

app = sio