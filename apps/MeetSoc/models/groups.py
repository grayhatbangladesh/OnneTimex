import uuid

from django.conf import settings
from django.db import models


class Group(models.Model):
    PRIVACY_CHOICES = [
        ("public", "Public"),
        ("private", "Private"),
        ("secret", "Secret"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=255)
    description = models.TextField(blank=True)
    cover_photo = models.ImageField(upload_to="groups/covers/%Y/%m/", blank=True, null=True)
    avatar = models.ImageField(upload_to="groups/avatars/%Y/%m/", blank=True, null=True)
    privacy = models.CharField(max_length=20, choices=PRIVACY_CHOICES, default="public")
    category = models.CharField(max_length=100, blank=True)
    rules = models.JSONField(default=list, blank=True)
    members_count = models.PositiveIntegerField(default=0)
    posts_count = models.PositiveIntegerField(default=0)
    is_on_hold = models.BooleanField(default=False, help_text="Held by admin — hidden from all users")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="groups_created"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "groups_group"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class GroupMembership(models.Model):
    ROLE_CHOICES = [
        ("admin", "Admin"),
        ("moderator", "Moderator"),
        ("member", "Member"),
    ]
    STATUS_CHOICES = [
        ("active", "Active"),
        ("pending", "Pending"),
        ("banned", "Banned"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="member")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="group_invites_sent",
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "groups_groupmembership"
        constraints = [
            models.UniqueConstraint(fields=["group", "user"], name="unique_group_member"),
        ]


class GroupInvite(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("declined", "Declined"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="invites")
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="group_invites_created"
    )
    invited_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="group_invites_received"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "groups_groupinvite"
