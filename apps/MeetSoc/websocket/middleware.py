"""
JWT authentication for WebSocket connections (query param `token`).
"""
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware


@database_sync_to_async
def get_user_from_token(token_key):
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import AnonymousUser
    from django.core.cache import cache
    from rest_framework_simplejwt.exceptions import InvalidToken
    from rest_framework_simplejwt.tokens import AccessToken

    User = get_user_model()
    if not token_key:
        return AnonymousUser()
    try:
        token = AccessToken(token_key)
        jti = token.get("jti")
        if jti and cache.get(f"jwt_blacklist:{jti}"):
            return AnonymousUser()
        user_id = token.get("user_id")
        if not user_id:
            return AnonymousUser()
        return User.objects.get(pk=user_id)
    except (InvalidToken, User.DoesNotExist):
        return AnonymousUser()
    except Exception:
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode()
        qs = parse_qs(query_string)
        token = (qs.get("token") or [None])[0]
        scope["user"] = await get_user_from_token(token)
        return await super().__call__(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    return JWTAuthMiddleware(inner)
