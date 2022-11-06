# flake8: noqa

import json
import re

from base.tests import SeleniumTests
from django.core import mail
from django.test import tag
from django.urls import reverse
from path import factories, models

HTML_REGEX = re.compile(r'src="?(/js)?/app([.a-z0-9]+)?\.js')


class JavaScriptTests(SeleniumTests):
    @classmethod
    def setUpClass(cls):
        from selenium.webdriver.firefox import webdriver

        profile = webdriver.FirefoxProfile()
        profile.set_preference('intl.accept_languages', 'en-us')
        profile.update_preferences()
        super().setUpClass(driver=webdriver.WebDriver(profile))

    def test_login(self):
        self.selenium.get(self.live_server_url)
        self.selenium.get('{}{}'.format(self.live_server_url, reverse('login')))
        self.selenium.find_element_by_name('username').send_keys('ellen')
        self.selenium.find_element_by_name('password').send_keys('pw')
        self.submit()
        user_is = json.loads(self.local_storage_retreive('user'))
        user_to_be = {
            'id': str(self.user.public_id),
            'username': 'ellen',
            'name': self.user.first_name,
            'avatar': self.user.get_avatar(),
            'authenticated': 'true',
            'expiryDate': self.client.session.get_expiry_date().isoformat(),
        }
        # TODO Why are the milliseconds different?
        self.assertEqual(
            user_is.pop('expiryDate')[:16], user_to_be.pop('expiryDate')[:16]
        )
        self.assertEqual(user_is, user_to_be)

        # When you go back in history you shouldn't get to the log in page again
        # TODO Why is an endless loop here?
        # self.selenium.back()
        self.assertEqual(
            self.selenium.current_url, '{}/'.format(self.live_server_url)
        )

    def test_login_success_url(self):
        self.selenium.get(self.live_server_url)
        success_url = reverse('api-root')
        self.selenium.get(
            '{}{}?next={}'.format(
                self.live_server_url, reverse('login'), success_url
            )
        )
        self.selenium.find_element_by_name('username').send_keys('ellen')
        self.selenium.find_element_by_name('password').send_keys('pw')
        self.submit()
        self.assertEqual(
            self.selenium.current_url,
            '{}{}'.format(self.live_server_url, success_url),
        )

    def test_logout(self):
        self.selenium.get(self.live_server_url)
        self.client.login(username=self.user.username, password='pw')
        self.local_storage_set('user', {'id': '81', 'name': 'James', 'x': 'y'})
        self.selenium.get(
            '{}{}'.format(self.live_server_url, reverse('logout'))
        )
        user_is = json.loads(self.local_storage_retreive('user'))
        user_to_be = {
            'id': '',
            'username': '',
            'name': '',
            'avatar': '',
            'authenticated': 'false',
            'expiryDate': '',
        }
        self.assertEqual(user_is, user_to_be)

        # When you go back in history you shouldn't get to the log in page again
        self.selenium.back()
        self.assertEqual(
            self.selenium.current_url, '{}/'.format(self.live_server_url)
        )

    def test_join(self):
        url = self.live_server_url + reverse('login')
        self.selenium.get(url)
        self.selenium.find_element_by_link_text('Register').click()
        password = 'lkADF$%43rds'

        # Minimum fields
        self.selenium.find_element_by_name('username').send_keys('Pit')
        self.selenium.find_element_by_name('password').send_keys(password)
        pwc = self.selenium.find_element_by_name('password_confirm')
        pwc.send_keys(password)
        self.selenium.find_element_by_name('first_name').send_keys('Pit')
        self.selenium.find_element_by_name('last_name').send_keys('Saxon')
        self.selenium.find_element_by_name('email').send_keys('pet@example.com')
        self.selenium.find_element_by_name('address').send_keys('Test street 1')
        self.selenium.find_element_by_name('zip_code').send_keys('1234')
        self.selenium.find_element_by_name('city').send_keys('Test city')
        self.selenium.find_element_by_name('country').send_keys('CA')
        self.submit()
        body = self.selenium.find_element_by_tag_name('body')
        self.assertRegex(body.get_attribute('innerHTML'), HTML_REGEX)
        pit = models.User.objects.filter(username='Pit')
        self.assertEqual(len(pit), 1)
        pit = pit[0]
        # TODO
        # self.assertEqual(pit.language, 'de')

        url = self.live_server_url + reverse('join')

        # With synonym
        self.selenium.get(url)
        self.selenium.find_element_by_name('username').send_keys('Alexa')
        self.selenium.find_element_by_name('password').send_keys(password)
        pwc = self.selenium.find_element_by_name('password_confirm')
        pwc.send_keys(password)
        self.selenium.find_element_by_name('first_name').send_keys('Alexa')
        self.selenium.find_element_by_name('last_name').send_keys('Saxon')
        self.selenium.find_element_by_name('email').send_keys('al@example.com')
        self.selenium.find_element_by_name('address').send_keys('Test street 1')
        self.selenium.find_element_by_name('zip_code').send_keys('1234')
        self.selenium.find_element_by_name('city').send_keys('Test city')
        self.selenium.find_element_by_name('country').send_keys('CA')
        self.selenium.find_element_by_name('secret_name').click()
        self.selenium.find_element_by_name('pseudonym').send_keys('Carol Höm')
        self.submit()
        body = self.selenium.find_element_by_tag_name('body')
        self.assertRegex(body.get_attribute('innerHTML'), HTML_REGEX)
        alexa = models.User.objects.filter(username='Alexa')
        self.assertEqual(len(alexa), 1)

        # Missing synonym
        self.selenium.get(url)
        self.selenium.find_element_by_name('username').send_keys('Jacob')
        self.selenium.find_element_by_name('password').send_keys(password)
        pwc = self.selenium.find_element_by_name('password_confirm')
        pwc.send_keys(password)
        self.selenium.find_element_by_name('first_name').send_keys('Jacob')
        self.selenium.find_element_by_name('last_name').send_keys('Saxon')
        self.selenium.find_element_by_name('email').send_keys('jac@example.com')
        self.selenium.find_element_by_name('address').send_keys('Test street 2')
        self.selenium.find_element_by_name('zip_code').send_keys('1234')
        self.selenium.find_element_by_name('city').send_keys('Test city')
        self.selenium.find_element_by_name('country').send_keys('CA')
        self.selenium.find_element_by_name('secret_name').click()
        self.submit()
        body = self.selenium.find_element_by_tag_name('body')
        self.assertIn(
            'Please enter a pseudonym or uncheck this box.',
            body.get_attribute('innerHTML'),
        )
        exists = models.User.objects.filter(username='Jacob').exists()
        self.assertFalse(exists)

        self.selenium.find_element_by_name('password').send_keys(password)
        pwc = self.selenium.find_element_by_name('password_confirm')
        pwc.send_keys(password)
        self.selenium.find_element_by_name('pseudonym').send_keys('André Soma')
        # import pdb;pdb.set_trace()
        self.submit()
        body = self.selenium.find_element_by_tag_name('body')
        self.assertRegex(body.get_attribute('innerHTML'), HTML_REGEX)
        exists = models.User.objects.filter(username='Jacob').exists()
        self.assertTrue(exists)

        # Missing checkbox secret
        self.selenium.get(url)
        self.selenium.find_element_by_name('username').send_keys('Sally')
        self.selenium.find_element_by_name('password').send_keys(password)
        pwc = self.selenium.find_element_by_name('password_confirm')
        pwc.send_keys(password)
        self.selenium.find_element_by_name('first_name').send_keys('Sally')
        self.selenium.find_element_by_name('last_name').send_keys('Saxon')
        self.selenium.find_element_by_name('email').send_keys(
            'sally@example.com'
        )
        self.selenium.find_element_by_name('address').send_keys('Test street 1')
        self.selenium.find_element_by_name('zip_code').send_keys('1234')
        self.selenium.find_element_by_name('city').send_keys('Test city')
        self.selenium.find_element_by_name('country').send_keys('CA')
        self.selenium.find_element_by_name('secret_name').click()
        self.selenium.find_element_by_name('pseudonym').send_keys('秀英 李')
        self.selenium.find_element_by_name('secret_name').click()
        self.submit()
        body = self.selenium.find_element_by_tag_name('body')
        self.assertRegex(body.get_attribute('innerHTML'), HTML_REGEX)
        exists = models.User.objects.filter(username='Sally').exists()
        self.assertTrue(exists)

    def test_change_password(self):
        self.login()
        password = 'lkADF$%43rds'

        url = self.live_server_url + reverse('password_change')
        self.selenium.get(url)
        self.selenium.find_element_by_name('old_password').send_keys('pw')
        self.selenium.find_element_by_name('new_password1').send_keys(password)
        self.selenium.find_element_by_name('new_password2').send_keys(password)
        self.submit()
        body = self.selenium.find_element_by_tag_name('body')
        self.assertIn('password was changed', body.get_attribute('innerHTML'))

    def test_forgot_password(self):
        password = 'lkADF$%43rds'

        # Login page
        url = self.live_server_url + reverse('login')
        self.selenium.get(url)
        self.selenium.find_element_by_link_text('Forgot password?').click()

        # Send e-mail page
        self.selenium.find_element_by_name('email').send_keys(self.user.email)
        self.submit()

        # E-mail sent page
        body = self.selenium.find_element_by_tag_name('body')
        self.assertIn('We’ve emailed instr', body.get_attribute('innerHTML'))

        # Read e-mail
        pattern = re.compile(
            r'http://localhost:[0-9]+/auth/password/reset/confirm/'
            r'[0-9A-Za-z_\-]+/[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20}/'
        )
        url = re.search(pattern, mail.outbox[0].body).group(0)

        # New password page
        self.selenium.get(url)
        self.selenium.find_element_by_name('new_password1').send_keys(password)
        self.selenium.find_element_by_name('new_password2').send_keys(password)
        self.submit()

        # Completed page
        body = self.selenium.find_element_by_tag_name('body')
        self.assertIn('password has been set.', body.get_attribute('innerHTML'))
        self.selenium.find_element_by_link_text('Log in').click()

        # Log in page
        self.selenium.find_element_by_name('username').send_keys('ellen')
        self.selenium.find_element_by_name('password').send_keys(password)
        self.submit()
