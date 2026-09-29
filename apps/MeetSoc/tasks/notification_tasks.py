import logging

from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache

from apps.MeetSoc.models import Notification

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task
def send_fcm_push_task(device_tokens, title, body, data):
    if not device_tokens:
        return
    try:
        from pyfcm import FCMNotification
        from django.conf import settings

        api_key = getattr(settings, "FCM_SERVER_KEY", "") or ""
        if not api_key:
            logger.warning("FCM_SERVER_KEY not set; skipping push")
            return
        push_service = FCMNotification(api_key=api_key)
        for token in device_tokens:
            push_service.notify_single_device(
                registration_id=token,
                message_title=title,
                message_body=body,
                data_message=data or {},
            )
    except Exception:
        logger.exception("send_fcm_push_task failed")


@shared_task(bind=True, max_retries=3)
def send_notification_task(self, recipient_id, notif_data):
    try:
        _create_and_send_notification(recipient_id, notif_data)
    except Exception as exc:
        logger.exception("send_notification_task failed")
        raise self.retry(exc=exc, countdown=30)


def _create_and_send_notification(recipient_id, notif_data):
    """Create notification in DB and send via WebSocket + push."""
    recipient = User.objects.get(pk=recipient_id)
    n = Notification.objects.create(
        recipient=recipient,
        actor_id=notif_data.get("actor_id"),
        notification_type=notif_data.get("notification_type", "message"),
        verb=notif_data.get("verb", ""),
        target_type_id=notif_data.get("target_type_id"),
        target_id=notif_data.get("target_id"),
        data=notif_data.get("data", {}),
    )
    channel_layer = get_channel_layer()
    group = f"notification_user_{recipient_id}"
    payload = {
        "type": "notify",
        "notification": {
            "id": str(n.id),
            "verb": n.verb,
            "notification_type": n.notification_type,
            "data": n.data,
            "created_at": n.created_at.isoformat(),
        },
    }
    try:
        async_to_sync(channel_layer.group_send)(group, payload)
    except Exception:
        logger.warning("WebSocket group_send failed for user %s", recipient_id)
    count = Notification.objects.filter(recipient=recipient, is_read=False).count()
    cache.set(f"unread_notif:{recipient_id}", count, timeout=None)
    try:
        async_to_sync(channel_layer.group_send)(
            group,
            {"type": "unread_count", "count": count},
        )
    except Exception:
        pass
    try:
        tokens = list(recipient.fcm_devices.values_list("token", flat=True))
        if tokens:
            send_fcm_push_task.delay(
                tokens,
                notif_data.get("title", "MeetSoc"),
                notif_data.get("body", n.verb),
                notif_data.get("data", {}),
            )
    except Exception:
        pass


def notify(recipient_id, actor_id, notification_type, verb, data=None, target_type=None, target_id=None):
    from django.contrib.contenttypes.models import ContentType

    target_type_id = None
    if target_type and target_id:
        try:
            # All of these models live in apps.MeetSoc (app_label "meetsoc"), so
            # resolve the ContentType from the model class instead of guessing
            # app labels (the old "posts.Post"/"groups.Group" lookups never matched).
            from apps.MeetSoc.models import Comment, Group, Page, Post, Product

            model_map = {
                "post": Post,
                "comment": Comment,
                "group": Group,
                "page": Page,
                "product": Product,
                "user": User,
            }
            model_cls = model_map.get(target_type)
            if model_cls is not None:
                target_type_id = ContentType.objects.get_for_model(model_cls).id
        except Exception:
            pass

    notif_data = {
        "actor_id": str(actor_id) if actor_id is not None else None,
        "notification_type": notification_type,
        "verb": verb,
        "data": data or {},
        "target_type_id": target_type_id,
        "target_id": str(target_id) if target_id else None,
    }
    try:
        # Only queue to Celery when it is explicitly enabled AND the broker is
        # reachable; otherwise create the notification right now so the row is
        # guaranteed to exist for the client.
        dispatched = False
        if getattr(settings, "CELERY_ENABLED", False):
            try:
                send_notification_task.delay(recipient_id, notif_data)
                dispatched = True
            except Exception:
                logger.warning("Celery broker unavailable, creating notification synchronously")
        if not dispatched:
            _create_and_send_notification(recipient_id, notif_data)
    except Exception:
        logger.exception("Synchronous notification creation also failed")
