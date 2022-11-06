import os

from celery import Celery

from django.conf import settings

# Set the default Django settings module for the 'celery' program
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'langify.settings')

app = Celery(
    'langify',
    broker='redis://:{}@{}:{}/{}'.format(
        settings.REDIS_PASSWORD,
        settings.REDIS_HOST,
        settings.REDIS_PERSISTENT_PORT,
        settings.REDIS_PERSISTENT_DATABASE,
    ),
)

# namespace='CELERY' means all celery-related configuration keys
# should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs
app.autodiscover_tasks()
