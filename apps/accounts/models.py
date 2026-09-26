import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------
E164_VALIDATOR = RegexValidator(
    r"^\+[1-9]\d{7,14}$",
    "Phone must be in international format, example +8801712345678",
)
USERNAME_VALIDATOR = RegexValidator(
    r"^[a-z0-9_.]{3,30}$",
    "3-30 chars: lowercase letters, numbers, underscore, dot.",
)

# 1. USER + PROFILE
class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, phone, password, **extra_fields):
        if not phone:
            raise ValueError("Phone is required")

        # Empty string would break UNIQUE, so blank email/username are always stored as NULL.
        email = extra_fields.pop("email", None)
        extra_fields["email"] = self.normalize_email(email).lower() if email else None
        username = extra_fields.pop("username", None)
        extra_fields["username"] = username.lower() if username else None

        user = self.model(phone=phone, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(self, phone, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(phone, password, **extra_fields)

    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if not extra_fields["is_staff"] or not extra_fields["is_superuser"]:
            raise ValueError("Superuser must have is_staff=True and is_superuser=True")
        return self._create_user(phone, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class Gender(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"
        OTHER = "other", "Other"
        PREFER_NOT = "prefer_not", "Prefer not to say"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        WARNING = "warning", "Warning"
        SUSPENDED = "suspended", "Suspended"
        BANNED = "banned", "Banned"
        PENDING_DELETION = "pending_deletion", "Pending deletion"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone = models.CharField(max_length=16, unique=True, validators=[E164_VALIDATOR])
    email = models.EmailField(unique=True, null=True, blank=True)
    username = models.CharField(
        max_length=30, unique=True, null=True, blank=True, validators=[USERNAME_VALIDATOR]
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, choices=Gender.choices, default=Gender.PREFER_NOT)

    # Verified = timestamp (NULL means not verified). Blue-tick / "verified badge" belongs to meetsoc, not here.
    phone_verified_at = models.DateTimeField(null=True, blank=True)
    email_verified_at = models.DateTimeField(null=True, blank=True)

    # Account state checked at every login. Keep is_active in sync with it (Django admin uses is_active).
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["first_name"]

    objects = UserManager()

    class Meta:
        db_table = "account_users"

    @property
    def full_name(self):
        return " ".join(x for x in [self.first_name, self.last_name] if x).strip()

    @property
    def is_verified(self):
        """True if the user currently holds an active blue badge."""
        try:
            from apps.MeetSoc.models import BlueVerificationRequest

            return bool(BlueVerificationRequest.get_active_for_user(self))
        except Exception:
            return False

    @property
    def avatar_url(self):
        """Resolve the profile avatar media id to a URL (B2 / media app)."""
        profile = getattr(self, "profile", None)
        media_id = getattr(profile, "avatar_media_id", None)
        if not media_id:
            return ""
        try:
            from apps.Media.models import Media

            m = Media.objects.filter(id=media_id).first()
            return (getattr(m, "url", "") or "") if m else ""
        except Exception:
            return ""

    def __str__(self):
        return self.username or self.phone


class UserProfile(models.Model):
    class Relationship(models.TextChoices):
        UNSPECIFIED = "unspecified", "Unspecified"
        SINGLE = "single", "Single"
        IN_RELATIONSHIP = "relationship", "In a relationship"
        MARRIED = "married", "Married"
        COMPLICATED = "complicated", "It's complicated"
        DIVORCED = "divorced", "Divorced"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")

    # Files live in the `media` app / Backblaze B2. Only the media id is stored here (no cross-app FK).
    avatar_media_id = models.UUIDField(null=True, blank=True)
    cover_media_id = models.UUIDField(null=True, blank=True)

    bio = models.CharField(max_length=500, blank=True)
    website = models.URLField(blank=True)
    country = models.CharField(max_length=2, blank=True)          # ISO code, e.g. "BD"
    city = models.CharField(max_length=60, blank=True)
    hometown = models.CharField(max_length=60, blank=True)
    hobbies = models.CharField(max_length=500, blank=True)
    work = models.CharField(max_length=200, blank=True)
    education = models.CharField(max_length=200, blank=True)
    relationship = models.CharField(
        max_length=20, choices=Relationship.choices, default=Relationship.UNSPECIFIED
    )
    public_contacts = models.CharField(max_length=200, blank=True)

    social_links = models.JSONField(default=dict, blank=True)
    other_info = models.JSONField(default=dict, blank=True)

    # Denormalized counters (kept in sync by views/services)
    posts_count = models.PositiveIntegerField(default=0)
    friends_count = models.PositiveIntegerField(default=0)
    followers_count = models.PositiveIntegerField(default=0)
    following_count = models.PositiveIntegerField(default=0)
    is_private = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def avatar(self):
        """Resolve avatar media id → URL (media app / B2)."""
        if not self.avatar_media_id:
            return None
        try:
            from apps.Media.models import Media

            m = Media.objects.filter(id=self.avatar_media_id).first()
            return m if m else None
        except Exception:
            return None

    @property
    def cover_photo(self):
        """Resolve cover media id → URL (media app / B2)."""
        if not self.cover_media_id:
            return None
        try:
            from apps.Media.models import Media

            m = Media.objects.filter(id=self.cover_media_id).first()
            return m if m else None
        except Exception:
            return None

    def __str__(self):
        return f"Profile of {self.user_id}"


# ---------------------------------------------------------------------------
# Signals — auto-create a profile for every new Devaz account
# ---------------------------------------------------------------------------
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)

