import uuid

from django.db import models


class Media(models.Model):
    """A single uploaded file referenced by id.

    `UserProfile.avatar_media_id` / `cover_media_id` point here (UUID, no FK
    across apps). Serializers resolve the id to `Media.url`.
    """

    KIND_IMAGE = "image"
    KIND_VIDEO = "video"
    KIND_FILE = "file"
    KIND_CHOICES = [
        (KIND_IMAGE, "Image"),
        (KIND_VIDEO, "Video"),
        (KIND_FILE, "File"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.FileField(upload_to="media/%Y/%m/")
    original_name = models.CharField(max_length=255, blank=True)
    kind = models.CharField(max_length=16, choices=KIND_CHOICES, default=KIND_IMAGE)
    content_type = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def url(self):
        """Public URL of the stored file (works with MEDIA_URL/media route)."""
        try:
            return self.file.url if self.file else ""
        except Exception:
            return ""

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.original_name or str(self.id)
