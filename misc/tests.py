import re
from unittest import skipIf
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.contrib.auth.models import Permission
from django.test import SimpleTestCase, TestCase, tag  # noqa: F401
from django.urls import reverse
from django.utils import timezone
from langify.routers import in_test_mode, set_test_mode
from panta.factories import TranslatedSegmentFactory
from path.factories import UserFactory

from . import factories, tasks
from .models import DeveloperComment, Page
from .utils import add_task_for_comments_deletion


class LangifyTests(TestCase):
    @skipIf(settings.VERSION == 'NaN', 'Version not available.')
    def test_version(self):
        import langify

        version = langify.__version__.split('.')
        self.assertGreaterEqual(len(version), 2)
        self.assertTrue(version[0].isdigit())
        self.assertTrue(version[1].isdigit())

    def test_api_docs(self):
        self.client.force_login(UserFactory(is_staff=True))
        res = self.client.get(reverse('schema_redoc'))
        self.assertEqual(res.status_code, 200)


class PageModelTests(TestCase):
    def test_obfuscate_email(self):
        page = Page(slug='test')
        page.styles = []
        # Short address
        self.assertRegex(
            page.obfuscate_email(re.search('.+', 'x@a.b')),
            '<span id="[a-zA-Z]+">%3C!-- &lt;!--</span>'
            '<a href="/page/test/0/">'
            '<span id="[a-zA-Z]+"> Click to send a message with your '
            'communication programm. </span>'
            '<span id="[a-zA-Z]+">x</span>'
            '<span id="[a-zA-Z]+">delete-[0-9]+-this-</span>'
            '<span id="[a-zA-Z]+">a<!--- - ->.shop <!-- --></span>'
            '<!-- --%gt; : <!-->.<!-- ; ---->b'
            '</a>'
            '<span id="[a-zA-Z]+">--%3E</span>',
        )
        self.assertEqual(len(page.styles), 1)
        self.assertRegex(
            page.styles[0],
            'span#[a-zA-Z]+ {display: none;}'
            'span#[a-zA-Z]+::before {content: "@";}',
        )
        # Many characters
        self.assertRegex(
            page.obfuscate_email(
                re.search('.+', 'aB3._%+-@aB-2468.company.example.com')
            ),
            r'<span id="[a-zA-Z]+">%3C!-- &lt;!--</span>'
            r'<a href="/page/test/1/">'
            r'<span id="[a-zA-Z]+"> Click to send a message with your '
            r'communication programm. </span>'
            r'<span id="[a-zA-Z]+">aB3._%\+-</span>'
            r'<span id="[a-zA-Z]+">delete-[0-9]+-this-</span>'
            r'<span id="[a-zA-Z]+">aB-2468.company.example'
            r'<!--- - ->.shop <!-- --></span>'
            r'<!-- --%gt; : <!-->.<!-- ; ---->com'
            r'</a>'
            r'<span id="[a-zA-Z]+">--%3E</span>',
        )
        self.assertEqual(len(page.styles), 2)
        self.assertRegex(
            page.styles[1],
            'span#[a-zA-Z]+ {display: none;}'
            'span#[a-zA-Z]+::before {content: "@";}',
        )

    def test_obfuscate_phone(self):
        page = Page()
        page.styles = []
        # Plus only
        self.assertRegex(
            page.obfuscate_phone(re.search('.+', '+ ')),
            r'<span id="[a-zA-Z]+">\+</span>',
        )
        self.assertEqual(len(page.styles), 1)
        self.assertRegex(
            page.styles[0], r'span#[a-zA-Z]+ {letter-spacing: 0\.3em;}'
        )
        # Phone number
        self.assertRegex(
            page.obfuscate_phone(re.search('.+', '+49 (0) 1234/56789-0')),
            r'\+4<!--- - ->0<!-- --><span id="[a-zA-Z]+">9</span>'
            r'\(0<!--- - ->0<!-- --><span id="[a-zA-Z]+">\)</span>'
            r'1234/56789-<!--- - ->0<!-- --><span id="[a-zA-Z]+">0</span>',
        )
        self.assertEqual(len(page.styles), 2)
        self.assertRegex(
            page.styles[1], r'span#[a-zA-Z]+ {letter-spacing: 0\.3em;}'
        )

    def test_render_email_only(self):
        page = Page(slug='test1', content='test.1-23@sub-95.example.com')
        page.save()
        self.assertRegex(
            page.rendered,
            '<style type="text/css">'
            'span#[a-zA-Z]+ {display: none;}'
            'span#[a-zA-Z]+::before {content: "@";}'
            '</style>'
            '<span id="[a-zA-Z]+">%3C!-- &lt;!--</span>'
            '<a href="/page/test1/0/">'
            '<span id="[a-zA-Z]+"> Click to send a message with your '
            'communication programm. </span>'
            '<span id="[a-zA-Z]+">test.1-23</span>'
            '<span id="[a-zA-Z]+">delete-[0-9]+-this-</span>'
            '<span id="[a-zA-Z]+">sub-95.example<!--- - ->.shop <!-- -->'
            '</span>'
            '<!-- --%gt; : <!-->.<!-- ; ---->com'
            '</a>'
            '<span id="[a-zA-Z]+">--%3E</span>',
        )

    def test_render_email_and_phone(self):
        page = Page(slug='test2', content='test@example.com +12 (0) 123')
        page.save()
        self.assertRegex(
            page.rendered,
            r'<style type="text/css">'
            r'span#[a-zA-Z]+ {letter-spacing: 0\.3em;}'
            r'span#[a-zA-Z]+ {display: none;}'
            r'span#[a-zA-Z]+::before {content: "@";}'
            r'</style>'
            r'<span id="[a-zA-Z]+">%3C!-- &lt;!--</span>'
            r'<a href="/page/test2/0/">'
            r'<span id="[a-zA-Z]+"> Click to send a message with your '
            r'communication programm. </span>'
            r'<span id="[a-zA-Z]+">test</span>'
            r'<span id="[a-zA-Z]+">delete-[0-9]+-this-</span>'
            r'<span id="[a-zA-Z]+">example<!--- - ->.shop <!-- --></span>'
            r'<!-- --%gt; : <!-->.<!-- ; ---->com'
            r'</a>'
            r'<span id="[a-zA-Z]+">--%3E</span> '
            r'\+1<!--- - ->0<!-- --><span id="[a-zA-Z]+">2</span>'
            r'\(0<!--- - ->0<!-- --><span id="[a-zA-Z]+">\)</span>'
            r'12<!--- - ->0<!-- --><span id="[a-zA-Z]+">3</span>',
        )

    def test_render_email_phone_and_text(self):
        page = Page(
            slug='test3',
            content=r'Title\n Text and name test@example.com\n+12 (0) 123 ...',
        )
        page.save()
        self.assertRegex(
            page.rendered,
            r'<style type="text/css">'
            r'span#[a-zA-Z]+ {letter-spacing: 0\.3em;}'
            r'span#[a-zA-Z]+ {display: none;}'
            r'span#[a-zA-Z]+::before {content: "@";}'
            r'</style>'
            r'Title\\n Text and name '
            r'<span id="[a-zA-Z]+">%3C!-- &lt;!--</span>'
            r'<a href="/page/test3/0/">'
            r'<span id="[a-zA-Z]+"> Click to send a message with your '
            r'communication programm. </span>'
            r'<span id="[a-zA-Z]+">test</span>'
            r'<span id="[a-zA-Z]+">delete-[0-9]+-this-</span>'
            r'<span id="[a-zA-Z]+">example<!--- - ->.shop <!-- --></span>'
            r'<!-- --%gt; : <!-->.<!-- ; ---->com'
            r'</a>'
            r'<span id="[a-zA-Z]+">--%3E</span>\\n'
            r'\+1<!--- - ->0<!-- --><span id="[a-zA-Z]+">2</span>'
            r'\(0<!--- - ->0<!-- --><span id="[a-zA-Z]+">\)</span>'
            r'12<!--- - ->0<!-- --><span id="[a-zA-Z]+">3</span>...',
        )

    def test_protected_array(self):
        page = Page(slug='test', content='you@t.example.com')
        page.save_without_historical_record()
        self.assertEqual(page.protected, ['you%40t.example.com'])
        page.content += 'x y z'
        page.save_without_historical_record()
        self.assertEqual(page.protected, ['you%40t.example.comx'])
        page.content += ' a@b.cd'
        page.save_without_historical_record()
        self.assertEqual(page.protected, ['you%40t.example.comx', 'a%40b.cd'])
        page.content = '@Test'
        page.save_without_historical_record()
        self.assertEqual(page.protected, [])


