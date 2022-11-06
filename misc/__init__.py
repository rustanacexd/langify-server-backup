import logging

from django.conf import settings

default_app_config = 'misc.apps.MiscConfig'


class RequireTestFalse(logging.Filter):
    def filter(self, record):
        return not settings.TEST


class RequireSentryDSN(logging.Filter):
    def filter(self, record):
        return bool(settings.SENTRY_DSN)
