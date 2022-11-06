from base.tests import PostOnlyAPITests
from django.test import tag  # noqa: F401
from django.urls import reverse


class AuthenticationTests(PostOnlyAPITests):
    def test_login(self):
        self.user.emailaddress_set.update(verified=True)
        with self.assertLogs() as log:
            self.client.post(
                reverse('rest_login'), {'username': 'david', 'password': 'pw'}
            )
        self.assertRegex(
            log.output[0],
            r'INFO:path.signals:[0-9.:\- ]+\+00:00 priority=1, '
            'system=mainserver, module=path.models, '
            'source=http://testserver/api/auth/login/, service=HTTP/1.1, '
            'method=POST, user={pk}, sessionhash=[0-9a-f]+, '
            'ipaddress=127.0.0.1, '
            'useragent=, action=login, object=user account, status=success, '
            'reason=$'.format(pk=self.user.pk),
        )

    def test_login_failed_with_view(self):
        with self.assertLogs() as log:
            self.client.post(
                reverse('rest_login'), {'username': 'Ann', 'password': 'wrong'}
            )
        self.assertRegex(
            log.output[0],
            r'WARNING:path.signals:[0-9.:\- ]+\+00:00 priority=3, '
            'system=mainserver, module=django.contrib.auth, '
            'source=http://testserver/api/auth/login/, service=HTTP/1.1, '
            'method=POST, user=Ann, sessionhash=, ipaddress=127.0.0.1, '
            'useragent=, action=login, object=user account, status=fail, '
            'reason=user not authenticated in database check$',
        )

    def test_login_failed_with_client(self):
        with self.assertLogs() as log:
            self.client.login(username='Ann', password='wrong')
        self.assertRegex(
            log.output[0],
            r'WARNING:path.signals:[0-9.:\- ]+\+00:00 priority=3, '
            'system=mainserver, module=django.contrib.auth, source=, '
            'service=, '
            'method=, user=Ann, sessionhash=, ipaddress=, '
            'useragent=, action=login, object=user account, status=fail, '
            'reason=user not authenticated in database check$',
        )

    def test_logout(self):
        self.client.force_login(self.user)
        with self.assertLogs() as log:
            self.client.post(reverse('rest_logout'))
        self.assertRegex(
            log.output[0],
            r'INFO:path.signals:[0-9.:\- ]+\+00:00 priority=1, '
            'system=mainserver, module=path.models, '
            'source=http://testserver/api/auth/logout/, service=HTTP/1.1, '
            'method=POST, user={pk}, sessionhash=[0-9a-f]+, '
            'ipaddress=127.0.0.1, useragent=, action=logout, '
            'object=user account, status=success, '
            'reason=$'.format(pk=self.user.pk),
        )

    def test_logout_not_authenticated(self):
        with self.assertLogs() as log:
            self.client.post(reverse('rest_logout'))
        self.assertRegex(
            log.output[0],
            r'INFO:path.signals:[0-9.:\- ]+\+00:00 priority=1, '
            'system=mainserver, module=builtins, '
            'source=http://testserver/api/auth/logout/, service=HTTP/1.1, '
            'method=POST, user=, sessionhash=, ipaddress=127.0.0.1, '
            'useragent=, action=logout, object=user account, status=useless, '
            'reason=user was not logged in$',
        )
