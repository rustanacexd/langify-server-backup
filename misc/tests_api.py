from inspect import cleandoc
from unittest import skipIf
from unittest.mock import MagicMock, call, patch

from requests.exceptions import ConnectionError as RequestsConnectionError
from rest_framework.exceptions import ValidationError

from base.serializers import LanguageSerializer
from base.tests import APITests, PostOnlyAPITests
from django.conf import settings
from django.contrib.auth.models import Group
from django.core import mail
from django.test import SimpleTestCase, override_settings, tag
from django.urls import reverse
from langify.routers import in_test_mode, set_test_mode
from misc import factories, models
from misc.apis import MailjetClient, Newsletter2GoClient
from path.factories import EmailAddressFactory, UserFactory


class LanguageSerializerTests(SimpleTestCase):
    def test_rtl_true_str(self):
        serializer = LanguageSerializer('ar')
        expected = {'code': 'ar', 'name': 'Arabic', 'rtl': True}
        self.assertEqual(serializer.data, expected)

    def test_rtl_true_tuple(self):
        serializer = LanguageSerializer(('ar', 'Arabic'))
        expected = {'code': 'ar', 'name': 'Arabic', 'rtl': True}
        self.assertEqual(serializer.data, expected)

    def test_rtl_false(self):
        serializer = LanguageSerializer('zh')
        expected = {'code': 'zh', 'name': 'Chinese', 'rtl': False}
        self.assertEqual(serializer.data, expected)


