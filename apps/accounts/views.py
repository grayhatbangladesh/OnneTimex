"""Devaz Account auth views: register, login (JWT), refresh, me, OTP verify, password reset."""
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.accounts.serializers import (
    LoginTokenObtainPairSerializer,
    MeSerializer,
    MeUpdateSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    ProfileUpdateSerializer,
    RegisterSerializer,
    SocialTokenSerializer,
    UserPublicSerializer,
    VerifyEmailSerializer,
    VerifyPhoneSerializer,
    store_otp,
)

User = get_user_model()


def _ok(data, message=""):
    return Response({"success": True, "data": data, "message": message, "meta": {}})


def _err(code, message, status_code=400):
    return Response(
        {"success": False, "error": {"code": code, "message": message, "details": {}}},
        status=status_code,
    )


# Top-level (flat) profile keys the app sends on PATCH /account/me/, mapped to
# their canonical UserProfile field names.
_PROFILE_ALIASES = {
    "bio": "bio",
    "website": "website",
    "country": "country",
    "city": "city",
    "hometown": "hometown",
    "hobbies": "hobbies",
    "work": "work",
    "education": "education",
    "relationship": "relationship",
    "public_contacts": "public_contacts",
    "publiccontacts": "public_contacts",
    "publicContacts": "public_contacts",
    "social_links": "social_links",
    "socialLinks": "social_links",
    "other_info": "other_info",
    "otherinfo": "other_info",
    "otherInfo": "other_info",
    "is_private": "is_private",
    "full_name": "full_name",
    "fullName": "full_name",
}

_USER_FIELDS = ("first_name", "last_name", "username", "email", "date_of_birth", "gender")


