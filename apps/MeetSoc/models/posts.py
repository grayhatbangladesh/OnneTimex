import uuid

from django.conf import settings
from django.db import models
from django.utils.text import slugify


class ContentCategory(models.Model):
    """Primary category for video/text posts (TikTok/Facebook-style feed buckets)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, db_index=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "posts_contentcategory"
        ordering = ["sort_order", "name"]

    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            base = slugify(self.name)[:120] or str(self.id)
            self.slug = base
            if ContentCategory.objects.exclude(pk=self.pk).filter(slug=self.slug).exists():
                self.slug = f"{base}-{str(self.id)[:8]}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ContentTag(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=100, unique=True, db_index=True)

    class Meta:
        db_table = "posts_contenttag"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            base = slugify(self.name)[:80] or str(self.id)
            self.slug = base
            if ContentTag.objects.exclude(pk=self.pk).filter(slug=self.slug).exists():
                self.slug = f"{base}-{str(self.id)[:8]}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Post(models.Model):
    POST_TYPE_CHOICES = [
        ("text", "Text"),
        ("photo", "Photo"),
        ("video", "Video"),
        ("link", "Link"),
        ("feeling", "Feeling"),
        ("checkin", "Checkin"),
        ("shared", "Shared"),
    ]
    PRIVACY_CHOICES = [
        ("public", "Public"),
        ("friends", "Friends"),
        ("only_me", "Only me"),
        ("custom", "Custom"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="posts")
    content = models.TextField(blank=True)
    post_type = models.CharField(max_length=20, choices=POST_TYPE_CHOICES, default="text")
    privacy = models.CharField(max_length=20, choices=PRIVACY_CHOICES, default="public")
    feeling = models.CharField(max_length=120, null=True, blank=True)
    location = models.JSONField(null=True, blank=True)
    link_preview = models.JSONField(null=True, blank=True)
    tagged_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="tagged_in_posts"
    )
    shared_post = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="shares"
    )
    group = models.ForeignKey(
        "Group", null=True, blank=True, on_delete=models.CASCADE, related_name="posts"
    )
    page = models.ForeignKey(
        "Page", null=True, blank=True, on_delete=models.CASCADE, related_name="posts"
    )
    category = models.ForeignKey(
        ContentCategory,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="posts",
    )
    tags = models.ManyToManyField(ContentTag, blank=True, related_name="posts")
    is_edited = models.BooleanField(default=False)
    is_anonymous = models.BooleanField(default=False, help_text="Hide author identity from all viewers")
    is_on_hold = models.BooleanField(default=False, help_text="Held by admin — hidden from all users")
    reactions_count = models.JSONField(default=dict, blank=True)
    comments_count = models.PositiveIntegerField(default=0)
    shares_count = models.PositiveIntegerField(default=0)
    views_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "posts_post"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["author", "-created_at"]),
            models.Index(fields=["category", "-created_at"]),
        ]


class PostMedia(models.Model):
    MEDIA_TYPE_CHOICES = [
        ("image", "Image"),
        ("video", "Video"),
        ("gif", "Gif"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="media_items")
    file = models.FileField(upload_to="posts/media/%Y/%m/")
    media_type = models.CharField(max_length=20, choices=MEDIA_TYPE_CHOICES, default="image")
    thumbnail = models.ImageField(upload_to="posts/thumbs/%Y/%m/", null=True, blank=True)
    width = models.PositiveIntegerField(default=0)
    height = models.PositiveIntegerField(default=0)
    duration = models.FloatField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "posts_postmedia"
        ordering = ["order", "id"]


class Story(models.Model):
    MEDIA_TYPE_CHOICES = [
        ("image", "Image"),
        ("video", "Video"),
        ("text", "Text"),
    ]
    PRIVACY_CHOICES = [
        ("public", "Public"),
        ("friends", "Friends"),
        ("close_friends", "Close friends"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="stories")
    media = models.FileField(upload_to="stories/%Y/%m/", blank=True, null=True)
    media_type = models.CharField(max_length=20, choices=MEDIA_TYPE_CHOICES, default="image")
    text_content = models.TextField(null=True, blank=True)
    background_color = models.CharField(max_length=32, null=True, blank=True)
    stickers = models.JSONField(null=True, blank=True)
    music = models.JSONField(null=True, blank=True)
    privacy = models.CharField(max_length=20, choices=PRIVACY_CHOICES, default="friends")
    views_count = models.PositiveIntegerField(default=0)
    reactions_count = models.PositiveIntegerField(default=0)
    comments_count = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "posts_story"
        ordering = ["-created_at"]

    @property
    def author_name(self):
        # আপনার কাস্টম ইউজার মডেলে fullName বা username যা আছে তা এখানে দিবেন
        return self.author.full_name if hasattr(self.author, 'full_name') else self.author.username

    @property
    def author_avatar(self):
        # 'related_name="profile"' হওয়ার কারণে এখানে সরাসরি .profile হবে
        if hasattr(self.author, 'profile') and self.author.profile.avatar:
            return self.author.profile.avatar.url
        return None


class StoryView(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name="views")
    viewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "posts_storyview"
        constraints = [
            models.UniqueConstraint(fields=["story", "viewer"], name="unique_story_view"),
        ]


class StoryComment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name="story_comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="story_comments")
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies")
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "posts_storycomment"
        ordering = ["-created_at"]


class PostView(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="post_views")
    viewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "posts_postview"
        constraints = [
            models.UniqueConstraint(fields=["post", "viewer"], name="unique_post_view"),
        ]


class StoryReaction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name="reactions")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="story_reactions")
    reaction_type = models.CharField(max_length=20, default="love")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "posts_storyreaction"
        constraints = [
            models.UniqueConstraint(fields=["story", "user"], name="unique_story_reaction"),
        ]


class PostReaction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="reactions")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="post_reactions")
    reaction_type = models.CharField(max_length=20, default="like")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "posts_postreaction"
        constraints = [
            models.UniqueConstraint(fields=["post", "user"], name="unique_post_reaction"),
        ]
