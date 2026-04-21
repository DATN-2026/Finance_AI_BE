from django.apps import AppConfig


class AuthenticationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core.authentication"

    def ready(self):
        # Import schema extensions for drf-spectacular
        from . import schema  # noqa: F401
