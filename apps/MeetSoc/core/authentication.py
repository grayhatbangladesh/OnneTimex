"""
JWT authentication with Redis-backed token revocation check.
"""
from django.conf import settings
from django.core.cache import cache
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken


class RedisAwareJWTAuthentication(JWTAuthentication):
    """
    Validates JWT then checks Redis blacklist by jti (logout / revoke).
    """

    def get_validated_token(self, raw_token):
        validated = super().get_validated_token(raw_token)
        jti = validated.get("jti")
        if jti and cache.get(f"jwt_blacklist:{jti}"):
            raise InvalidToken("Token has been revoked.")
        return validated

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        from apps.suspensions.models import AccountSuspension

        active = AccountSuspension.get_active_for_user(user)
        if active:
            raise AuthenticationFailed("Account is suspended.")
        return user
