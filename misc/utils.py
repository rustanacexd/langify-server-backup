from base.constants import COMMENT_DELETION_DELAY
from django.core.cache import cache

from .tasks import delete_comments


def add_task_for_comments_deletion(kwargs):
    """
    Triggers max. 1 Celery task per minute if TTL was set on a comment.

    kwargs are from signals.
    """
    instance = kwargs['instance']
    model_name = instance._meta.model.__name__
    key = '{}_deletion_scheduled'.format(model_name)
    if instance.to_delete and not kwargs['raw'] and not cache.get(key):
        interval = 60
        # This comes first because the TTL has to expire before the task is run
        cache.set(key, True, timeout=interval)
        # Add interval to have max. 1 task per minute
        delete_comments.apply_async(
            args=(model_name,),
            countdown=COMMENT_DELETION_DELAY.total_seconds() + interval,
        )
