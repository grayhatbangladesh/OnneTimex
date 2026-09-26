import uuid

from django.conf import settings
from django.db import models


class SubscriptionPlan(models.Model):
    """Paid plans for the blue verification badge."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price_bdt = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price_usd = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    duration_days = models.PositiveIntegerField(default=30)
    features = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "verification_subscriptionplan"
        ordering = ["sort_order"]

    def __str__(self):
        return self.name


class BlueVerificationRequest(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="verification_requests"
    )
    plan = models.ForeignKey(
        SubscriptionPlan, on_delete=models.SET_NULL, null=True, blank=True, related_name="requests"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    nid_front = models.FileField(upload_to="verification/nid/%Y/%m/", blank=True, null=True)
    nid_back = models.FileField(upload_to="verification/nid/%Y/%m/", blank=True, null=True)
    note = models.TextField(blank=True)
    admin_note = models.TextField(blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "verification_bluerequest"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Verification({self.user_id}, {self.status})"

    @classmethod
    def get_active_for_user(cls, user):
        """Currently valid blue-badge request for a user (approved & not expired)."""
        from django.utils import timezone

        return (
            cls.objects.filter(
                user=user, status="approved", valid_from__lte=timezone.now(), valid_until__gt=timezone.now()
            ).first()
        )


class UserSubscription(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscriptions"
    )
    plan = models.ForeignKey(
        SubscriptionPlan, on_delete=models.PROTECT, related_name="subscriptions"
    )
    verification_request = models.ForeignKey(
        BlueVerificationRequest, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="subscriptions",
    )
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "verification_usersubscription"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Subscription({self.user_id}, {self.plan_id})"
