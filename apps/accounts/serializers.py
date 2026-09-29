"""
Account-level serializers: auth, profile, public user cards, friend/follow.
All aligned with apps.accounts.models (User + UserProfile).
"""
import random
import re
import string

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.db.models import Q
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.accounts.models import User, UserProfile

UserModel = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _full_name(user):
    return " ".join(x for x in [user.first_name, user.last_name] if x).strip() or (user.username or "")


def _media_url(media_id):
    if not media_id:
        return ""
    try:
        from apps.Media.models import Media

        m = Media.objects.filter(id=media_id).first()
        return (getattr(m, "url", "") or "") if m else ""
    except Exception:
        return ""


def _avatar_url(user):
    profile = getattr(user, "profile", None)
    media_id = getattr(profile, "avatar_media_id", None) if profile else None
    if not media_id:
        return "https://cdn.pixabay.com/photo/2015/10/05/22/37/blank-profile-picture-973460_960_720.png"
    try:
        from apps.Media.models import Media
        m = Media.objects.filter(id=media_id).first()
        url = (getattr(m, "url", "") or "") if m else ""
        return url if url else "https://cdn.pixabay.com/photo/2015/10/05/22/37/blank-profile-picture-973460_960_720.png"
    except Exception:
        return "https://cdn.pixabay.com/photo/2015/10/05/22/37/blank-profile-picture-973460_960_720.png"


def _cover_url(user):
    profile = getattr(user, "profile", None)
    media_id = getattr(profile, "cover_media_id", None) if profile else None
    if not media_id:
        return ""
    try:
        from apps.Media.models import Media
        m = Media.objects.filter(id=media_id).first()
        url = (getattr(m, "url", "") or "") if m else ""
        return url if url else ""
    except Exception:
        return ""


def _otp_key(identifier: str) -> str:
    return f"otp:{identifier}"


def generate_otp(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))


def store_otp(identifier: str, ttl: int = 600) -> str:
    code = generate_otp()
    cache.set(_otp_key(identifier), code, timeout=ttl)
    return code


# ---------------------------------------------------------------------------
# Public user cards
# ---------------------------------------------------------------------------
class UserPublicLiteSerializer(serializers.Serializer):
    """Lightweight public user card (used inside posts, comments, messages...)."""

    def to_representation(self, instance):
        return {
            "id": str(instance.id),
            "username": instance.username or "",
            "fullName": _full_name(instance),
            "avatar": _avatar_url(instance),
        }


class UserPublicSerializer(serializers.Serializer):
    """Full public profile card."""

    def to_representation(self, instance):
        has_badge = False
        badge_until = None
        try:
            from apps.MeetSoc.models import BlueVerificationRequest

            active = BlueVerificationRequest.get_active_for_user(instance)
            has_badge = bool(active)
            badge_until = active.valid_until if active else None
        except Exception:
            pass
        p = getattr(instance, "profile", None)
        friendship_status = None
        is_following = False
        request = self.context.get("request")
        try:
            if request and getattr(request, "user", None) and request.user.is_authenticated and request.user.id != instance.id:
                from apps.MeetSoc.models import Friendship, Follow

                fr = Friendship.objects.filter(
                    Q(sender=request.user, receiver=instance) | Q(sender=instance, receiver=request.user)
                ).first()
                if fr:
                    if fr.status == "accepted":
                        friendship_status = "friends"
                    elif fr.sender_id == request.user.id:
                        friendship_status = "request_sent"
                    else:
                        friendship_status = "request_received"
                is_following = Follow.objects.filter(follower=request.user, following=instance).exists()
        except Exception:
            pass
        return {
            "id": str(instance.id),
            "username": instance.username or "",
            "fullName": _full_name(instance),
            "avatar": _avatar_url(instance),
            "cover": _cover_url(instance),
            "hasBlueBadge": has_badge,
            "blueBadgeValidUntil": badge_until.isoformat() if badge_until else None,
            "friendshipStatus": friendship_status,
            "isFollowing": is_following,
            "profile": {
                "bio": getattr(p, "bio", ""),
                "website": getattr(p, "website", ""),
                "country": getattr(p, "country", ""),
                "city": getattr(p, "city", ""),
                "hometown": getattr(p, "hometown", ""),
                "work": getattr(p, "work", ""),
                "education": getattr(p, "education", ""),
                "hobbies": getattr(p, "hobbies", ""),
                "relationship": getattr(p, "relationship", "unspecified"),
                "socialLinks": getattr(p, "social_links", {}),
                "posts_count": getattr(p, "posts_count", 0),
                "friends_count": getattr(p, "friends_count", 0),
                "followers_count": getattr(p, "followers_count", 0),
                "following_count": getattr(p, "following_count", 0),
            } if p else {},
        }


