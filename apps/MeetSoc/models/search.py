import uuid

from django.conf import settings
from django.db import models


class TrendingTopic(models.Model):
    """Optional DB mirror; primary trending uses Redis sorted sets."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tag = models.CharField(max_length=100, unique=True)
    score = models.FloatField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "search_trendingtopic"
