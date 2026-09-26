import uuid

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class Reaction(models.Model):
    REACTION_TYPES = [
        ("like", "Like"),
        ("love", "Love"),
        ("haha", "Haha"),
        ("wow", "Wow"),
        ("sad", "Sad"),
        ("angry", "Angry"),
        ("care", "Care"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reactions")
    reaction_type = models.CharField(max_length=20, choices=REACTION_TYPES, default="like")
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    content_object = GenericForeignKey("content_type", "object_id")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "reactions_reaction"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "content_type", "object_id"],
                name="unique_reaction_per_object",
            ),
        ]
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]
