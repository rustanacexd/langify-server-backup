from unittest.mock import patch

from allauth.account.models import EmailAddress
from allauth.account.utils import user_pk_to_url_str
from django.core import mail
from django.core.cache import cache
from django.test import override_settings, tag  # noqa: F401
from django.urls import reverse

from base.tests import PostOnlyAPITests
from misc.apis import MailjetClient
from path import factories, models


class MailjetTests(PostOnlyAPITests):
    outbox = MailjetClient.test_outbox

    def setUp(self):
        self.outbox.clear()


class SignupTests(MailjetTests):
    urls = {
        'signup': reverse('rest_register'),
        'confirm_email': reverse('rest_verify_email'),
    }
    data = {
        'username': 'user',
        'email': 'n@example.com',
        'password1': 'D-dklaskdjhjkfkkksdlj345498459837',
        'password2': 'D-dklaskdjhjkfkkksdlj345498459837',
        'terms': True,
    }

    # def test_signup(self):
    #     self.assertEqual(EmailAddress.history.count(), 1)
    #     res = self.client.post(self.urls['signup'], self.data)
    #     self.assertEqual(res.status_code, 201)
    #     self.assertEqual(res.json(), {'detail': 'Verification e-mail sent.'})
    #     self.assertEqual(len(mail.outbox), 0)
    #     self.assertEqual(len(self.outbox), 1)
    #     msg = self.outbox[0][-1]['data']['Messages'][0]
    #     self.assertEqual(msg['To'][0]['Email'], 'n@example.com')
    #     self.assertEqual(msg['TemplateID'], 533481)
    #     self.assertIn('https://testserver/', msg['Variables']['link'])
    #     self.assertEqual(EmailAddress.history.count(), 2)
    #     self.assertIn('account_user', self.client.session)
    #     user = models.User.objects.get(username='user')
    #     self.assertEqual(user.language, '')
    #     return
    #     # Old behavior
    #     email_text = mail.outbox[0].body
    #     self.assertIn('Legal notice: http', email_text)
    #     self.assertIn('Privacy: http', email_text)

    # def test_signup_honors_password_validators(self):
    #     data = self.data.copy()
    #     data['password1'] = data['email']
    #     data['password2'] = data['email']
    #     res = self.client.post(self.urls['signup'], data)
    #     self.assertEqual(res.status_code, 400)
    #     self.assertEqual(
    #         res.json(), ['The password is too similar to the e-mail address.']
    #     )

    #     data['password1'] = 1234
    #     data['password2'] = 1234
    #     res = self.client.post(self.urls['signup'], data)
    #     self.assertEqual(res.status_code, 400)
    #     self.assertEqual(
    #         res.json(),
    #         {
    #             'password1': [
    #                 'This password is too short. It must contain at least 8 '
    #                 'characters.',
    #                 'This password is too common.',
    #                 'This password is entirely numeric.',
    #             ]
    #         },
    #     )

    # def test_terms_required(self):
    #     data = self.data.copy()
    #     data.pop('terms')
    #     res = self.client.post(self.urls['signup'], data)
    #     self.assertEqual(res.status_code, 400)
    #     self.assertEqual(res.json(), {'terms': ['This field is required.']})

    @patch('path.api.views.AuthRateThrottle.get_rate')
    def test_throttling(self, mock):
        cache.clear()
        mock.return_value = '1/day'
        res = self.client.post(self.urls['signup'], {})
        self.assertEqual(res.status_code, 400)
        res = self.client.post(self.urls['signup'], {})
        self.assertEqual(res.status_code, 429)

    def test_confirm_email(self):
        email = EmailAddress.objects.create(
            email='1@example.com', user=factories.UserFactory(username='Debby')
        )
        confirmation = email.send_confirmation()
        session = self.client.session
        session['account_user'] = user_pk_to_url_str(email.user)
        session.save()
        res = self.client.post(
            self.urls['confirm_email'], {'key': confirmation.key}
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['username'], 'Debby')
        # Access endpoint with login required
        res = self.client.get(reverse('emailaddress-list'))
        self.assertEqual(res.status_code, 200)
        # Second request with same key and logged in
        res = self.client.post(
            self.urls['confirm_email'], {'key': confirmation.key}
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['username'], 'Debby')
        self.client.logout()
        # Third request with same key and logged out
        res = self.client.post(
            self.urls['confirm_email'], {'key': confirmation.key}
        )
        self.assertEqual(res.status_code, 404)

    def test_confirm_email_without_auto_login(self):
        email = EmailAddress.objects.create(
            email='1@example.com', user=factories.UserFactory(username='Debby')
        )
        confirmation = email.send_confirmation()
        res = self.client.post(
            self.urls['confirm_email'], {'key': confirmation.key}
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            res.json()['detail'], 'E-mail address confirmed successfully.'
        )

    def test_confirm_email_404(self):
        res = self.client.post(self.urls['confirm_email'], {'key': '123'})
        self.assertEqual(res.status_code, 404)
        self.assertEqual(res.json()['detail'], 'Not found.')

    @override_settings(ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS=0)
    def test_confirm_email_expired(self):
        email = EmailAddress.objects.create(
            email='1@example.com', user=factories.UserFactory()
        )
        confirmation = email.send_confirmation()
        res = self.client.post(
            self.urls['confirm_email'], {'key': confirmation.key}
        )
        self.assertEqual(res.status_code, 404)


