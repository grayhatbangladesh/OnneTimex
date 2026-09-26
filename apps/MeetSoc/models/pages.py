import uuid

from django.conf import settings
from django.db import models


class Page(models.Model):
    FEATURE_CHOICES = [
        ("feed", "Feed Posts"),
        ("marketplace", "Marketplace"),
        ("groups", "Groups"),
        ("stories", "Stories"),
        ("videos", "Videos"),
        ("reels", "Reels"),
        ("live", "Live"),
        ("events", "Events"),
        ("messaging", "Messaging"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=255)
    category = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    avatar = models.ImageField(upload_to="pages/avatars/%Y/%m/", blank=True, null=True)
    cover_photo = models.ImageField(upload_to="pages/covers/%Y/%m/", blank=True, null=True)
    website = models.URLField(blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    address = models.JSONField(default=dict, blank=True)
    verified = models.BooleanField(default=False)
    is_on_hold = models.BooleanField(default=False, help_text="Held by admin — hidden from all users")
    allowed_features = models.JSONField(
        default=list, blank=True,
        help_text='List of feature keys this page can use, e.g. ["feed", "marketplace"]',
    )
    followers_count = models.PositiveIntegerField(default=0)
    likes_count = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="pages_created"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "pages_page"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class PageFollower(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name="followers_rel")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_liked = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "pages_pagefollower"
        constraints = [
            models.UniqueConstraint(fields=["page", "user"], name="unique_page_follower"),
        ]


class PageAdmin(models.Model):
    ROLE_CHOICES = [
        ("owner", "Owner"),
        ("admin", "Admin"),
        ("editor", "Editor"),
        ("analyst", "Analyst"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name="admins")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="editor")

    class Meta:
        db_table = "pages_pageadmin"
        constraints = [
            models.UniqueConstraint(fields=["page", "user"], name="unique_page_admin"),
        ]
