from time import sleep

import requests

from django.conf import settings


class UnexpectedResponse(Exception):
    pass


class QuotaExceeded(Exception):
    pass


class DeepLAPI:
    def __init__(self):
        self.default_params = {
            'auth_key': settings.DEEPL_KEY,
            'tag_handling': 'xml',
            'non_splitting_tags': ['span'],
            # This lead to mistakes in XML handling. The support told me to
            # not use it.
            # 'preserve_formatting': 1,
        }

    def translate(self, **custom_params):
        params = self.default_params.copy()
        params.update(custom_params)
        response = requests.post(
            'https://api.deepl.com/v1/translate', params=params
        )
        return response

    def translate_iterable(
        self, source_lang, target_lang, texts, celery=False, **params
    ):
        """
        Yields translations while respecting the usage limitations.
        """
        self.celery = celery
        # Max 600 characters per minute are allowed
        characters_per_minute = 600
        length = 0
        texts = tuple(texts)
        self.inform(
            'Processing will take approx. {} min',
            round(len(''.join(texts)) / characters_per_minute, 1),
        )
        for n, text in enumerate(texts):
            if not celery:
                length += len(text)
                while length > characters_per_minute:
                    length -= characters_per_minute
                    self.inform('Waiting for 60 s')
                    sleep(60)

            self.inform('Processing text {}/{}', n + 1, len(texts))
            response = self.translate(
                text=text,
                source_lang=source_lang,
                target_lang=target_lang,
                **params
            )
            if response.status_code == 200:
                yield response.json()['translations'][0]['text']
            else:
                msg = '{} {}', response.status_code, response.text
                if celery:
                    if response.status_code == 456:
                        raise QuotaExceeded(msg)
                    raise UnexpectedResponse(msg)
                else:
                    self.inform(msg)
                break

    def inform(self, message, *args):
        if not (self.celery or settings.TEST):
            print(message.format(*args))
