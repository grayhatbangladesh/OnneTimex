import uuid

from django.conf import settings
from django.db import models


class Call(models.Model):
    CALL_TYPE_CHOICES = [
        ("audio", "Audio"),
        ("video", "Video"),
    ]
    STATUS_CHOICES = [
        ("ringing", "Ringing"),
        ("active", "Active"),
        ("ended", "Ended"),
        ("missed", "Missed"),
        ("declined", "Declined"),
        ("busy", "Busy"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    call_type = models.CharField(max_length=20, choices=CALL_TYPE_CHOICES, default="video")
    caller = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="calls_initiated"
    )
    conversation = models.ForeignKey(
        "Conversation", on_delete=models.CASCADE, related_name="calls"
    )
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL, through="CallParticipant", related_name="calls"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="ringing")
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "calls_call"
        ordering = ["-created_at"]


class CallParticipant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    call = models.ForeignKey(Call, on_delete=models.CASCADE, related_name="call_participants")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(null=True, blank=True)
    left_at = models.DateTimeField(null=True, blank=True)
    is_muted = models.BooleanField(default=False)
    is_video_on = models.BooleanField(default=True)

    class Meta:
        db_table = "calls_callparticipant"
        constraints = [
            models.UniqueConstraint(fields=["call", "user"], name="unique_call_participant"),
        ]
