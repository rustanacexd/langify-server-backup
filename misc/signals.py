from django.db.models.signals import post_save
from django.dispatch import receiver

from . import models
from .utils import add_task_for_comments_deletion


@receiver(
    post_save,
    sender=models.DeveloperComment,
    dispatch_uid='schedule_developer_comment_deletion',
)
def schedule_developer_comment_deletion(sender, **kwargs):
    """
    Triggers a Celery task if the comment has a TTL.
    """
    add_task_for_comments_deletion(kwargs)