# ---------------------------------------------------------------------------
# Me / profile update
# ---------------------------------------------------------------------------
class MeSerializer(serializers.ModelSerializer):
    fullName = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    cover = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    profile = serializers.SerializerMethodField()
    is_verified = serializers.SerializerMethodField()
    is_online = serializers.SerializerMethodField()
    has_blue_badge = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id", "phone", "email", "username", "first_name", "last_name",
            "date_of_birth", "gender", "status", "createdAt", "fullName",
            "avatar", "cover", "profile", "is_verified", "is_online", "has_blue_badge",
        )
        read_only_fields = ("id", "phone", "status")

    def get_fullName(self, obj):
        return _full_name(obj)

    def get_avatar(self, obj):
        return _avatar_url(obj)

    def get_cover(self, obj):
        return _cover_url(obj)

    def get_profile(self, obj):
        p = getattr(obj, "profile", None)
        if not p:
            return {}
        return {
            "bio": p.bio,
            "website": p.website,
            "country": p.country,
            "city": p.city,
            "hometown": p.hometown,
            "work": p.work,
            "education": p.education,
            "hobbies": p.hobbies,
            "relationship": p.relationship,
            "publiccontacts": p.public_contacts,
            "socialLinks": p.social_links,
            "otherInfo": p.other_info,
            # Denormalized counters — the app renders these on the profile.
            "posts_count": p.posts_count,
            "friends_count": p.friends_count,
            "followers_count": p.followers_count,
            "following_count": p.following_count,
            "is_private": p.is_private,
        }

    def get_is_verified(self, obj):
        return obj.is_verified

    def get_is_online(self, obj):
        return False

    def get_has_blue_badge(self, obj):
        return obj.is_verified


class MeUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "username", "email", "date_of_birth", "gender")

    def validate_username(self, value):
        if value:
            value = value.lower()
            qs = User.objects.filter(username=value).exclude(pk=self.instance.pk) if self.instance else User.objects.filter(username=value)
            if qs.exists():
                raise serializers.ValidationError("Username already taken.")
        return value


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = (
            "bio", "website", "country", "city", "hometown", "hobbies", "work",
            "education", "relationship", "public_contacts", "social_links", "other_info",
            "is_private",
        )

    def validate_bio(self, value):
        from apps.MeetSoc.core.utils import sanitize_html

        return sanitize_html(value) if value else value


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
_GENDER_ALIASES = {
    "male": "male",
    "m": "male",
    "female": "female",
    "f": "female",
    "other": "other",
    "prefer_not": "prefer_not",
    "prefer not to say": "prefer_not",
    "prefer-not-to-say": "prefer_not",
    "prefer_not_to_say": "prefer_not",
    "not specified": "prefer_not",
    "unspecified": "prefer_not",
}

# Django's E.164 rule: + then 8-15 digits, first digit 1-9.
_PHONE_RE = re.compile(r"^\+[1-9]\d{7,14}$")


def _normalize_phone(raw):
    """Accept the formats users actually type and return E.164 (or "").

    Handles "+88017...", "88017...", "0088017...", separators
    (space/dash/parentheses/dot) and the local Bangladeshi "01712345678".
    """
    v = re.sub(r"[\s\-().]", "", str(raw or ""))
    if not v:
        return ""
    if v.startswith("00"):
        v = "+" + v[2:]
    if v.startswith("+"):
        return v
    if v.startswith("01") and len(v) == 11:
        # Local mobile: 01712345678 -> +8801712345678
        return "+880" + v[1:]
    if v.isdigit():
        return "+" + v
    return v


def _placeholder_phone():
    """`User.phone` is UNIQUE and NOT NULL — email-only signups get a number.

    Nobody can log in with it (login matches the real phone/email), it only
    satisfies the column constraint.
    """
    for _ in range(30):
        candidate = "+1" + "".join(random.choices(string.digits, k=9))
        if not User.objects.filter(phone=candidate).exists():
            return candidate
    return "+1" + "".join(random.choices(string.digits, k=9))


