from django.conf import settings

from .celery import app as celery_app  # noqa: F401

__all__ = ('__version__', 'celery_app')

__version__ = settings.VERSION
