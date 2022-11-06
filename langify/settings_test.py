from .settings import *  # noqa: F403

TEST = True

TEST_RUNNER = 'base.tests.TestRunner'

PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']

# It shouldn't make any sense to use cachalot in tests because the objects
# change all the time
INSTALLED_APPS.remove('cachalot')

CACHES = {
    'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}
}

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'

# Make sure that another database is used for testing
REDIS_PERSISTENT_DATABASE = 15

SENDFILE_BACKEND = 'sendfile.backends.development'

DEBUG_TOOLBAR_CONFIG = {'SHOW_TOOLBAR_CALLBACK': lambda request: False}
