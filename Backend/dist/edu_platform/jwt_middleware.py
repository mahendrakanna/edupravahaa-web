# dist/edu_platform/middleware.py

import jwt
import logging
from channels.auth import AuthMiddlewareStack
from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.conf import settings
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import UntypedToken
from django.db import close_old_connections

logger = logging.getLogger(__name__)
User = get_user_model()

@database_sync_to_async
def get_user_from_token(payload):
    """
    Get user from validated token payload.
    """
    try:
        user = User.objects.get(id=payload['user_id'])
        return user if user.is_active else AnonymousUser()
    except User.DoesNotExist:
        logger.warning(f"User not found from token: user_id={payload.get('user_id')}")
        return AnonymousUser()

class JwtAuthMiddleware(BaseMiddleware):
    """
    Custom middleware to authenticate JWT from query params (?token=Bearer <jwt>).
    """
    def __init__(self, inner):
        super().__init__(inner)
        logger.info("JWT Auth Middleware initialized")

    async def __call__(self, scope, receive, send):
        close_old_connections()

        if scope['type'] != 'websocket':
            logger.debug("Non-WebSocket scope, skipping JWT auth")
            return await super().__call__(scope, receive, send)

        logger.debug(f"Processing WebSocket scope: {scope.get('path')}")

        # Extract token from query string
        query_string = scope.get('query_string', b'').decode('utf-8')
        logger.debug(f"Query string: {query_string}")
        query_params = parse_qs(query_string)
        raw_token = query_params.get('token', [None])[0]
        logger.debug(f"Raw token from query: {raw_token[:20] if raw_token else None}...")

        if not raw_token or not raw_token.startswith('Bearer '):
            logger.warning("No valid Bearer token in query string")
            scope['user'] = AnonymousUser()
            return await super().__call__(scope, receive, send)

        token = raw_token[7:].strip()  # Remove 'Bearer ' and any extra spaces

        try:
            # Validate token using simplejwt
            untyped_token = UntypedToken(token)
            logger.debug("Token validation passed (simplejwt)")

            # Decode payload
            decoded_payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=['HS256'],
                audience=None,
                issuer=None
            )
            logger.debug(f"Token decoded successfully: user_id={decoded_payload.get('user_id')}")

            # Get user async
            user = await get_user_from_token(decoded_payload)
            scope['user'] = user
            logger.info(f"JWT Auth successful: user_id={decoded_payload.get('user_id')}, email={user.email if user.is_authenticated else 'Anonymous'}")

        except (InvalidToken, TokenError, jwt.InvalidTokenError, jwt.ExpiredSignatureError, jwt.DecodeError, jwt.InvalidAlgorithmError) as e:
            logger.error(f"JWT Error: {str(e)}, token={token[:20]}...")
            scope['user'] = AnonymousUser()
        except Exception as e:
            logger.error(f"Unexpected error in JWT middleware: {str(e)}")
            scope['user'] = AnonymousUser()

        # Proceed to inner middleware
        return await super().__call__(scope, receive, send)

# Stack function
def JwtAuthMiddlewareStack(inner):
    logger.info("Creating JwtAuthMiddlewareStack")
    return JwtAuthMiddleware(AuthMiddlewareStack(inner))