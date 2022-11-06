from unittest import skipIf
from unittest.mock import Mock, patch

import requests

from django.conf import settings
from django.test import TestCase, tag

from ..api import external

requests_mock = Mock(spec=requests)
requests_mock.post.return_value = Mock(
    status_code=200, json=lambda: {'translations': [{'text': 'mock'}]}
)


class DeepLAPITests(TestCase):
    def tearDown(self):
        requests_mock.reset_mock()

    @tag('online')
    @skipIf(not settings.DEEPL_KEY, 'DeepL key required.')
    def test_translate_live(self):
        """
        Tests the external endpoint without consuming the contingent.
        """
        api = external.DeepLAPI()
        res = api.translate(text='', target_lang='en')
        self.assertEqual(res.status_code, 200)

    @tag('offline')
    @patch('panta.api.external.requests', requests_mock)
    def test_translate_mock(self):
        api = external.DeepLAPI()
        res = api.translate(text='', target_lang='en')
        self.assertEqual(res.status_code, 200)

    @patch('panta.api.external.requests', requests_mock)
    def test_translate_iterable(self):
        api = external.DeepLAPI()
        for translation in api.translate_iterable('en', 'es', ('me', 'you')):
            self.assertEqual(translation, 'mock')
        self.assertEqual(len(requests_mock.method_calls), 2)

    @patch('panta.api.external.requests', requests_mock)
    def test_translate_iterable_celery(self):
        api = external.DeepLAPI()
        translations = api.translate_iterable(
            'en', 'es', (800 * 'a', 600 * 'b'), celery=True
        )
        for translation in translations:
            self.assertEqual(translation, 'mock')
        self.assertEqual(len(requests_mock.method_calls), 2)
