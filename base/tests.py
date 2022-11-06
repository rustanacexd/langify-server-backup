import datetime
import json
import re
from unittest import skipIf
from urllib.request import url2pathname

from allauth.account.models import EmailAddress
from randomcolor import RandomColor
from rest_framework import test

from base.constants import LANGUAGES, PERMISSIONS
from django.contrib.staticfiles.handlers import StaticFilesHandler
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import tag
from django.test.runner import DiscoverRunner
from django.urls import reverse
from langify.celery import app
from panta.models import Vote
from path.factories import UserFactory
from path.models import Reputation

try:
    from selenium.webdriver.firefox.webdriver import WebDriver
    from selenium.webdriver.support import expected_conditions
    from selenium.webdriver.support.ui import WebDriverWait
except ImportError:
    WebDriver = None

DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'

SPA_STATIC_REGEX = re.compile(r'^(?P<path>(/(js|css)/.+|.+\.js(on)?))$')

LANGUAGE_PERMISSIONS = dict(
    (
        ('addTranslation', False),
        ('changeTranslation', False),
        ('deleteTranslation', False),
        ('addComment', False),
        ('changeComment', False),
        ('deleteComment', True),
        ('flagComment', False),
        ('flagTranslation', False),
        ('flagUser', False),
        ('approveTranslation', False),
        ('disapproveTranslation', False),
        ('restoreTranslation', False),
        ('hideComment', False),
        ('reviewTranslation', False),
        ('trustee', False),
    )
)


class TestRunner(DiscoverRunner):
    """
    DiscoverRunner that purges all waiting Celery tasks after running tests.
    """

    def teardown_databases(self, old_config, **kwargs):
        super().teardown_databases(old_config, **kwargs)
        # Purge all waiting Celery tasks
        app.control.purge()


class SPAStaticFilesHandler(StaticFilesHandler):
    """
    Detect and serve static files for Django (STATIC_URL) and SPA (/).
    """

    def _should_handle(self, path):
        """
        Check if the path should be handled.
        """
        spa_static = SPA_STATIC_REGEX.match(path)
        django_static = super()._should_handle(path)
        return spa_static or django_static

    def file_path(self, url):
        """
        Return the relative path to the media file on disk for SPA and Django.
        """
        if url.startswith(self.base_url[2]):
            return super().file_path(url)

        return url2pathname(url)


class APITests(test.APITestCase):
    """
    Customizations for tests.
    """

    maxDiff = None
    basename = ''
    language_permissions = LANGUAGE_PERMISSIONS
    permissions = {l[0]: LANGUAGE_PERMISSIONS for l in LANGUAGES}

    @classmethod
    def get_user_field(cls, user=None, edits=0):
        """
        Returns the small user object that should be part of JSON responses.
        """
        user = user or cls.user
        user = {
            'id': user.public_id,
            'url': reverse('community_user_profile', args=(user.username,)),
            'username': user.username,
            'firstName': '',
            'lastName': '',
            'thumbnail': cls.get_svg_avatar(user),
            'contributions': {'edits': edits},
        }
        return user

    @classmethod
    def get_svg_avatar(cls, user=None, color=None):
        svg = (
            'data:image/svg+xml;utf8,%3Csvg '
            'xmlns=%27http://www.w3.org/2000/svg%27 width=%27120%27 '
            'height=%27120%27 viewBox=%270 0 120 120%27 %3E %3Crect '
            'width=%27100%%27 height=%27100%%27 fill=%27{color}%27/%3E '
            '%3Cpath fill=%27white%27 d=%27M39.954 71.846c6.948-2.788 '
            '13.629-4.185 20.048-4.185 6.413 0 13.094 1.396 20.043 4.185 '
            '6.947 2.793 10.424 6.444 10.424 '
            '10.961v7.662H29.53v-7.662c0-4.517 3.475-8.168 '
            '10.424-10.961zm30.734-16.303C67.724 58.514 64.156 60 60.002 '
            '60c-4.16 '
            '0-7.721-1.486-10.692-4.457-2.973-2.967-4.454-6.532-4.454-10.688 '
            '0-4.16 1.48-7.75 4.454-10.782 2.971-3.03 6.532-4.542 '
            '10.692-4.542 4.154 0 7.721 1.512 10.686 4.542 2.973 3.032 4.457 '
            '6.622 4.457 10.782.001 4.156-1.484 7.721-4.457 10.688z%27 /%3E '
            '%3C/svg%3E'
        )
        if color is None:
            color = RandomColor(user.username).generate()[0]
        return svg.format(color=color.replace('#', '%23'))

    @classmethod
    def get_url(cls, name, *args, **kwargs):
        if '-' not in name:
            name = f'{cls.basename}-{name}'
        relative_url = reverse(name, args=args, kwargs=kwargs)
        # return 'http://testserver{}'.format(relative_url)
        return relative_url

    @classmethod
    def date(cls, date):
        if isinstance(date, datetime.datetime):
            return date.strftime(DATETIME_FORMAT)
        else:
            return date.isoformat()

    @classmethod
    def set_reputation(cls, value, summand=0, user=None):
        """
        Sets the reputation for given user and language taken from self.work.
        """
        if isinstance(value, str):
            value = PERMISSIONS[value]
        Reputation.objects.update_or_create(
            user=user or cls.user,
            language=cls.work.language,
            defaults={'score': value + summand},
        )

    @classmethod
    def create_vote(cls, save=True, segment=None, **kwargs):
        defaults = dict(
            segment=segment or getattr(cls, '_segment', None) or cls._obj,
            user=cls.user,
            role='translator',
            value=1,
        )
        defaults.update(kwargs)
        if save:
            return Vote.objects.create(**defaults)
        return Vote(**defaults)

    @classmethod
    def get_segment(cls, segment=None, record=None, **kwargs):
        segment = (
            segment
            or getattr(cls, 'segment', None)
            or getattr(cls, '_segment', None)
            or getattr(cls, 'obj', None)
            or cls._obj
        )
        if 'records' in kwargs:
            record = record or getattr(cls, 'record', None)
            if not record:
                record = segment.history.select_related('history_user').latest()
        else:
            record = None
        comment = kwargs.get('comment')
        obj = {
            'id': segment.pk,
            'position': segment.position,
            'page': segment.page,
            'tag': segment.tag,
            'classes': segment.classes,
            'work': segment.work_id,
            'original': segment.original.content,
            'ai': None,
            'content': segment.content,
            'lockedBy': (
                segment.locked_by_id and cls.get_user_field(segment.locked_by)
            ),
            'reference': segment.original.reference,
            'progress': segment.progress,
            'chapter': segment.chapter.number if segment.chapter_id else None,
            'chapterPosition': segment.chapter_position,
            'workAbbreviation': segment.original.reference.split()[0],
            'translatorCanEdit': kwargs.get('translator_can_edit', True),
            'reviewerCanEdit': kwargs.get('reviewer_can_edit', True),
            'reviewerCanVote': kwargs.get('reviewer_can_vote', True),
            'trusteeCanVote': kwargs.get('trustee_can_vote', False),
            'created': cls.date(segment.created),
            'lastModified': cls.date(segment.last_modified),
            'statistics': {
                'comments': kwargs.get('comments', 0),
                'records': kwargs.get('records', 0),
                'lastCommented': comment and cls.date(comment.created),
                'lastEdited': record and cls.date(record.history_date),
                'lastEditedBy': (
                    record
                    and record.history_user
                    and cls.get_user_field(
                        record.history_user, edits=kwargs.get('edits', 1)
                    )
                ),
                'translators': {
                    'vote': kwargs.get('translators_vote', 0),
                    'user': kwargs.get('translators_user', 0),
                },
                'reviewers': {
                    'vote': kwargs.get('reviewers_vote', 0),
                    'user': kwargs.get('reviewers_user', 0),
                },
                'trustees': {
                    'vote': kwargs.get('trustees_vote', 0),
                    'user': kwargs.get('trustees_user', 0),
                },
            },
        }
        return obj


