"""
Friend/follow-related serializers.
Auth, profile and public-user serializers live in apps.accounts.serializers.
"""
from apps.accounts.serializers import (  # noqa: F401
    FollowSerializer,
    FriendshipSerializer,
    LoginTokenObtainPairSerializer,
    MeSerializer,
    MeUpdateSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    ProfileUpdateSerializer,
    RegisterSerializer,
    SocialTokenSerializer,
    UserPublicLiteSerializer,
    UserPublicSerializer,
    VerifyEmailSerializer,
    VerifyPhoneSerializer,
    generate_otp,
    store_otp,
)

__all__ = [
    "FollowSerializer", "FriendshipSerializer", "LoginTokenObtainPairSerializer",
    "MeSerializer", "MeUpdateSerializer", "PasswordResetConfirmSerializer",
    "PasswordResetRequestSerializer", "ProfileUpdateSerializer", "RegisterSerializer",
    "SocialTokenSerializer", "UserPublicLiteSerializer", "UserPublicSerializer",
    "VerifyEmailSerializer", "VerifyPhoneSerializer", "generate_otp", "store_otp",
]