class LoginTests(MailjetTests):
    urls = {'login': reverse('rest_login')}

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user.reputations.exclude(language='de').delete()
        cls.expected_permissions = cls.permissions.copy()
        cls.expected_permissions['de'] = {
            'addComment': True,
            'addTranslation': True,
            'approveTranslation': False,
            'changeComment': True,
            'changeTranslation': True,
            'deleteComment': True,
            'deleteTranslation': True,
            'restoreTranslation': True,
            'disapproveTranslation': False,
            'flagComment': True,
            'flagTranslation': True,
            'flagUser': True,
            'hideComment': False,
            'reviewTranslation': False,
            'trustee': False,
        }
        cls.url_profile = reverse(
            'community_user_profile', args=(cls.user.username,)
        )

    def test_login_with_username(self):
        self.user.emailaddress_set.update(verified=True)
        res = self.client.post(
            self.urls['login'], {'username': 'david', 'password': 'pw'}
        )
        self.assertEqual(res.status_code, 200)
        expected = {
            'username': 'david',
            'id': self.user.public_id,
            'firstName': '',
            'lastName': '',
            'contributions': {'edits': 0},
            'thumbnail': self.user.get_avatar(),
            'url': self.url_profile,
            'language': None,
            'permissions': self.expected_permissions,
        }
        self.assertEqual(res.json(), expected)

    def test_login_with_email(self):
        self.user.emailaddress_set.update(verified=True)
        res = self.client.post(
            self.urls['login'], {'username': self.user.email, 'password': 'pw'}
        )
        self.assertEqual(res.status_code, 200)
        expected = {
            'username': 'david',
            'id': self.user.public_id,
            'firstName': '',
            'lastName': '',
            'contributions': {'edits': 0},
            'thumbnail': self.user.get_avatar(),
            'url': self.url_profile,
            'language': None,
            'permissions': self.expected_permissions,
        }
        self.assertEqual(res.json(), expected)

    def test_login_with_email_failure(self):
        self.user.emailaddress_set.update(verified=True)
        res = self.client.post(
            self.urls['login'],
            {'username': self.user.email, 'password': 'wrong'},
        )
        self.assertEqual(res.status_code, 400)

    # TODO (#119)
    def test_username(self):
        user = factories.UserFactory(username='danieL')
        user.reputations.exclude(language='de').delete()
        EmailAddress.objects.create(user=user, email=user.email, verified=True)
        res = self.client.post(
            self.urls['login'], {'username': 'daniel', 'password': 'pw'}
        )
        self.assertEqual(res.status_code, 200)
        expected = {
            'username': 'danieL',
            'id': user.public_id,
            'firstName': '',
            'lastName': '',
            'contributions': {'edits': 0},
            'thumbnail': user.get_avatar(),
            'url': reverse('community_user_profile', args=(user.username,)),
            'language': None,
            'permissions': self.expected_permissions,
        }
        self.assertEqual(res.json(), expected)

    def test_login_inactive_user(self):
        self.user.is_active = False
        self.user.save_without_historical_record()

        res = self.client.post(
            self.urls['login'], {'username': 'david', 'password': 'pw'}
        )
        self.assertEqual(res.status_code, 400)
        expected = {
            'nonFieldErrors': ['Unable to log in with provided credentials.']
        }
        self.assertEqual(res.json(), expected)
        self.user.is_active = True

    def test_login_creates_no_historical_record(self):
        self.assertEqual(self.user.history.count(), 2)
        self.client.post(
            self.urls['login'], {'username': 'david', 'password': 'pw'}
        )
        self.assertEqual(self.user.history.count(), 2)

    def test_login_creates_email_address(self):
        user = factories.UserFactory()
        self.assertFalse(user.emailaddress_set.exists())
        res = self.client.post(
            self.urls['login'], {'username': user.username, 'password': 'pw'}
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(user.emailaddress_set.count(), 1)
        msg = (
            'Your e-mail address is not verified yet. '
            'We just sent you an e-mail with a confirmation link. '
            'Please check your mailbox.'
        )
        self.assertEqual(res.json(), {'nonFieldErrors': [msg]})

    def test_login_sends_confirmation_email(self):
        res = self.client.post(
            self.urls['login'],
            {'username': self.user.username, 'password': 'pw'},
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(len(self.outbox), 1)
        msg = self.outbox[0][-1]['data']['Messages'][0]
        self.assertEqual(msg['To'][0]['Email'], self.user.email)
        self.assertEqual(msg['Subject'], 'Confirm your e-mail address')


class LogoutTests(PostOnlyAPITests):
    urls = {'logout': reverse('rest_logout')}

    def test_logout(self):
        res = self.client.post(self.urls['logout'])
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {'detail': 'Successfully logged out.'})


class PasswordTests(MailjetTests):
    urls = {
        'password_change': reverse('rest_password_change'),
        'password_reset': reverse('rest_password_reset'),
        'password_reset_confirm': reverse('rest_password_reset_confirm'),
    }

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.data = {
            'old_password': 'pw',
            'new_password1': '§lkfj984rejfdkdskjlKL',
            'new_password2': '§lkfj984rejfdkdskjlKL',
        }

    def test_change(self):
        self.client.force_login(self.user)
        res = self.client.post(self.urls['password_change'], self.data)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {'detail': 'New password has been saved.'})

    def test_change_honors_password_validators(self):
        self.client.force_login(self.user)
        data = {
            'old_password': 'pw',
            'new_password1': 'david',
            'new_password2': 'david',
        }
        res = self.client.post(self.urls['password_change'], data)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.json(),
            {
                'newPassword2': [
                    'The password is too similar to the username.',
                    'This password is too short. It must contain at least 8 '
                    'characters.',
                    'This password is too common.',
                ]
            },
        )

    def test_set(self):
        pass  # TODO

    def test_reset(self):
        res = self.client.post(
            self.urls['password_reset'], {'email': self.user.email}
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            res.json(), {'detail': 'Password reset e-mail has been sent.'}
        )
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(len(self.outbox), 1)
        msg = self.outbox[0][-1]['data']['Messages'][0]
        parts = msg['Variables']['link'].split('/')
        self.assertEqual(len(parts), 8)
        data = self.data.copy()
        data['uid'] = parts[5]
        data['token'] = parts[6]
        res = self.client.post(self.urls['password_reset_confirm'], data)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            res.json(),
            {'detail': 'Password has been reset with the new password.'},
        )
        return
        email_text = None
        # Old behavior
        self.assertIn('Legal notice: http', email_text)
        self.assertIn('Privacy: http', email_text)
        text = (
            """
            Hello David,

            You’re receiving this email because someone requested
            a password reset for your user account at example.com.

            In case you asked for it please follow the link below
            to enter a new password:
            http://example.com/auth/password-reset-confirmation
            """,
            """
            Your username, in case you’ve forgotten: david

            Thanks for using our site!

            Your example.com team


            ---
            Legal notice: http://example.com/about
            Privacy: http://example.com/privacy
            """,
        )
        self.assertHTMLEqual(parts[0], text[0])
        self.assertHTMLEqual(parts[3], text[1])

    def test_reset_as_inactive_user(self):
        self.user.is_active = False
        self.user.save_without_historical_record()
        res = self.client.post(
            self.urls['password_reset'], {'email': self.user.email}
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.json(),
            {
                'email': '"{}" was not found in our system.'.format(
                    self.user.email
                )
            },
        )
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(len(self.outbox), 0)
        self.user.is_active = True

    def test_reset_honors_password_validators(self):
        res = self.client.post(
            self.urls['password_reset'], {'email': self.user.email}
        )
        self.assertEqual(res.status_code, 200)
        msg = self.outbox[0][-1]['data']['Messages'][0]
        parts = msg['Variables']['link'].split('/')
        data = {
            'old_password': 'pw',
            'new_password1': 'david',
            'new_password2': 'david',
            'uid': parts[5],
            'token': parts[6],
        }
        res = self.client.post(self.urls['password_reset_confirm'], data)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.json(),
            {
                'newPassword2': [
                    'The password is too similar to the username.',
                    'This password is too short. It must contain at least 8 '
                    'characters.',
                    'This password is too common.',
                ]
            },
        )