class PostOnlyAPITests(APITests):
    urls = {}

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(username='david', first_name='David')
        EmailAddress.objects.create(user=cls.user, email=cls.user.email)

    def test_list(self):
        for url in self.urls.values():
            self.client.force_login(self.user)
            res = self.client.get(url)
            self.assertEqual(res.status_code, 405)

    def test_options(self):
        for url in self.urls.values():
            self.client.force_login(self.user)
            res = self.client.options(url)
            self.assertEqual(res.status_code, 200)

    def test_put(self):
        for url in self.urls.values():
            self.client.force_login(self.user)
            res = self.client.put(url, {})
            self.assertEqual(res.status_code, 405)

    def test_patch(self):
        for url in self.urls.values():
            self.client.force_login(self.user)
            res = self.client.patch(url, {})
            self.assertEqual(res.status_code, 405)

    def test_delete(self):
        for url in self.urls.values():
            self.client.force_login(self.user)
            res = self.client.delete(url)
            self.assertEqual(res.status_code, 405)


@skipIf(WebDriver is None, 'Selenium not installed')
@tag('selenium')
class SeleniumTests(StaticLiveServerTestCase):
    maxDiff = None
    static_handler = SPAStaticFilesHandler

    @classmethod
    def setUpClass(cls, driver=None):
        super().setUpClass()
        cls.selenium = driver or WebDriver()
        cls.selenium.implicitly_wait(1)

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()

    def setUp(self):
        self.user = UserFactory(username='ellen')

    def wait_for(self, kind, value):
        # TODO
        # http://selenium-python.readthedocs.io/waits.html
        element = WebDriverWait(self.selenium, 2).until(
            expected_conditions.presence_of_element_located((kind, value))
        )
        return element

    def submit(self):
        button = 'button[type="submit"]'
        self.selenium.find_element_by_css_selector(button).click()
        # self.selenium.find_element_by_name('submit').click()

    def local_storage_retreive(self, key=None):
        # source: https://stackoverflow.com/a/46361900
        if key:
            return self.selenium.execute_script(
                'return window.localStorage.getItem("{}")'.format(key)
            )
        else:
            return self.selenium.execute_script(
                """
                var items = {}, ls = window.localStorage;
                for (var i = 0, k; i < ls.length; i++)
                  items[k = ls.key(i)] = ls.getItem(k);
                return items;
                """
            )

    def local_storage_set(self, key, value):
        self.selenium.execute_script(
            'window.localStorage.setItem("{}",{})'.format(
                key, json.dumps(value)
            )
        )

    def login(self):
        # TODO Can you allow not authenticated users in tests?
        self.selenium.get(self.live_server_url + reverse('login'))
        self.selenium.find_element_by_name('username').send_keys('ellen')
        self.selenium.find_element_by_name('password').send_keys('pw')
        self.submit()
