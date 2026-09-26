import logging

from celery import shared_task
from django.core.cache import cache
from django.utils import timezone

from apps.MeetSoc.models import Story

logger = logging.getLogger(__name__)


@shared_task
def cleanup_expired_stories():
    deleted, _ = Story.objects.filter(expires_at__lt=timezone.now()).delete()
    logger.info("cleanup_expired_stories removed %s rows", deleted)
    return deleted


@shared_task
def update_feed_cache(user_id):
    try:
        cache.delete_pattern(f"feed:{user_id}:*")
    except Exception:
        for i in range(1, 50):
            cache.delete(f"feed:{user_id}:{i}")


@shared_task
def compute_friend_suggestions(user_id):
    from apps.MeetSoc.services.friend_services import get_friend_suggestions
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.filter(pk=user_id).first()
    if user:
        get_friend_suggestions(user, limit=20)


@shared_task
def process_video_thumbnail(post_media_id):
    logger.info("process_video_thumbnail placeholder for %s", post_media_id)


@shared_task
def send_birthday_notifications():
    from django.contrib.auth import get_user_model

    from apps.MeetSoc.tasks.notification_tasks import send_notification_task

    User = get_user_model()
    today = timezone.now().date()
    users = User.objects.filter(date_of_birth__month=today.month, date_of_birth__day=today.day)
    for u in users:
        send_notification_task.delay(
            str(u.id),
            {
                "actor_id": None,
                "notification_type": "birthday",
                "verb": "Happy birthday!",
                "title": "MeetSoc",
                "body": "Happy birthday!",
                "data": {},
            },
        )


@shared_task
def generate_memories():
    from django.contrib.auth import get_user_model
    from apps.MeetSoc.models import Memory
    from apps.MeetSoc.models import Post

    User = get_user_model()
    today = timezone.now().date()
    for user in User.objects.all()[:1000]:
        posts = Post.objects.filter(
            author=user,
            created_at__month=today.month,
            created_at__day=today.day,
            created_at__year__lt=today.year,
        )
        for p in posts:
            Memory.objects.get_or_create(
                user=user,
                year=p.created_at.year,
                post=p,
                defaults={"summary": p.content[:500]},
            )


@shared_task
def send_weekly_email_digest(user_id):
    from django.contrib.auth import get_user_model
    from django.core.mail import send_mail
    from django.conf import settings

    User = get_user_model()
    user = User.objects.filter(pk=user_id).first()
    if user:
        send_mail(
            "Your MeetSoc weekly digest",
            "Here's what you missed this week.",
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=True,
        )
