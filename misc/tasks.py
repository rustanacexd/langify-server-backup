from django.utils import timezone
from langify.celery import app
from panta.models import SegmentComment

from .models import DeveloperComment


@app.task
def delete_comments(model_name):
    """
    Deletes comments with an expired TTL.
    """
    if model_name == 'DeveloperComment':
        model = DeveloperComment
    elif model_name == 'SegmentComment':
        model = SegmentComment
    else:
        raise NotImplementedError
    _x, count = model.objects.filter(to_delete__lte=timezone.now()).delete()
    return count
