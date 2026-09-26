import uuid

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import models


class Notification(models.Model):
    TYPES = [
        ("friend_request", "Friend request"),
        ("friend_accept", "Friend accept"),
        ("post_like", "Post like"),
        ("post_comment", "Post comment"),
        ("comment_reply", "Comment reply"),
        ("post_share", "Post share"),
        ("follow", "Follow"),
        ("tag", "Tag"),
        ("mention", "Mention"),
        ("group_invite", "Group invite"),
        ("group_post", "Group post"),
        ("page_post", "Page post"),
        ("birthday", "Birthday"),
        ("memory", "Memory"),
        ("call_missed", "Call missed"),
        ("message", "Message"),
        ("live_started", "Live started"),
        ("event_reminder", "Event reminder"),
        ("report_update", "Report update"),
        ("payment_update", "Payment update"),
        ("product_update", "Product update"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="notifications_sent"
    )
    notification_type = models.CharField(max_length=40, choices=TYPES)
    verb = models.CharField(max_length=255)
    target_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    target_id = models.UUIDField(null=True, blank=True)
    data = models.JSONField(default=dict, blank=True)
    is_read = models.BooleanField(default=False)
    is_seen = models.BooleanField(default=False)
    push_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notifications_notification"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "-created_at"]),
        ]


class NotificationSettings(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_settings"
    )
    email_friend_requests = models.BooleanField(default=True)
    email_messages = models.BooleanField(default=True)
    email_posts = models.BooleanField(default=True)
    push_friend_requests = models.BooleanField(default=True)
    push_messages = models.BooleanField(default=True)
    push_posts = models.BooleanField(default=True)
    push_calls = models.BooleanField(default=True)

    class Meta:
        db_table = "notifications_notificationsettings"


class FCMDevice(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="fcm_devices")
    token = models.CharField(max_length=512, unique=True)
    device_id = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notifications_fcmdevice"