def _save_profile_fields(profile, prof_data):
    """Save the profile fields.

    First try the whole payload; if any single value fails validation, fall back
    to saving field-by-field so one bad value never silently drops the rest.
    """
    from apps.accounts.models import UserProfile

    pser = ProfileUpdateSerializer(profile, data=prof_data, partial=True)
    if pser.is_valid():
        pser.save()
        return
    model_fields = {f.name for f in UserProfile._meta.fields}
    for key, value in prof_data.items():
        if key not in model_fields:
            continue
        sub = ProfileUpdateSerializer(profile, data={key: value}, partial=True)
        if sub.is_valid():
            sub.save()


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = ser.save()
        # Ensure profile exists even if signal didn't fire
        from apps.accounts.models import UserProfile
        UserProfile.objects.get_or_create(user=user)
        refresh = RefreshToken.for_user(user)
        return _ok(
            {
                "user": UserPublicSerializer(user, context={"request": request}).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            "Account created.",
        )


class LoginView(TokenObtainPairView):
    serializer_class = LoginTokenObtainPairSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            return Response(
                {"success": False, "error": {"code": "INVALID_CREDENTIALS", "message": "Invalid credentials.", "details": {}}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return Response(
            {
                "success": True,
                "data": {
                    "access": str(serializer.validated_data["access"]),
                    "refresh": str(serializer.validated_data["refresh"]),
                },
                "message": "Login successful.",
                "meta": {},
            },
            status=status.HTTP_200_OK,
        )


class RefreshView(TokenRefreshView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            return Response(
                {"success": False, "error": {"code": "INVALID_REFRESH", "message": "Invalid refresh token.", "details": {}}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        refresh = serializer.validated_data["refresh"]
        access = str(refresh.access_token)
        return Response(
            {
                "success": True,
                "data": {"access": access, "refresh": str(refresh)},
                "message": "Token refreshed.",
                "meta": {},
            },
            status=status.HTTP_200_OK,
        )


class MeView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MeSerializer

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return MeUpdateSerializer
        return MeSerializer

    def update(self, request, *args, **kwargs):
        data = request.data

        # Support BOTH the nested {"profile": {...}} payload and the flat payload
        # the app actually sends (bio, website, country, ... at the top level).
        nested = data.get("profile")
        if isinstance(nested, dict) and nested:
            prof_data = dict(nested)
        else:
            prof_data = {}
            for raw_key, canonical in _PROFILE_ALIASES.items():
                if raw_key in data:
                    prof_data[canonical] = data[raw_key]

        # Social handles arrive as top-level "<site>Username" keys but are stored
        # in the profile's social_links JSON (what the app reads back as socialLinks).
        social = dict(prof_data["social_links"]) if isinstance(prof_data.get("social_links"), dict) else {}
        for raw_key in data.keys():
            if raw_key.endswith("Username") and isinstance(data[raw_key], str) and data[raw_key].strip():
                social[raw_key] = data[raw_key].strip()
        if social:
            prof_data["social_links"] = social

        user_payload = {k: data[k] for k in _USER_FIELDS if k in data}

        # full_name (or "John Doe" in first_name) → first_name / last_name.
        full_name = prof_data.pop("full_name", None)
        if not isinstance(full_name, str) or not full_name.strip():
            full_name = data.get("full_name") or data.get("fullName") or ""
        if isinstance(full_name, str) and full_name.strip():
            parts = full_name.split(None, 1)
            if not str(user_payload.get("first_name") or "").strip():
                user_payload["first_name"] = parts[0]
            if len(parts) > 1 and not str(user_payload.get("last_name") or "").strip():
                user_payload["last_name"] = parts[1]

        profile = getattr(request.user, "profile", None)

        # Update user fields if any
        if user_payload:
            ser = self.get_serializer(request.user, data=user_payload, partial=True)
            ser.is_valid(raise_exception=True)
            ser.save()

        # Update profile fields if any
        if prof_data:
            if profile is None:
                from apps.accounts.models import UserProfile

                profile, _ = UserProfile.objects.get_or_create(user=request.user)
            _save_profile_fields(profile, prof_data)

        # Refresh user and profile from database to get latest data
        request.user.refresh_from_db()
        if profile is not None:
            profile.refresh_from_db()

        return _ok(MeSerializer(request.user).data, "Updated.")


def _store_profile_media(request, upload_keys):
    """Save an uploaded file (or reuse a media id) and return (media_id, url).

    The app sends `PATCH` multipart with the file; older clients send JSON
    `{"media_id": ...}`. Both are supported.
    """
    media_id = request.data.get("media_id")
    url = ""

    uploaded = None
    for key in upload_keys:
        if key in request.FILES:
            uploaded = request.FILES[key]
            break
    if uploaded is None:
        for key in upload_keys:
            if key in request.data and hasattr(request.data[key], "read"):
                uploaded = request.data[key]
                break

    if uploaded is not None:
        from apps.Media.models import Media

        m = Media(
            file=uploaded,
            original_name=getattr(uploaded, "name", "") or "",
            kind=Media.KIND_IMAGE,
            content_type=getattr(uploaded, "content_type", "") or "",
        )
        m.save()
        media_id = m.id
        url = m.url
    elif media_id:
        try:
            from apps.Media.models import Media

            existing = Media.objects.filter(id=media_id).first()
            url = existing.url if existing else ""
        except Exception:
            url = ""

    return media_id, url


class AvatarUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        return self._update(request)

    # The Flutter app uploads with PATCH multipart.
    patch = post

    def _update(self, request):
        profile = getattr(request.user, "profile", None)
        if not profile:
            return _err("NO_PROFILE", "Profile not found.")

        media_id, url = _store_profile_media(request, ("avatar", "image", "file"))
        if not media_id:
            return _err("NO_FILE", "No image received.")

        profile.avatar_media_id = media_id
        profile.save(update_fields=["avatar_media_id"])
        return _ok(
            {
                "id": str(media_id),
                "url": url,
                # Nested shape the app reads on upload.
                "profile": {"avatar": url, "avatar_media_id": str(media_id)},
            },
            "Avatar updated.",
        )


class CoverUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        return self._update(request)

    patch = post

    def _update(self, request):
        profile = getattr(request.user, "profile", None)
        if not profile:
            return _err("NO_PROFILE", "Profile not found.")

        media_id, url = _store_profile_media(
            request, ("cover_photo", "cover", "image", "file")
        )
        if not media_id:
            return _err("NO_FILE", "No image received.")

        profile.cover_media_id = media_id
        profile.save(update_fields=["cover_media_id"])
        return _ok(
            {
                "id": str(media_id),
                "url": url,
                "profile": {"cover_photo": url, "cover_media_id": str(media_id)},
            },
            "Cover updated.",
        )


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        ser = VerifyEmailSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = User.objects.filter(email__iexact=ser.validated_data["email"]).first()
        if user and user.email_verified_at is None:
            from django.utils import timezone

            user.email_verified_at = timezone.now()
            user.save(update_fields=["email_verified_at"])
        return _ok({}, "Email verified.")


class VerifyPhoneView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        ser = VerifyPhoneSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = User.objects.filter(phone=ser.validated_data["phone"]).first()
        if user and user.phone_verified_at is None:
            from django.utils import timezone

            user.phone_verified_at = timezone.now()
            user.save(update_fields=["phone_verified_at"])
        return _ok({}, "Phone verified.")


class SendOTPView(APIView):
    """Dev helper: generates and returns an OTP (no SMS provider configured yet)."""

    permission_classes = [AllowAny]

    def post(self, request):
        identifier = request.data.get("identifier", "")
        if not identifier:
            return _err("INVALID", "identifier required.")
        code = store_otp(identifier)
        return _ok({"dev_code": code}, "OTP generated (dev mode).")


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        ser = PasswordResetRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        email = ser.validated_data["email"]
        if User.objects.filter(email__iexact=email).exists():
            store_otp(email)
        return _ok({}, "If the email exists, a reset code was sent.")


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        ser = PasswordResetConfirmSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        return _ok({}, "Password reset flow endpoint.")


class SocialLoginView(APIView):
    """Google/Apple social token exchange."""

    permission_classes = [AllowAny]

    def post(self, request):
        ser = SocialTokenSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        id_token = ser.validated_data.get("id_token")
        if not id_token:
            return _err("INVALID", "id_token required.")
        try:
            from google.oauth2 import id_token as google_id_token
            from google.auth.transport import requests as google_requests

            info = google_id_token.verify_oauth2_token(id_token, google_requests.requests())
        except Exception:
            return _err("INVALID_TOKEN", "Could not verify social token.", 401)
        email = info.get("email")
        user = User.objects.filter(email__iexact=email).first() if email else None
        if not user:
            user = User.objects.create_user(
                phone=f"+1{abs(hash(email)) % 10**10:010d}",
                email=email,
                first_name=info.get("given_name", "User"),
                last_name=info.get("family_name", ""),
            )
        refresh = RefreshToken.for_user(user)
        return _ok({"access": str(refresh.access_token), "refresh": str(refresh)})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh = request.data.get("refresh")
        if refresh:
            try:
                RefreshToken(refresh).blacklist()
            except Exception:
                pass
        return _ok({}, "Logged out.")