class PageTests(APITests):
    basename = 'page'

    @classmethod
    def setUpTestData(cls):
        cls.obj = models.Page.objects.create(slug='test-page', content='abc')
        cls.user = UserFactory()
        cls.data = {
            'slug': cls.obj.slug,
            'contactBtn': False,
            'rendered': cls.obj.content,
            'created': cls.date(cls.obj.created),
            'lastModified': cls.date(cls.obj.last_modified),
        }
        cls.url_detail = cls.get_url('detail', cls.obj.slug)

    def test_retrieve_public(self):
        models.Page.objects.update(public=True)
        res = self.client.get(self.url_detail)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), self.data)

    def test_retrieve_not_public(self):
        res = self.client.get(self.url_detail)
        self.assertEqual(res.status_code, 401)
        self.client.force_login(self.user)
        res = self.client.get(self.url_detail)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), self.data)

    def test_update_put(self):
        res = self.client.put(self.url_detail, {})
        self.assertEqual(res.status_code, 405)

    def test_update_patch(self):
        res = self.client.patch(self.url_detail, {})
        self.assertEqual(res.status_code, 405)

    def test_delete(self):
        res = self.client.delete(self.url_detail)
        self.assertEqual(res.status_code, 405)

    def test_automation(self):
        res = self.client.get(self.get_url('detail', 'automation'))
        self.assertEqual(res.status_code, 401)
        self.client.force_login(self.user)
        res = self.client.get(self.get_url('detail', 'automation'))
        self.assertEqual(res.status_code, 200)
        content = """
        # Automated text processing

        Some characters and strings are automatically replaced by others.
        Please let us know if you wish improvements!

        Note that `␣` stands for a space.

        ## All languages

        1. spaces at the beginning and end of paragraphs are removed
        2. *two spaces* → *one space*

        ## Some languages

        1. `'` → `’` (apostrophe)

        ## Amharic<a name="am"></a>

        1. `""` → `«»`
        2. `''` → `‹›`
        3. `...` → `…`

        ## Arabic<a name="ar"></a>

        1. `""` → `“”`
        2. `''` → `‘’`

        ## Berber<a name="ber"></a>

        1. `""` → `“”`
        2. `''` → `‘’`

        ## Bulgarian<a name="bg"></a>

        1. `""` → `“”`
        2. `''` → `‘’`
        3. `...` → `…`

        ## Central Kurdish<a name="ckb"></a>

        1. `""` → `“”`
        2. `''` → `‘’`

        ## Chinese<a name="zh"></a>

        1. `...` → `…`

        ## Czech<a name="cs"></a>

        1. `""` → `“”`
        2. `''` → `‘’`
        3. `...` → `…`

        ## French<a name="fr"></a>

        1. `""` → `“”`
        2. `''` → `‘’`

        ## German<a name="de"></a>

        1. `␣-␣` → `␣–␣`
        2. `....` → `...`
        3. `….` → `␣…`
        4. `.…` → `␣…`
        5. `""` → `„“`
        6. `''` → `‚‘`
        7. `...` → `…`

        ## Hindi<a name="hi"></a>

        1. `""` → `“”`
        2. `''` → `‘’`
        3. `...` → `…`

        ## Hungarian<a name="hu"></a>

        1. `EGW` → `E.␣G.␣W.`
        2. `""` → `„”`
        3. `''` → `’’`
        4. `...` → `…`

        ## Indonesian<a name="id"></a>

        1. `""` → `“”`
        2. `''` → `‘’`

        ## Italian<a name="it"></a>

        1. `""` → `“”`
        2. `''` → `‘’`

        ## Norwegian Bokmål<a name="nb"></a>

        1. `""` → `“”`
        2. `''` → `‘’`

        ## Persian<a name="fa"></a>

        1. `""` → `“”`
        2. `''` → `‘’`

        ## Polish<a name="pl"></a>

        1. `""` → `“”`
        2. `''` → `‘’`

        ## Portuguese<a name="pt"></a>

        1. `""` → `“”`
        2. `''` → `‘’`

        ## Romanian<a name="ro"></a>

        1. `""` → `“”`
        2. `''` → `‘’`

        ## Russian<a name="ru"></a>

        1. `""` → `“”`
        2. `''` → `‘’`
        3. `...` → `…`

        ## Kinyarwanda<a name="rw"></a>

        1. `""` → `“”`
        2. `''` → `‘’`
        3. `...` → `…`

        ## S'gaw Karen<a name="ksw"></a>

        1. `""` → `“”`
        2. `''` → `‘’`

        ## Spanish<a name="es"></a>

        1. `""` → `“”`
        2. `''` → `‘’`

        ## Swahili<a name="sw"></a>

        1. `""` → `“”`
        2. `''` → `‘’`

        ## Tagalog<a name="tl"></a>

        1. `""` → `“”`
        2. `''` → `‘’`

        ## Tonga (Zambia and Zimbabwe)<a name="toi"></a>

        1. `""` → `“”`
        2. `''` → `‘’`

        ## Turkish<a name="tr"></a>

        1. `""` → `“”`
        2. `''` → `‘’`
        3. `...` → `…`

        ## Ukrainian<a name="uk"></a>

        1. `""` → `“”`
        2. `''` → `‘’`
        3. `...` → `…`

        ## Vietnamese<a name="vi"></a>

        1. `""` → `“”`
        2. `''` → `‘’`
        """
        data = {
            'slug': 'automation',
            'contactBtn': False,
            'rendered': cleandoc(content),
            'created': None,
            'lastModified': None,
        }
        self.assertEqual(res.json(), data)


