from unittest.mock import patch

from django.contrib.admin.sites import site as admin_site
from django.test import TestCase, tag  # noqa: F401
from django.urls import reverse
from panta import admin, factories, models
from path.factories import UserFactory


class AdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(is_staff=True, is_superuser=True)
        cls.draft = factories.SegmentDraftFactory()

    def setUp(self):
        self.client.force_login(self.user)


class DraftTests(AdminTests):
    def test_list_view(self):
        res = self.client.get(reverse('admin:panta_segmentdraft_changelist'))
        self.assertContains(res, 'Content')
        self.assertContains(res, 'Date created')
        self.assertContains(res, 'Owner')
        self.assertContains(res, 'Position')

    def test_change_view(self):
        res = self.client.get(
            reverse('admin:panta_segmentdraft_change', args=(self.draft.pk,))
        )
        self.assertContains(res, 'Content')


@patch('panta.admin.TranslatedWorkAdmin.message_user')
class TranslatedWorkTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        factories.TranslatedWorkFactory.create_batch(2)
        cls.works = models.TranslatedWork.objects.all()
        cls.admin = admin.TranslatedWorkAdmin(models.TranslatedWork, admin_site)

    @patch('panta.models.ImportantHeading.update')
    def test_update_headings(self, update, message_user):
        update.return_value = 3
        self.admin.update_headings('r', self.works)
        self.assertEqual(len(update.mock_calls), 2)
        message_user.assert_called_once_with('r', 'Updated 6 headings.')

    @patch('panta.models.ImportantHeading.insert')
    def test_recreate_headings(self, insert, message_user):
        insert.return_value = (8, 9)
        self.admin.recreate_headings('r', self.works)
        self.assertEqual(len(insert.mock_calls), 2)
        message_user.assert_called_once_with(
            'r', 'Deleted 0 and created 4 headings.'
        )


@patch('panta.admin.ImportantHeadingAdmin.message_user')
class ImportantHeadingTests(TestCase):
    @patch('panta.models.ImportantHeading.update')
    def test_update_headings(self, update, message_user):
        a = admin.ImportantHeadingAdmin(models.ImportantHeading, admin_site)
        update.return_value = 5
        a.update_headings('r', 'q')
        update.assert_called_once_with('q')
        message_user.assert_called_once_with('r', 'Updated 5 headings.')
