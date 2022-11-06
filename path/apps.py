from django.apps import AppConfig


class PathConfig(AppConfig):
    name = 'path'

    def ready(self):
        # Register signals
        from . import signals  # noqa: F401