class ResendConfirmationTests(MailjetTests):
    urls = {'confirm': reverse('resend_confirmation')}

    not_found = '"{}" is confirmed already or was not found in our system.'

    @classmethod
    def setUpTestData(cls):
        cls.user = factories.UserFactory()
        cls.email_address = EmailAddress.objects.create(
            email=cls.user.email, user=cls.user
        )

    def test_send_confirmation(self):
        res = self.client.post(self.urls['confirm'], {'email': self.user.email})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {'detail': 'Confirmation e-mail sent.'})
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(len(self.outbox), 1)
        msg = self.outbox[0][-1]['data']['Messages'][0]
        self.assertEqual(msg['To'][0]['Email'], self.user.email)
        self.assertEqual(msg['TemplateID'], 533481)
        self.assertIn(
            'https://testserver/auth/confirm-email', msg['Variables']['link']
        )
        session = self.client.session
        self.assertEqual(session['account_user'], user_pk_to_url_str(self.user))

    def test_send_confirmation_user_inactive(self):
        """
        Tests that data of inactive users isn't processed.
        """
        models.User.objects.update(is_active=False)
        EmailAddress.objects.update(verified=True)
        res = self.client.post(self.urls['confirm'], {'email': self.user.email})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.json(), {'email': self.not_found.format(self.user.email)}
        )

    def test_send_confirmation_email_verified_already(self):
        """
        Tests that bots don't have a chance to check for existing e-mails.
        """
        EmailAddress.objects.update(verified=True)
        res = self.client.post(self.urls['confirm'], {'email': self.user.email})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            res.json(), {'email': self.not_found.format(self.user.email)}
        )
