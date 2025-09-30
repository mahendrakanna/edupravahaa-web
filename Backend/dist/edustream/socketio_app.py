import logging
import socketio
from urllib.parse import parse_qs
import redis.asyncio as aioredis
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.sessions.models import Session
from edu_platform.models import User, ClassSession, ClassSchedule, CourseEnrollment
from asgiref.sync import sync_to_async
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Initialize Socket.IO server with Redis manager
mgr = socketio.AsyncRedisManager("redis://13.200.52.218:6379/0")
sio = socketio.AsyncServer(
    async_mode="asgi",
    client_manager=mgr,
    cors_allowed_origins="*",
    logger=True,
    engineio_logger=True
)

# Redis client for participant tracking
redis_client = aioredis.Redis(
    host="13.200.52.218",
    port=6379,
    db=0,
    decode_responses=True
)

@sync_to_async
def validate_class_session_pk(pk):
    """Validate ClassSession exists for given primary key (id)."""
    try:
        pk = int(pk)  # Ensure pk is an integer
        ClassSession.objects.get(id=pk)
        return True
    except (ValueError, ObjectDoesNotExist):
        logger.error(f"ClassSession not found for id={pk}")
        return False
    except Exception as e:
        logger.error(f"Error validating id {pk}: {e}")
        return False

@sync_to_async
def authenticate_user(token, user_role):
    """Authenticate user using JWT token and validate user_role."""
    try:
        # Validate JWT token using SimpleJWT
        access_token = AccessToken(token)
        user = User.objects.get(id=access_token['user_id'])
        if not user.is_active:
            logger.error(f"User {user.email} is inactive")
            return None
        # Validate user_role matches user's role
        if user_role not in ['student', 'teacher'] or user.role != user_role:
            logger.error(f"Invalid user_role {user_role} for user {user.email} with role {user.role}")
            return None
        return user
    except (InvalidToken, TokenError):
        logger.error(f"Invalid JWT token: {token}")
        return None
    except ObjectDoesNotExist:
        logger.error(f"User not found for JWT token: {token}")
        return None
    except Exception as e:
        logger.error(f"Error authenticating JWT token {token}: {e}")
        return None

@sync_to_async
def is_user_authorized_for_session(user, room_id):
    """Check if user (student or teacher) is authorized for the ClassSession."""
    try:
        room_id = int(room_id)  # Ensure room_id is an integer
        class_session = ClassSession.objects.get(id=room_id)
        schedule = class_session.schedule

        if user.is_student:
            # Check if student is enrolled in the batch of the session
            enrollment_exists = CourseEnrollment.objects.filter(
                student=user,
                course=schedule.course,
                batch=schedule.batch,
                start_date__lte=class_session.session_date,
                end_date__gte=class_session.session_date
            ).exists()
            if not enrollment_exists:
                logger.error(f"Student {user.email} not enrolled in batch {schedule.batch} for course {schedule.course.name}")
                return False
            return True

        if user.is_teacher:
            # Check if teacher is assigned to the batch of the session
            schedule_exists = ClassSchedule.objects.filter(
                teacher=user,
                course=schedule.course,
                batch=schedule.batch,
                batch_start_date__lte=class_session.session_date,
                batch_end_date__gte=class_session.session_date
            ).exists()
            if not schedule_exists:
                logger.error(f"Teacher {user.email} not assigned to batch {schedule.batch} for course {schedule.course.name}")
                return False
            return True

        logger.error(f"User {user.email} has invalid role: {user.role}")
        return False
    except (ValueError, ObjectDoesNotExist):
        logger.error(f"Invalid ClassSession id {room_id} for user {user.email}")
        return False
    except Exception as e:
        logger.error(f"Error checking authorization for user {user.email}, room_id {room_id}: {e}")
        return False

