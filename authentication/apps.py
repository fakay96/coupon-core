"""
Configuration for the Authentication app.

This class sets up the Django app configuration for the Authentication app,
defining its default settings and name.
"""

from django.apps import AppConfig


class AuthenticationConfig(AppConfig):
    """
    Configures the Authentication app.

    Attributes:
        default_auto_field (str): The type of primary key field to use by default.
        name (str): The name of the app.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "authentication"

    def ready(self):
        import authentication.v1.signals
