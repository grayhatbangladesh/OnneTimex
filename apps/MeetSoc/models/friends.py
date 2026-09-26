
import uuid

from django.conf import settings
from django.db import models


class Friendship(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("blocked", "Blocked"),
        ("declined", "Declined"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="friendship_sent")
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="friendship_received")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users_friendship"
        constraints = [
            models.UniqueConstraint(
                fields=["sender", "receiver"],
                name="unique_friendship_pair",
            ),
        ]
        indexes = [
            models.Index(fields=["sender", "status"]),
            models.Index(fields=["receiver", "status"]),
        ]

    def __str__(self):
        return f"{self.sender_id} -> {self.receiver_id} ({self.status})"


class Follow(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    follower = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="following_rel")
    following = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="follower_rel")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "users_follow"
        constraints = [
            models.UniqueConstraint(fields=["follower", "following"], name="unique_follow_pair"),
        ]


class BlockList(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    blocker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="blocks_initiated")
    blocked = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="blocked_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "users_blocklist"
        constraints = [
            models.UniqueConstraint(fields=["blocker", "blocked"], name="unique_block_pair"),
        ]
