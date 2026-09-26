import uuid

from django.conf import settings
from django.db import models


class Conversation(models.Model):
    TYPE_CHOICES = [
        ("direct", "Direct"),
        ("group", "Group"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="direct")
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL, through="ConversationParticipant", related_name="conversations"
    )
    name = models.CharField(max_length=255, null=True, blank=True)
    avatar = models.ImageField(upload_to="conversations/%Y/%m/", null=True, blank=True)
    last_message = models.ForeignKey(
        "Message", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "messages_conversation"


class ConversationParticipant(models.Model):
    ROLE_CHOICES = [
        ("admin", "Admin"),
        ("member", "Member"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="cp")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="member")
    is_muted = models.BooleanField(default=False)
    last_read_at = models.DateTimeField(null=True, blank=True)
    unread_count = models.PositiveIntegerField(default=0)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "messages_conversationparticipant"
        constraints = [
            models.UniqueConstraint(
                fields=["conversation", "user"], name="unique_conversation_participant"
            ),
        ]


class Message(models.Model):
    MESSAGE_TYPE_CHOICES = [
        ("text", "Text"),
        ("image", "Image"),
        ("video", "Video"),
        ("audio", "Audio"),
        ("file", "File"),
        ("sticker", "Sticker"),
        ("gif", "Gif"),
        ("call_log", "Call log"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPE_CHOICES, default="text")
    content = models.TextField(blank=True)
    media = models.FileField(upload_to="messages/media/%Y/%m/", null=True, blank=True)
    reply_to = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL)
    reactions = models.JSONField(default=dict, blank=True)
    is_edited = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    is_on_hold = models.BooleanField(default=False, help_text="Held by admin — hidden from all users")
    seen_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL, through="MessageSeen", related_name="messages_seen"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "messages_message"
        ordering = ["created_at"]


class MessageSeen(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="seen_records")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    seen_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "messages_messageseen"
        constraints = [
            models.UniqueConstraint(fields=["message", "user"], name="unique_message_seen"),
        ]
