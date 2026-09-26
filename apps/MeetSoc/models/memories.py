import uuid

from django.conf import settings
from django.db import models


class Memory(models.Model):
    """On This Day snapshot for a user."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memories")
    year = models.PositiveIntegerField()
    post = models.ForeignKey("Post", on_delete=models.CASCADE, null=True, blank=True)
    summary = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "memories_memory"
        ordering = ["-year"]