class DeveloperCommentTests(APITests):
    basename = 'developercomment'

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.obj = factories.DeveloperCommentFactory()
        cls.data = {
            'id': cls.obj.pk,
            'user': cls.get_user_field(cls.obj.user),
            'content': cls.obj.content,
            'toDelete': None,
            'created': cls.date(cls.obj.created),
            'lastModified': cls.date(cls.obj.last_modified),
        }
        cls.url_list = cls.get_url('list')
        cls.url_detail = cls.get_url('detail', cls.obj.pk)

    def setUp(self):
        self.client.force_login(self.user)

    def test_login_required(self):
        self.client.logout()
        res = self.client.get(self.url_list)
        self.assertEqual(res.status_code, 401)
        res = self.client.get(self.url_detail)
        self.assertEqual(res.status_code, 401)

    def test_list(self):
        res = self.client.get(self.url_list)
        self.assertEqual(res.json()['count'], 1)
        self.assertEqual(res.json()['results'][0], self.data)

    def test_retrieve(self):
        res = self.client.get(self.url_detail)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), self.data)

    def test_create(self):
        # Permission
        res = self.client.post(self.url_list, {'content': ':)'})
        self.assertEqual(res.status_code, 201)

    def test_update_put(self):
        res = self.client.put(self.url_detail, {'content': ':)'})
        self.assertEqual(res.status_code, 403)
        # Owner
        owner = self.obj.user
        self.client.force_login(owner)
        res = self.client.put(self.url_detail, {'content': ':)'})
        self.assertEqual(res.status_code, 200)

    def test_update_patch(self):
        owner = self.obj.user
        self.client.force_login(owner)
        res = self.client.patch(self.url_detail, {'content': ':)'})
        self.assertEqual(res.status_code, 200)

    def test_delete(self):
        res = self.client.delete(self.url_detail)
        self.assertEqual(res.status_code, 403)
        # Owner
        owner = self.obj.user
        self.client.force_login(owner)
        res = self.client.delete(self.url_detail)
        self.assertEqual(res.status_code, 204)

    def test_mark_to_delete(self):
        # Tested with segment comments
        pass

    def test_max_length(self):
        res = self.client.post(self.url_list, {'content': 2001 * 'a'})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.json()['content'],
            ['Ensure this field has no more than 2000 characters.'],
        )

    def test_read_only_fields(self):
        owner = self.obj.user
        self.client.force_login(owner)
        res = self.client.patch(self.url_detail, {'to_delete': 400})
        self.assertEqual(res.status_code, 200)

    @override_settings(DEFAULT_FROM_EMAIL='from@example.com')
    def test_send_email(self):
        user = UserFactory()
        group = Group.objects.create(name='Support')
        user.groups.add(group)
        self.assertEqual(len(mail.outbox), 0)
        res = self.client.post(self.url_list, {'content': ':)'})
        self.assertEqual(res.status_code, 201)
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.subject, 'New comment on Langify')
        self.assertEqual(email.from_email, 'from@example.com')
        self.assertEqual(email.to, [user.email])
        self.assertEqual(email.body, ':)\n\nhttps://www.ellen4all.org/roadmap/')


class BaseMailingClientTests(SimpleTestCase):
    def test_check_response_passes(self):
        response = MagicMock()
        response.status_code = 204
        MailjetClient().check_response(response, 204)

    def test_check_response_minimal(self):
        response = MagicMock()
        response.status_code = 204
        response.json.return_value = 'response text'
        msg = 'Something went wrong. Please retry later.'
        with self.assertLogs('misc.apis', 'ERROR') as cm:
            with self.assertRaisesMessage(ValidationError, msg):
                MailjetClient().check_response(response)
        self.assertEqual(len(cm.records), 1)
        record = cm.records[0]
        self.assertEqual(
            record.message, 'Mailjet API didn\'t response with 200.'
        )
        self.assertEqual(record.status_code, 204)
        self.assertEqual(record.body, 'response text')
        self.assertEqual(record.data, None)

    @tag('online')
    def test_check_response_all_attributes(self):
        response = MagicMock()
        response.status_code = 500
        response.json.return_value = 'response text'
        client = Newsletter2GoClient()
        msg = 'Something went wrong. Please retry later.'
        with self.assertLogs('misc.apis', 'ERROR') as cm:
            with self.assertRaisesMessage(ValidationError, msg):
                client.check_response(response, 201, 'test data')
        self.assertEqual(len(cm.records), 1)
        record = cm.records[0]
        self.assertEqual(
            record.message, 'Newsletter2Go API didn\'t response with 201.'
        )
        self.assertEqual(record.status_code, 500)
        self.assertEqual(record.body, 'response text')
        self.assertEqual(record.data, 'test data')


