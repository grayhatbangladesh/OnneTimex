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
        ser = self.get_serializer(request.user, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        profile = getattr(request.user, "profile", None)
        prof_data = request.data.get("profile")
        if prof_data and profile:
            pser = ProfileUpdateSerializer(profile, data=prof_data, partial=True)
            if pser.is_valid():
                pser.save()
        return _ok(MeSerializer(request.user).data, "Updated.")


class AvatarUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        media_id = request.data.get("media_id")
        profile = getattr(request.user, "profile", None)
        if not profile:
            return _err("NO_PROFILE", "Profile not found.")
        profile.avatar_media_id = media_id
        profile.save(update_fields=["avatar_media_id"])
        return _ok({"avatar_media_id": str(media_id) or None}, "Avatar updated.")


class CoverUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        media_id = request.data.get("media_id")
        profile = getattr(request.user, "profile", None)
        if not profile:
            return _err("NO_PROFILE", "Profile not found.")
        profile.cover_media_id = media_id
        profile.save(update_fields=["cover_media_id"])
        return _ok({"cover_media_id": str(media_id) or None}, "Cover updated.")


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
