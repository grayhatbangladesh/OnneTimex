import uuid

from django.conf import settings
from django.db import models


class Comment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey("Post", on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comments")
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="replies")
    content = models.TextField()
    media = models.ImageField(upload_to="comments/%Y/%m/", null=True, blank=True)
    tagged_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="tagged_in_comments"
    )
    reactions_count = models.JSONField(default=dict, blank=True)
    replies_count = models.PositiveIntegerField(default=0)
    is_edited = models.BooleanField(default=False)
    is_on_hold = models.BooleanField(default=False, help_text="Held by admin — hidden from all users")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "comments_comment"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["post", "parent", "created_at"]),
        ]


class CommentReaction(models.Model):
    REACTION_TYPES = [
        ("like", "Like"),
        ("love", "Love"),
        ("haha", "Haha"),
        ("wow", "Wow"),
        ("sad", "Sad"),
        ("angry", "Angry"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name="reactions")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    reaction_type = models.CharField(max_length=10, choices=REACTION_TYPES, default="like")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "comments_reaction"
        unique_together = ("comment", "user")
