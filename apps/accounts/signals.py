"""
Django signals for auto-creating user profiles and other post-save actions.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.accounts.models import User, UserProfile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Automatically create a UserProfile when a new User is created."""
    if created:
        UserProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Ensure the user profile is saved whenever the user is saved."""
    try:
        if hasattr(instance, "profile"):
            instance.profile.save()
    except UserProfile.DoesNotExist:
        UserProfile.objects.get_or_create(user=instance)
