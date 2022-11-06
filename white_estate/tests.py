from unittest.mock import MagicMock, patch

from allauth.socialaccount.models import SocialApp

from base.tests import PostOnlyAPITests
from django.contrib.sites.models import Site
from django.test import (  # noqa: F401
    SimpleTestCase,
    TestCase,
    override_settings,
    tag,
)
from django.urls import reverse
from panta.factories import OriginalSegmentFactory, TagFactory
from panta.models import Tag

from .apis import EGWWritingsClient
from .conversion import Import


@patch('white_estate.apis.BackendApplicationClient')
@patch('white_estate.apis.OAuth2Session')
@override_settings(EGW_CLIENT_ID='id', EGW_CLIENT_SECRET='secret')
class EGWWritingsClientTests(SimpleTestCase):
    def test_init(self, session, backend_client):
        client = MagicMock()
        session.return_value = client
        EGWWritingsClient()
        backend_client.assert_called_once_with(client_id='id')
        session.assert_called_once_with(client=backend_client())
        client.fetch_token.assert_called_once_with(
            token_url='https://cpanel.egwwritings.org/o/token/',
            client_id='id',
            client_secret='secret',
            scope='writings search',
        )


@patch('white_estate.apis.BackendApplicationClient')
@patch('white_estate.apis.OAuth2Session')
class SimpleImportTests(SimpleTestCase):
    def test_init(self, session, backend_client):
        """
        A really basic test only because this class is used manually.
        """
        Import()

    def test_replace_inline_p(self, session, backend_client):
        client = Import()
        client.verbosity = 0
        text = '<p><br/>br</p> <p >abc<br/></p> y<p>z<br/></p>'
        expected = (
            '<span><br/>br</span><br/><br/> '
            '<br/><br/><span >abc<br/></span><br/><br/> '
            'y<br/><br/><span>z<br/></span>'
        )
        self.assertEqual(client.replace_inline_p(text), expected)


@patch('white_estate.apis.BackendApplicationClient')
@patch('white_estate.apis.OAuth2Session')
class ImportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.segment = OriginalSegmentFactory(key='1234.56')
        cls.tag = TagFactory(name='Tag 1')

    def test_get_tag(self, session, backend_client):
        client = Import()
        tag_item = client.get_tag('Tag 1')
        self.assertEqual(tag_item.pk, self.tag.pk)

        tag_item = client.get_tag('Tag 2')
        self.assertEqual(tag_item.name, 'Tag 2')
        self.assertEqual(tag_item.slug, 'tag-2')
        self.assertEqual(Tag.objects.count(), 2)

        with self.assertNumQueries(0):
            client.get_tag('Tag 1')

    def test_work_exists(self, session, backend_client):
        client = Import()
        self.assertFalse(client.work_exists({'book_id': 1}))
        self.assertFalse(client.work_exists({'pubnr': 1}))

        self.assertTrue(client.work_exists({'book_id': 1234}))
        self.assertTrue(client.work_exists({'pubnr': 1234}))


class WhiteEstateSocialAccountAPITests(PostOnlyAPITests):
    urls = {
        'auth_server_redirect': reverse('white-estate_auth_server'),
        'callback_create': reverse('white-estate_callback_login'),
        'callback_connect': reverse('white-estate_callback_connect'),
    }

    def test_login_url(self):
        white_estate = SocialApp.objects.create(
            provider='white-estate',
            name='EGW Estate',
            client_id='12345',
            secret='secret',
        )
        white_estate.sites.add(Site.objects.get())
        res = self.client.post(self.urls['auth_server_redirect'], {})
        self.assertEqual(res.status_code, 200)
        expected = (
            'https://cpanel.egwwritings.org/o/authorize/',
            'client_id=12345&redirect_uri='
            'https%3A%2F%2Ftestserver%2Fauth%2Fsocial%2Fwhite-estate%2F'
            'callback%2F&scope=user_info&response_type=code&state=',
        )
        result = res.json()['url'].split('?')
        self.assertEqual(result[0], expected[0])
        state = 'state='
        result = {
            state if i.startswith(state) else i for i in result[1].split('&')
        }
        self.assertEqual(result, set(expected[1].split('&')))

    def test_validate_state(self):
        res = self.client.post(self.urls['callback_create'], {'state': '123'})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json(), {'state': ['State did not match.']})

        self.client.force_login(self.user)
        res = self.client.post(self.urls['callback_connect'], {'state': '123'})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json(), {'state': ['State did not match.']})

    # TODO Maybe test these with Selenium
    # def test_login_callback_create(self):
    # def test_relogin_callback(self):
    # def test_login_callback_connect(self):
    #     self.assertEqual(len(mail.outbox), 1)
    # def test_username_exists(self):
    # def test_email_exists(self):
    # def test_connected_accounts(self):
    # def test_disconnect_account(self):