class ViewTests(TestCase):
    def test_home(self):
        res = self.client.get('/')
        self.assertRedirects(
            res, 'http://localhost:3000/', fetch_redirect_response=False
        )
        res = self.client.get('/anything/?xy=z')
        self.assertRedirects(
            res,
            'http://localhost:3000/anything/?xy=z',
            fetch_redirect_response=False,
        )

    def test_statistics(self):
        url = reverse('statistics')
        user = UserFactory()
        TranslatedSegmentFactory()
        self.client.force_login(user)
        res = self.client.get(url)
        self.assertEqual(res.status_code, 403)
        perm = Permission.objects.get(codename='view_page')
        user.user_permissions.add(perm)
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)


class TaskTests(SimpleTestCase):
    @patch('misc.tasks.timezone.now', lambda: 'time')
    @patch('misc.tasks.DeveloperComment', spec=DeveloperComment)
    def test_delete_comments(self, model):
        filter_mock = MagicMock()
        filter_mock.delete.return_value = (None, 0)
        model.objects.filter.return_value = filter_mock
        tasks.delete_comments('DeveloperComment')
        model.objects.filter.assert_called_once_with(to_delete__lte='time')
        filter_mock.delete.assert_called()


@patch('misc.utils.cache')
@patch('misc.utils.delete_comments')
class AddTaskForCommentsDeletionTests(SimpleTestCase):
    def setUp(self):
        self.instance = MagicMock(DeveloperComment(to_delete=timezone.now()))
        self.instance._meta.model = DeveloperComment
        self.kwargs = {'instance': self.instance, 'raw': False}

    def test_cache(self, task, cache):
        cache.get.return_value = None
        add_task_for_comments_deletion(self.kwargs)
        key = 'DeveloperComment_deletion_scheduled'
        cache.get.assert_called_once_with(key)
        cache.set.assert_called_once_with(key, True, timeout=60)
        task.apply_async.assert_called_once()

    def test_key_set(self, task, cache):
        cache.get.return_value = True
        add_task_for_comments_deletion(self.kwargs)
        cache.set.assert_not_called()
        task.apply_async.assert_not_called()

    def test_to_delete_not_set(self, task, cache):
        cache.get.return_value = None
        self.instance.to_delete = None
        add_task_for_comments_deletion(self.kwargs)
        cache.set.assert_not_called()
        task.apply_async.assert_not_called()

    def test_task_call(self, task, cache):
        cache.get.return_value = None
        add_task_for_comments_deletion(self.kwargs)
        task.apply_async.assert_called_once_with(
            args=('DeveloperComment',), countdown=10 * 60 + 60
        )


class SignalTests(TestCase):
    @patch('misc.signals.add_task_for_comments_deletion')
    def test_schedule_developer_comment_deletion(self, mocked):
        factories.DeveloperCommentFactory()
        mocked.assert_called_once()


class RouterTests(TestCase):
    def test_e2e_getter_and_setter(self):
        self.assertFalse(in_test_mode())
        set_test_mode(True)
        self.assertTrue(in_test_mode())
        set_test_mode(False)
        self.assertFalse(in_test_mode())

    @skipIf('e2e_tests' not in settings.DATABASES, 'Requires E2E tests DB.')
    def test_e2e_test_database_is_used(self):
        self.assertFalse(Page.objects.using('default').exists())
        self.assertFalse(Page.objects.using('e2e_tests').exists())
        set_test_mode(True)
        factories.PageFactory()
        self.assertFalse(Page.objects.using('default').exists())
        self.assertTrue(Page.objects.using('e2e_tests').count(), 1)
        set_test_mode(False)
        factories.PageFactory()
        self.assertTrue(Page.objects.using('default').count(), 1)
        self.assertTrue(Page.objects.using('e2e_tests').count(), 1)
        # Tidy up
        Page.objects.using('e2e_tests').delete()
