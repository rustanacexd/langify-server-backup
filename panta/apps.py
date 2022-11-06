from django.apps import AppConfig


class PantaConfig(AppConfig):
    name = 'panta'

    def ready(self):
        # Register signals
        from . import signals  # noqa: F401