@sio.event
async def connect(sid, environ, auth=None):
    """Handle client connection, authenticate user, and store sessionId."""
    query = parse_qs(environ.get('QUERY_STRING', ''))
    session_id = query.get('sessionId', [None])[0] if query else None
    token = None
    user_role = None
    user_name = None
    if auth and isinstance(auth, dict):
        session_id = auth.get('sessionId', session_id)
        token = auth.get('token')
        user_role = auth.get('userRole')
        user_name = auth.get('userName', 'Anonymous')

    # Validate token, user_role, and session_id
    if not token:
        logger.error(f"Connect failed: No token provided, sid={sid}")
        raise socketio.exceptions.ConnectionRefusedError({"message": "Token required"})
    if not user_role:
        logger.error(f"Connect failed: No userRole provided, sid={sid}")
        raise socketio.exceptions.ConnectionRefusedError({"message": "userRole required"})
    if not session_id:
        logger.error(f"Connect failed: No sessionId provided, sid={sid}")
        raise socketio.exceptions.ConnectionRefusedError({"message": "sessionId required"})

    # Authenticate user
    user = await authenticate_user(token, user_role)
    if not user:
        logger.error(f"Connect failed: Invalid or inactive user for token or userRole {user_role}, sid={sid}")
        raise socketio.exceptions.ConnectionRefusedError({"message": "Invalid or inactive user"})

    # Store sessionId and user info
    await sio.save_session(sid, {
        "sessionId": session_id,
        "userRole": user_role,
        "userName": user_name,
        "user": user.id  # Store user ID for later reference
    })
    
    logger.info(f"Connected: sid={sid}, session_id={session_id}, user={user.email}, userRole={user_role}, userName={user_name}")
    return None


@sio.event
async def disconnect(sid):
    """Handle client disconnection, update participant count if in a room."""
    session = await sio.get_session(sid)
    session_id = session.get("sessionId")
    room_id = session.get("roomId")  # Check if client joined a room
    if not session_id:
        logger.debug(f"Disconnect: sid={sid}, no sessionId")
        return
 
    if room_id:
        sio.leave_room(sid, room_id)
        await redis_client.srem(f"class:{room_id}:participants", sid)
        await redis_client.srem(f"class:{room_id}:raised_hands", sid)
       
        # Broadcast updated participant count
        count = await redis_client.scard(f"class:{room_id}:participants")
        await sio.emit("action:participant_count", {"count": count}, room=room_id)
       
        # Notify others of terminated connection
        await sio.emit(
            "action:terminate_peer_connection",
            {"userId": sid},
            room=room_id
        )
       
        # Update raised hands
        await update_raised_hands(room_id)
       
        logger.info(f"Disconnected: sid={sid}, room_id={room_id}, participants={count}")
    else:
        logger.info(f"Disconnected: sid={sid}, session_id={session_id}, no room joined")


async def update_raised_hands(room_id):
    raised_key = f"class:{room_id}:raised_hands"
    raised_sids = await redis_client.smembers(raised_key)
    raised_list = []
    for rsid in raised_sids:
        session = await sio.get_session(rsid)
        if session:
            raised_list.append({"userId": rsid, "userName": session.get("userName", "Anonymous")})
    await sio.emit("action:raised_hands_update", {"raisedHands": raised_list}, room=room_id)

@sio.on("request:join_room")
async def join_room(sid, data):
    """Handle join_room request, validate roomId and user authorization."""
    session = await sio.get_session(sid)
    room_id = data.get("roomId")
    user_name = data.get("userName", session.get("userName", "Anonymous"))
    user_role = data.get("userRole", session.get("userRole", "student"))
    logger.debug(f"Join room: sid={sid}, roomId={room_id}, userName={user_name}, userRole={user_role}")

    # Validate roomId as ClassSession primary key
    if not room_id or not await validate_class_session_pk(room_id):
        logger.error(f"Join failed: Invalid ClassSession id {room_id}, sid={sid}")
        return {"name": "Error", "message": "Invalid ClassSession id"}

    # Check user authorization
    user = await sync_to_async(User.objects.get)(id=session.get("user"))
    if not await is_user_authorized_for_session(user, room_id):
        logger.error(f"Join failed: User {user.email} not authorized for ClassSession id {room_id}, sid={sid}")
        return {"name": "Error", "message": "Not authorized for this session"}

    # Update session with roomId
    await sio.save_session(sid, {
        "sessionId": session.get("sessionId"),
        "roomId": room_id,
        "userName": user_name,
        "userRole": user_role,
        "user": user.id
    })

    # Join the room and track participant
    sio.enter_room(sid, room_id)
    await redis_client.sadd(f"class:{room_id}:participants", sid)

    # Confirm room join
    room_data = {
        "id": room_id,
        "name": f"Class {room_id}",
        "created_by": user_name,
        "opts": {}
    }
    await sio.emit("action:room_connection_established", {"room": room_data}, to=sid)
    
    # Broadcast peer connection request
    await sio.emit(
        "action:establish_peer_connection",
        {"userId": sid, "userName": user_name},
        room=room_id,
        skip_sid=sid
    )
    
    # Update participant count
    count = await redis_client.scard(f"class:{room_id}:participants")
    await sio.emit("action:participant_count", {"count": count}, room=room_id)
    
    # Update raised hands for new joiner
    await update_raised_hands(room_id)
    
    logger.info(f"Joined room: sid={sid}, room_id={room_id}, userName={user_name}, participants={count}")
    return None

