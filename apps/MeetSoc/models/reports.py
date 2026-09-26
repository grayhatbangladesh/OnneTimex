import uuid

from django.conf import settings
from django.db import models


class Report(models.Model):
    """User-submitted report for content moderation."""

    REASON_CHOICES = [
        ("spam", "Spam or Fake Content"),
        ("nudity", "Nudity or Sexual Content"),
        ("pornography", "Pornography"),
        ("violence", "Violence or Dangerous Content"),
        ("drugs", "Drugs or Controlled Substances"),
        ("hate_speech", "Hate Speech or Discrimination"),
        ("harassment", "Harassment or Bullying"),
        ("misinformation", "False Information or Misinformation"),
        ("scam", "Scam or Fraud"),
        ("intellectual_property", "Intellectual Property Violation"),
        ("suicide", "Suicide or Self-Harm"),
        ("terrorism", "Terrorism or Extremism"),
        ("child_exploitation", "Child Exploitation"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending Review"),
        ("reviewed", "Reviewed"),
        ("resolved", "Resolved"),
        ("held", "Held"),
        ("dismissed", "Dismissed"),
    ]

    CONTENT_TYPE_CHOICES = [
        ("post", "Post"),
        ("comment", "Comment"),
        ("message", "Message"),
        ("profile", "Profile"),
        ("page", "Page"),
        ("group", "Group"),
        ("product", "Product"),
        ("video", "Video"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reports_filed"
    )
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPE_CHOICES)
    content_id = models.UUIDField(help_text="ID of the reported content")
    reason = models.CharField(max_length=30, choices=REASON_CHOICES)
    description = models.TextField(blank=True, default="", help_text="Optional details from reporter")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reports_reviewed"
    )
    admin_note = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reports_report"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Report({self.reason}) on {self.content_type}/{self.content_id} by {self.reporter_id}"
