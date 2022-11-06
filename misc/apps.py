from django.apps import AppConfig


class MiscConfig(AppConfig):
    name = 'misc'

    def ready(self):
        # Register signals
        from . import signals  # noqa: F401
