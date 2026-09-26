from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"

    def ready(self):
        """Import signals to ensure they are connected when Django starts."""
        import apps.accounts.signals  # noqa: F401