@patch.multiple('misc.apis', FROM_EMAIL='name@example.com', FROM_NAME='Name')
@override_settings(DEFAULT_TO_EMAILS=('admin@example.com',))
class MailjetClientTests(SimpleTestCase):
    data = [
        {
            'From': {'Email': 'name@example.com', 'Name': 'Name'},
            'To': [{'Email': 't@example.com'}],
            'TemplateID': 123,
            'TemplateLanguage': True,
            'Subject': 'Hi',
            'Variables': {
                1: 2,
                'link_doesnt_work_note': (
                    'Link doesn\'t work? '
                    'Copy the following link to your browser bar:'
                ),
                'germany': 'Germany',
                'legal_notice': 'Legal notice',
                'privacy_policy': 'Privacy policy',
            },
            'TemplateErrorReporting': {
                'Email': 'admin@example.com',
                'Name': 'admin@example.com',
            },
        }
    ]

    @patch('misc.apis.CoreMailjetClient')
    def test_create_email(self, *args):
        client = MailjetClient()
        client.create_email(123, 't@example.com', 'Hi', {1: 2})
        self.assertEqual(client.messages, self.data)

    @patch('misc.apis.CoreMailjetClient')
    @override_settings(DEBUG=False, TEST=False)
    def test_send(self, *args):
        client = MailjetClient()
        client.client.send.create.return_value = 'response'
        client.check_response = MagicMock()
        client.messages = self.data
        response = client.send(sandbox=True)
        self.assertEqual(response, 'response')
        self.assertEqual(client.messages, [])
        data = {'Messages': self.data, 'SandboxMode': True}
        client.client.send.create.assert_called_once_with(data=data)
        client.check_response.assert_called_once_with('response', data=data)

    @patch.multiple(
        'misc.apis', CoreMailjetClient=MagicMock(), sleep=MagicMock()
    )
    @override_settings(DEBUG=False, TEST=False)
    def test_send_error(self):
        client = MailjetClient()
        client.check_response = MagicMock(side_effect=ValidationError())
        with self.assertRaises(ValidationError):
            client.send(sandbox=True)
        self.assertEqual(len(client.check_response.mock_calls), 5)
        client.client.send.create.side_effect = RequestsConnectionError()
        with self.assertRaises(RequestsConnectionError):
            client.send(sandbox=True)
        self.assertEqual(len(client.client.send.create.mock_calls), 10)

    @patch('misc.apis.CoreMailjetClient')
    @override_settings(DEBUG=False, TEST=False)
    def test_send_transactional_email(self, *args):
        client = MailjetClient()
        client.client.send.create.return_value = 'response'
        client.check_response = MagicMock()
        response = client.send_transactional_email(
            123, 't@example.com', 'Hi', {1: 2}
        )
        self.assertEqual(response, 'response')
        data = {'Messages': self.data}
        client.client.send.create.assert_called_once_with(data=data)
        client.check_response.assert_called_once_with('response', data=data)

    @patch('misc.apis.CoreMailjetClient')
    @override_settings(DEBUG=True)
    def test_send_transactional_email_development_mode(self, *args):
        client = MailjetClient()
        client.send_transactional_email(123, 't@example.com', 'Hi', {1: 2})
        client.client.send.create.assert_not_called()


@patch('misc.apis.OAuth2Session', MagicMock())
class Newsletter2GoClientTests(SimpleTestCase):
    @override_settings(
        NL2GO_AUTH_KEY='test:key',
        EMAIL_BACKEND=Newsletter2GoClient.production_email_backend,
    )
    def test_send_transactional_email(self):
        client = Newsletter2GoClient()
        client.session.post.return_value = 'response'
        client.check_response = MagicMock()
        client.send_transactional_email('myid', 't@e.c', {1: 2, 3: 4})
        client.session.post.assert_called_once_with(
            'https://api.newsletter2go.com/newsletters/myid/send',
            json={'contexts': [{'recipient': {'email': 't@e.c', 1: 2, 3: 4}}]},
        )
        client.check_response.assert_has_calls([call('response')])


