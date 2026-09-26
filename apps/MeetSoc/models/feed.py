import uuid

from django.conf import settings
from django.db import models


class SavedPost(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_posts")
    post = models.ForeignKey("Post", on_delete=models.CASCADE, related_name="saved_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "feed_savedpost"
        constraints = [
            models.UniqueConstraint(fields=["user", "post"], name="unique_saved_post"),
        ]


class FeedHide(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="feed_hides")
    post = models.ForeignKey("Post", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "feed_feedhide"
        constraints = [
            models.UniqueConstraint(fields=["user", "post"], name="unique_feed_hide"),
        ]


class FeedSnooze(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="feed_snoozes")
    snoozed_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="snoozed_by"
    )
    until = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "feed_feedsnooze"
        constraints = [
            models.UniqueConstraint(fields=["user", "snoozed_user"], name="unique_snooze_pair"),
        ]


class RecentSearch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recent_searches")
    query = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "feed_recentsearch"
        ordering = ["-created_at"]