def _parse_birthday(value):
    """Return 'YYYY-MM-DD', '' (drop the value) or None (unparseable).

    Accepts ISO dates, ISO datetimes (Dart's DateTime.toIso8601String) and the
    common day-first/month-first slash formats, so signup never 400s on a date
    the client formatted differently.
    """
    from datetime import date as _date, datetime

    from django.utils.dateparse import parse_date, parse_datetime

    if isinstance(value, _date) and not isinstance(value, datetime):
        return value.isoformat()
    s = str(value).strip()
    if not s:
        return ""
    dt = parse_datetime(s)
    if dt is not None:
        return dt.date().isoformat()
    d = parse_date(s)
    if d is not None:
        return d.isoformat()
    for fmt in ("%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d", "%d.%m.%Y", "%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return None


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    # Declared without the model's E.164 validator: `validate_phone` accepts
    # the formats users actually type (and an email address, see below).
    phone = serializers.CharField(max_length=32)
    # The app may send the whole display name as `full_name` (or dump it all
    # into `first_name`); both are split into first/last in validate().
    full_name = serializers.CharField(required=False, allow_blank=True, write_only=True, max_length=200)
    first_name = serializers.CharField(required=False, allow_blank=True, max_length=100)
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=100)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    gender = serializers.CharField(required=False, allow_blank=True, max_length=20)

    class Meta:
        model = User
        fields = (
            "phone", "email", "username",
            "first_name", "last_name", "full_name",
            "date_of_birth", "gender",
            "password", "password_confirm",
        )

    def to_internal_value(self, data):
        # Tolerate empty date_of_birth / gender ("" would fail field parsing).
        if isinstance(data, dict):
            data = data.copy()
            if data.get("date_of_birth") in ("", None):
                data.pop("date_of_birth", None)
            elif isinstance(data.get("date_of_birth"), str):
                parsed = _parse_birthday(data["date_of_birth"])
                if parsed == "":
                    data.pop("date_of_birth", None)
                elif parsed is not None:
                    data["date_of_birth"] = parsed

            # The website signup field doubles as "email or phone". When an
            # email address lands in `phone`, keep it as the email and give the
            # account a generated number (the column is UNIQUE + NOT NULL).
            raw_phone = str(data.get("phone") or "").strip()
            if "@" in raw_phone:
                if not str(data.get("email") or "").strip():
                    if User.objects.filter(email__iexact=raw_phone).exists():
                        raise serializers.ValidationError(
                            {"email": "An account with this email already exists."}
                        )
                    data["email"] = raw_phone
                data["phone"] = _placeholder_phone()
        return super().to_internal_value(data)

    def validate_phone(self, value):
        if "@" in (value or ""):
            return value  # already replaced in to_internal_value
        phone = _normalize_phone(value)
        if not _PHONE_RE.match(phone):
            raise serializers.ValidationError(
                "Enter your phone number with country code, e.g. +8801712345678."
            )
        return phone

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate_gender(self, value):
        key = (value or "").strip().lower()
        if not key:
            return "prefer_not"
        if key in dict(User.Gender.choices):
            return key
        return _GENDER_ALIASES.get(key, "prefer_not")

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})

        first = (attrs.get("first_name") or "").strip()
        last = (attrs.get("last_name") or "").strip()
        full = (attrs.pop("full_name", None) or "").strip()
        if full and not first:
            parts = full.split(None, 1)
            first = parts[0]
            last = last or (parts[1] if len(parts) > 1 else "")
        elif first and not last and " " in first:
            # App posts "John Doe" entirely in first_name — split it.
            parts = first.split(None, 1)
            first = parts[0]
            last = parts[1]
        if not first:
            raise serializers.ValidationError({"first_name": "This field is required."})
        attrs["first_name"] = first
        attrs["last_name"] = last
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")
        validated_data.pop("full_name", None)
        return User.objects.create_user(password=password, **validated_data)


class LoginTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Login with phone OR email; the `phone` field doubles as login identifier."""

    default_error_messages = {"no_active_account": "Invalid credentials."}

    def validate(self, attrs):
        login_input = (attrs.get("phone", "") or attrs.get("email", "")).strip()
        if "@" in login_input:
            user = User.objects.filter(email__iexact=login_input).first()
        else:
            # Match whatever format the user types against the stored E.164.
            normalized = _normalize_phone(login_input)
            user = (
                User.objects.filter(Q(phone=login_input) | Q(phone=normalized)).first()
                if normalized
                else None
            )

        if user is None:
            raise AuthenticationFailed("No account found with this phone or email.")
        if user.status in ("suspended", "banned"):
            raise AuthenticationFailed("Your account is suspended.")
        if user.status == "pending_deletion":
            raise AuthenticationFailed("This account is pending deletion.")

        attrs["phone"] = user.phone
        data = super().validate(attrs)
        return data


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8)
    new_password_confirm = serializers.CharField()

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError({"new_password_confirm": "Passwords do not match."})
        validate_password(attrs["new_password"])
        return attrs


class VerifyEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=8)

    def validate(self, attrs):
        key = _otp_key(attrs["email"])
        expected = cache.get(key)
        if not expected or expected != attrs["code"]:
            raise serializers.ValidationError({"code": "Invalid or expired code."})
        return attrs


class VerifyPhoneSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=32)
    code = serializers.CharField(max_length=8)

    def validate(self, attrs):
        key = _otp_key(attrs["phone"])
        expected = cache.get(key)
        if not expected or expected != attrs["code"]:
            raise serializers.ValidationError({"code": "Invalid or expired code."})
        return attrs


class SocialTokenSerializer(serializers.Serializer):
    access_token = serializers.CharField(required=False, allow_blank=True)
    id_token = serializers.CharField(required=False, allow_blank=True)


class FriendshipSerializer(serializers.Serializer):
    def to_representation(self, instance):
        return {
            "id": str(instance.id),
            "sender": UserPublicLiteSerializer(instance.sender).data,
            "receiver": UserPublicLiteSerializer(instance.receiver).data,
            "status": instance.status,
            "createdAt": instance.created_at.isoformat(),
        }


class FollowSerializer(serializers.Serializer):
    def to_representation(self, instance):
        return {
            "id": str(instance.id),
            "follower": UserPublicLiteSerializer(instance.follower).data,
            "following": UserPublicLiteSerializer(instance.following).data,
            "createdAt": instance.created_at.isoformat(),
        }