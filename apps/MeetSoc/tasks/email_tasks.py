import logging

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task(bind=True, max_retries=3)
def send_email_verification_task(self, user_id, otp_code):
    try:
        user = User.objects.get(pk=user_id)
        send_mail(
            subject="Verify your MeetSoc email",
            message=f"Your verification code is: {otp_code}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception as exc:
        logger.exception("send_email_verification_task failed")
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_password_reset_email_task(self, email, uid, token):
    try:
        link = f"https://app.meetsoc.com/reset-password?uid={uid}&token={token}"
        send_mail(
            subject="Reset your MeetSoc password",
            message=f"Use this link to reset your password: {link}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
    except Exception as exc:
        logger.exception("send_password_reset_email_task failed")
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_sms_otp_task(self, phone, otp_code):
    """
    SMS via provider (Twilio etc.) — log in development.
    """
    logger.info("SMS OTP to %s: %s", phone, otp_code)
    return True