@sio.on("request:leave_room")
async def leave_room(sid, data):
    """Handle leave_room request."""
    session = await sio.get_session(sid)
    room_id = data.get("roomId")
    logger.debug(f"Leave room: sid={sid}, roomId={room_id}")

    # Validate roomId
    if not room_id or not await validate_class_session_pk(room_id):
        logger.error(f"Leave failed: Invalid ClassSession id {room_id}, sid={sid}")
        return {"name": "Error", "message": "Invalid ClassSession id"}

    sio.leave_room(sid, room_id)
    await redis_client.srem(f"class:{room_id}:participants", sid)
    await redis_client.srem(f"class:{room_id}:raised_hands", sid)
    
    # Broadcast updated participant count
    count = await redis_client.scard(f"class:{room_id}:participants")
    await sio.emit("action:participant_count", {"count": count}, room=room_id)
    
    # Notify others of terminated connection
    await sio.emit(
        "action:terminate_peer_connection",
        {"userId": sid},
        room=room_id
    )
    await sio.emit("action:room_connection_terminated", {"roomId": room_id}, to=sid)
    
    # Update raised hands
    await update_raised_hands(room_id)
    
    # Clear roomId from session
    await sio.save_session(sid, {
        "sessionId": session.get("sessionId"),
        "userName": session.get("userName", "Anonymous"),
        "userRole": session.get("userRole", "student"),
        "user": session.get("user")
    })
    logger.info(f"Left room: sid={sid}, room_id={room_id}, participants={count}")
    return None

@sio.on("request:send_message")
async def send_message(sid, data):
    """Handle send_message for chat or WebRTC signaling."""
    session = await sio.get_session(sid)
    room_id = data.get("roomId", session.get("roomId"))  # Fallback to session's roomId
    msg_data = data.get("data", {})
    to_user = data.get("to")
    logger.debug(f"Send message: sid={sid}, roomId={room_id}, to={to_user}, data={msg_data}")

    if not room_id:
        logger.error(f"Send message failed: No roomId provided, sid={sid}")
        return {"name": "Error", "message": "No roomId provided"}

    # Validate roomId
    if not await validate_class_session_pk(room_id):
        logger.error(f"Send message failed: Invalid ClassSession id {room_id}, sid={sid}")
        return {"name": "Error", "message": "Invalid ClassSession id"}

    if to_user:
        # Direct message (e.g., WebRTC signaling)
        await sio.emit(
            "action:message_received",
            {"from": sid, "data": msg_data},
            to=to_user
        )
        logger.info(f"Direct message sent: from={sid}, to={to_user}, room_id={room_id}")
    else:
        # Broadcast chat message
        chat_data = msg_data.get("chat", {})
        if chat_data:
            await sio.emit(
                "action:message_received",
                {
                    "from": session.get("userName", "Anonymous"),
                    "data": {"chat": {"text": chat_data.get("text"), "userName": session.get("userName", "Anonymous")}}
                },
                room=room_id
            )
            logger.info(f"Chat message broadcast: from={sid}, room_id={room_id}")
    return None

@sio.on("request:send_mesage")  # Handle frontend typo
async def send_message_typo(sid, data):
    """Handle send_mesage due to frontend typo."""
    logger.warning(f"Received request:send_mesage (typo) from sid={sid}, redirecting to send_message")
    return await send_message(sid, data)

