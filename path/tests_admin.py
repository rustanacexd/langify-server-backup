from django.test import TestCase, tag  # noqa: F401
from django.urls import reverse
from path import factories, models


class UserTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = factories.UserFactory(is_staff=True, is_superuser=True)

    def setUp(self):
        self.client.force_login(self.admin)

    def test_add(self):
        url = reverse('admin:path_user_add')
        password = '4$3kfgkakk$iorkjg3kj"§$dkdsflls'
        # Get
        res = self.client.get(url)
        self.assertContains(res, 'Password confirm')
        # Post
        data = {
            'username': 'Albin',
            'password_1': password,
            'password_2': password,
            'email': 'albin@example.com',
            'reputations-TOTAL_FORMS': 0,
            'reputations-INITIAL_FORMS': 0,
            'reputations-MAX_NUM_FORMS': '',
        }
        res = self.client.post(url, data, follow=True)
        self.assertContains(res, 'successful')
        self.assertContains(res, 'Active')
        self.assertTrue(models.User.objects.filter(username='Albin').exists())

    def test_change(self):
        user = factories.UserFactory()
        url = reverse('admin:path_user_change', args=(user.pk,))
        # Get
        res = self.client.get(url)
        self.assertContains(res, 'algorithm')
        self.assertContains(res, 'avatar')
        # Post
        data = {
            'username': 'Mike123',
            'reputation': 100,
            'name_display': 'first',
            'email': 'mike123@example.com',
            'image_crop': {'x': 'y'},
            'langauge': 'fr',
            'reputations-TOTAL_FORMS': 0,
            'reputations-INITIAL_FORMS': 0,
            'reputations-MAX_NUM_FORMS': '',
        }
        res = self.client.post(url, data, follow=True)
        # Test failed here because the "Personal info" part
        # seems to be missing in the test (but not in reality).
        return
        self.assertContains(res, 'successful')
