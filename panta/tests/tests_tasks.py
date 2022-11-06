import json
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, tag  # noqa: F401
from langify.celery import app
from panta import models
from panta.api.external import QuotaExceeded
from panta.tasks import translate_segment_with_deepl


@patch('panta.tasks.translate_segment_with_deepl.apply_async')
@patch('panta.models.OriginalWork', spec=models.OriginalWork)
class TranslateSegmentWithDeepLTests(SimpleTestCase):
    key = 'next_deepl_segments'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.redis = app.broker_connection().default_channel.client

    def tearDown(self):
        self.redis.delete(self.key)

    def add_item_to_queue(self):
        self.redis.rpush(
            self.key, json.dumps({'work': 1, 'language': 'x', 'position': 1})
        )

    def test_normal_workflow(self, model, task):
        self.add_item_to_queue()
        instance = MagicMock()
        model.objects.get.return_value = instance
        translate_segment_with_deepl()
        model.objects.get.assert_called_once_with(pk=1)
        instance.get_deepl_translation.assert_called_once_with(
            to='x', positions=(1,), celery=True
        )
        task.assert_called_once_with(countdown=120)
        self.assertEqual(self.redis.llen(self.key), 0)

    def test_empty_queue(self, model, task):
        self.assertEqual(self.redis.llen(self.key), 0)
        translate_segment_with_deepl()
        model.objects.get.assert_not_called()

    def test_quota_exceeded(self, model, task):
        self.add_item_to_queue()
        instance = MagicMock()
        instance.get_deepl_translation.side_effect = QuotaExceeded
        model.objects.get.return_value = instance
        translate_segment_with_deepl()
        instance.get_deepl_translation.assert_called_once()
        task.assert_not_called()
        self.assertEqual(self.redis.llen(self.key), 1)

    def test_excpetion(self, model, task):
        self.add_item_to_queue()
        instance = MagicMock()
        instance.get_deepl_translation.side_effect = TypeError
        model.objects.get.return_value = instance
        with self.assertRaises(TypeError):
            translate_segment_with_deepl()
        task.assert_not_called()
        self.assertEqual(self.redis.llen(self.key), 1)
