from django.apps import AppConfig


class MediaConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    # Must be the importable path: "Media" alone raises ModuleNotFoundError.
    name = "apps.Media"
