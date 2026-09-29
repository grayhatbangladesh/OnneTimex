import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class AccountSuspension(models.Model):
    """Admin-imposed account suspension.

    `status` is computed, never stored: a suspension is "active" while it is
    permanent or its `ends_at` is still in the future, otherwise "expired".
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="suspensions"
    )
    reason = models.CharField(max_length=255, blank=True)
    is_permanent = models.BooleanField(default=False)
    ends_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "suspensions_accountsuspension"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Suspension({self.user_id}) — {self.status}"

    @property
    def status(self):
        """"active" while permanent or `ends_at` is in the future, else "expired"."""
        if self.is_permanent:
            return "active"
        if self.ends_at and self.ends_at > timezone.now():
            return "active"
        return "expired"