class LanguageNewsletterTests:
    urls = {'post': reverse('newsletter_languages')}

    def test_email_required(self):
        res = self.client.post(self.urls['post'])
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json(), {'email': ['This field is required.']})


@tag('online')
class OnlineLanguageNewsletterTests(LanguageNewsletterTests, PostOnlyAPITests):
    def test_subscribe_error_nl2go_api(self):
        res = self.client.post(
            self.urls['post'], data={'email': 'test@example.com'}
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.json(), ['Something went wrong. Please retry later.']
        )


@tag('offline')
@patch('misc.apis.in_test_mode', lambda: True)
class OfflineLanguageNewsletterTests(LanguageNewsletterTests, PostOnlyAPITests):
    def test_subscribe_with_email_only(self):
        res = self.client.post(
            self.urls['post'], data={'email': 'test@mylangify.com'}
        )
        self.assertEqual(res.status_code, 201)

    def test_subscribe_with_all_fields(self):
        data = {'name': 'Me', 'email': 'test@mylangify.com', 'language': 'en'}
        res = self.client.post(self.urls['post'], data=data)
        self.assertEqual(res.status_code, 201)


class E2ETestsTests(APITests):
    url = '/api/test/'

    def tearDown(self):
        set_test_mode(False)

    @skipIf(not settings.DEBUG, 'Endpoint available when DEBUG == True only.')
    def test_retrieve(self):
        self.assertFalse(in_test_mode())
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {'test': False})

    @skipIf(not settings.DEBUG, 'Endpoint available when DEBUG == True only.')
    def test_change(self):
        self.assertFalse(in_test_mode())
        res = self.client.post(self.url, data={'test': True})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(in_test_mode())
        res = self.client.get(self.url)
        self.assertEqual(res.json(), {'test': True})

    @skipIf(not settings.DEBUG, 'Endpoint available when DEBUG == True only.')
    def test_flush_test_database(self):
        factories.PageFactory()
        set_test_mode(True)
        factories.PageFactory()
        res = self.client.post(self.url, data={'test': False})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(models.Page.objects.using('default').count(), 1)
        self.assertFalse(models.Page.objects.using('e2e_tests').exists())

    @skipIf(settings.DEBUG, 'Endpoint available when DEBUG == True.')
    def test_endpoint_not_available_when_debug_false(self):
        res = self.client.post(self.url, data={'test': True})
        self.assertEqual(res.status_code, 404)
        self.assertFalse(in_test_mode())

    @skipIf(not settings.DEBUG, 'Endpoint available when DEBUG == True only.')
    def test_get_confirmation_key(self):
        email = EmailAddressFactory()
        res = self.client.post(
            self.url + 'email-confirmation-key/', data={'email': email.email}
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn(':', res.json()['key'])


class HealthTests(APITests):
    def test(self):
        res = self.client.get('/api/health/?format=json')
        received = res.json()
        self.assertIn(
            received.pop('CeleryHealthCheckCelery'),
            ('working', 'unavailable: Unknown error'),
        )
        # I didn't activate disk and memory checks because they check the Docker
        # container which makes little sense. Using the host's ones is also not
        # trivial because the implementation depends on the OS.
        # For Linux you can do:
        #
        # import psutil
        # psutil.PROCFS_PATH = '/proc-host'
        #
        # After adding following to the volumes in docker-compose.yml:
        #
        # - /proc:/proc-host:ro
        #
        # See https://github.com/giampaolo/psutil/issues/
        # 1011#issuecomment-293890934
        #
        expected = {
            'CacheBackend': 'working',
            'DatabaseBackend': 'working',
            'DefaultFileStorageHealthCheck': 'working',
            # 'DiskUsage': 'working',
            # 'MemoryUsage': 'working',
        }
        self.assertEqual(received, expected)
