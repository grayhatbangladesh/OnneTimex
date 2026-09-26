"""
Shared utilities: sanitization, Redis keys, rate limits.
"""
import nh3
import bleach
from django.conf import settings
from django.core.cache import cache


def sanitize_html(text: str) -> str:
    if not text:
        return ""
    return bleach.clean(
        text,
        tags=settings.BLEACH_ALLOWED_TAGS,
        attributes=settings.BLEACH_ALLOWED_ATTRIBUTES,
        strip=True,
    )


def rate_limit_key(user_id, action: str) -> str:
    return f"ratelimit:{user_id}:{action}"


def check_rate_limit(user_id, action: str, limit: int, window_seconds: int) -> bool:
    """
    Returns True if allowed, False if rate limited.
    Uses INCR with expiry on first hit.
    """
    key = rate_limit_key(user_id, action)
    try:
        current = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=window_seconds)
        current = 1
    return current <= limit


def check_ip_rate_limit(ip: str, action: str, limit: int, window_seconds: int) -> bool:
    key = f"ratelimit:ip:{ip}:{action}"
    try:
        current = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=window_seconds)
        current = 1
    return current <= limit


def redis_keys_reference():
    """Documentation map for Redis key patterns (see project spec)."""
    return {
        "online:{user_id}": "SET — user online (TTL 90s heartbeat)",
        "last_seen:{user_id}": "STRING — ISO timestamp",
        "feed:{user_id}:{page}": "STRING JSON — cached feed TTL 5min",
        "unread_msg:{user_id}": "HASH — conv_id: count",
        "unread_notif:{user_id}": "STRING — integer",
        "ratelimit:{user_id}:{action}": "STRING — count TTL 60s",
        "otp:{email_or_phone}": "STRING — OTP TTL 10min",
        "trending:posts": "ZSET — post_id by score",
        "trending:hashtags": "ZSET — hashtag",
        "seen_stories:{user_id}": "SET — story ids",
        "seen_posts:{user_id}": "SET — post ids TTL 7d",
        "jwt_blacklist:{jti}": "STRING — blacklisted token",
        "call_room:{call_id}": "HASH — participants, status",
    }
