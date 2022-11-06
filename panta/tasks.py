import json

from langify.celery import app
from misc.apis import SlackClient

from . import models
from .api.external import QuotaExceeded


@app.task
def translate_segment_with_deepl():
    redis = app.broker_connection().default_channel.client
    key = 'next_deepl_segments'
    kwargs = redis.lpop(key)
    if kwargs:
        kwargs = json.loads(kwargs)
    else:
        # Queue empty
        slack = SlackClient()
        slack.to_dev(
            'My DeepL translation queue is empty. Do you have something to do '
            'for me? Thanks!'
        )
        return
    work = models.OriginalWork.objects.get(pk=kwargs['work'])
    try:
        work.get_deepl_translation(
            to=kwargs['language'], positions=(kwargs['position'],), celery=True
        )
    except QuotaExceeded:
        # Stop translation
        redis.lpush(key, json.dumps(kwargs))
        return
    except Exception:
        redis.lpush(key, json.dumps(kwargs))
        raise
    else:
        # Trigger translation of next segment with a two minutes delay
        translate_segment_with_deepl.apply_async(countdown=120)