@sio.on("request:raise_hand")
async def raise_hand(sid, data):
    session = await sio.get_session(sid)
    room_id = data.get("roomId", session.get("roomId"))
    raised = data.get("raised", False)
    
    logger.debug(f"Raise hand request: sid={sid}, userName={session.get('userName', 'Anonymous')}, sessionId={session.get('sessionId')}, room_id={room_id}, raised={raised}")

    if session.get("userRole") != 'student':
        logger.error(f"Raise hand failed: Only students can raise hands, sid={sid}")
        return {"name": "Error", "message": "Only students can raise hands"}
    
    if not room_id or not await validate_class_session_pk(room_id):
        logger.error(f"Raise hand failed: Invalid room_id {room_id}, sid={sid}")
        return {"name": "Error", "message": "Invalid room id"}
    
    raised_key = f"class:{room_id}:raised_hands"
    current_raised = await redis_client.smembers(raised_key)
    logger.debug(f"Before raise update: raised_sids={current_raised}")
    
    if raised:
        await redis_client.sadd(raised_key, sid)
    else:
        await redis_client.srem(raised_key, sid)
    
    current_raised_after = await redis_client.smembers(raised_key)
    logger.debug(f"After raise update: raised_sids={current_raised_after}")
    
    await update_raised_hands(room_id)
    logger.info(f"Hand raised updated: sid={sid}, raised={raised}, room_id={room_id}")
    return None

@sio.on("request:unmute_user")
async def unmute_user(sid, data):
    session = await sio.get_session(sid)
    room_id = data.get("roomId")
    target_user_id = data.get("userId")
    
    logger.debug(f"Unmute request: sid={sid}, session={session}, room_id={room_id}, target_user_id={target_user_id}")
    
    if session.get("userRole") != "teacher":
        logger.error(f"Unmute failed: Only teachers can unmute, sid={sid}, userRole={session.get('userRole')}")
        return {"name": "Error", "message": "Only teachers can unmute"}
    
    if not room_id or not await validate_class_session_pk(room_id):
        logger.error(f"Unmute failed: Invalid room_id {room_id}, sid={sid}")
        return {"name": "Error", "message": "Invalid room id"}
    
    participants_key = f"class:{room_id}:participants"
    participants = await redis_client.smembers(participants_key)
    if target_user_id not in participants:
        logger.error(f"Unmute failed: Target user {target_user_id} not in room {room_id}, sid={sid}")
        return {"name": "Error", "message": "User not in room"}
    
    logger.debug(f"Emitting action:unmute to target_user_id={target_user_id} in room_id={room_id}")
    await sio.emit("action:unmute", {}, to=target_user_id)
    
    raised_key = f"class:{room_id}:raised_hands"
    if await redis_client.sismember(raised_key, target_user_id):
        logger.debug(f"Removing target_user_id={target_user_id} from raised_hands")
        await redis_client.srem(raised_key, target_user_id)
        await update_raised_hands(room_id)
    
    logger.info(f"Unmuted user: target_user_id={target_user_id}, room_id={room_id}, by sid={sid}")
    return None

@sio.on("request:mute_user")
async def mute_user(sid, data):
    session = await sio.get_session(sid)
    room_id = data.get("roomId", session.get("roomId"))
    target_user_id = data.get("userId")
    
    if session.get("userRole") != 'teacher':
        logger.error(f"Mute failed: Only teachers can mute, sid={sid}")
        return {"name": "Error", "message": "Only teachers can mute"}
    
    if not room_id or not await validate_class_session_pk(room_id):
        logger.error(f"Mute failed: Invalid room_id {room_id}, sid={sid}")
        return {"name": "Error", "message": "Invalid room id"}
    
    if not target_user_id:
        logger.error(f"Mute failed: No target user_id, sid={sid}")
        return {"name": "Error", "message": "No target user id"}
    
    await sio.emit("action:mute", to=target_user_id)
    
    logger.info(f"Muted user: target={target_user_id}, by={sid}, room_id={room_id}")
    return None

app = sio