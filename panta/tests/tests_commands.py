import datetime
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.db.models import F
from django.test import SimpleTestCase, TestCase, tag  # noqa: F401
from panta import factories, models
from path.factories import UserFactory


# TODO Shouldn't I use TransactionTestCase here?
class UnlockSegmentsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        works_dict = factories.create_work(
            segments=5, translations=1, completeness=(50, 50)
        )
        cls.original = works_dict['original']
        cls.translation = works_dict['translations'][0]

    def test_basics(self):
        out = StringIO()
        # Only the segments with content have a historical record
        # (because they are filled with content after bulk_create)
        self.assertEqual(models.TranslatedSegment.history.count(), 2)

        # No locked segments
        call_command('unlock_segments', stdout=out)
        self.assertIn(
            'Released 0 locked segment(s), created 0 and updated 0 historical',
            out.getvalue(),
        )

        # Locked segments too new
        out = StringIO()
        first_segment = self.translation.segments.first()
        first_segment.locked_by = self.user
        first_segment.save_without_historical_record()
        another_user = UserFactory()
        new_segment = factories.TranslatedSegmentFactory(locked_by=another_user)
        call_command('unlock_segments', stdout=out)
        self.assertIn(
            'Released 0 locked segment(s), created 0 and updated 0 historical',
            out.getvalue(),
        )
        self.assertEqual(models.TranslatedSegment.history.count(), 3)

        # Time passed... 2 segments to unlock
        out = StringIO()
        last_segment = self.translation.segments.last()
        last_segment.locked_by = self.user
        last_segment.save_without_historical_record()
        older_segments = (first_segment.pk, new_segment.pk)
        models.TranslatedSegment.objects.filter(pk__in=older_segments).update(
            last_modified=F('last_modified') - datetime.timedelta(minutes=3)
        )
        call_command('unlock_segments', stdout=out)
        self.assertIn(
            'Released 2 locked segment(s), created 0 and updated 0 historical',
            out.getvalue(),
        )
        self.assertEqual(models.TranslatedSegment.history.count(), 3)

        # No locked segments
        out = StringIO()
        call_command('unlock_segments', stdout=out)
        self.assertIn(
            'Released 0 locked segment(s), created 0 and updated 0 historical',
            out.getvalue(),
        )

        # Check that the unlocking doesn't create historical records
        self.assertEqual(models.TranslatedSegment.history.count(), 3)


class UpdateDBCacheTests(SimpleTestCase):
    @patch('panta.models.ImportantHeading.update')
    @patch('panta.models.WorkStatistics.update')
    def test(self, update_statistics, update_headings):
        update_headings.return_value = 10
        update_statistics.return_value = 5
        out = StringIO()
        call_command('update_db_cache', stdout=out)
        self.assertIn('Updated 10 headings and 5 statistics.', out.getvalue())
        update_headings.assert_called_once_with()
        update_statistics.assert_called_once_with()
