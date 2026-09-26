"""Devaz Account URLs — mounted at /account/."""
from django.urls import path

from apps.accounts import views as v

urlpatterns = [
    path("auth/register/", v.RegisterView.as_view(), name="register"),
    path("auth/login/", v.LoginView.as_view(), name="login"),
    path("auth/refresh/", v.RefreshView.as_view(), name="token-refresh"),
    path("auth/logout/", v.LogoutView.as_view(), name="logout"),
    path("auth/verify-email/", v.VerifyEmailView.as_view(), name="verify-email"),
    path("auth/verify-phone/", v.VerifyPhoneView.as_view(), name="verify-phone"),
    path("auth/send-otp/", v.SendOTPView.as_view(), name="send-otp"),
    path("auth/password-reset/", v.PasswordResetRequestView.as_view(), name="password-reset"),
    path("auth/password-reset/confirm/", v.PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("auth/social/", v.SocialLoginView.as_view(), name="social-login"),
    path("me/", v.MeView.as_view(), name="me"),
    path("me/avatar/", v.AvatarUpdateView.as_view(), name="me-avatar"),
    path("me/cover/", v.CoverUpdateView.as_view(), name="me-cover"),
]