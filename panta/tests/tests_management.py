import datetime
from copy import deepcopy

from django.db.models import F
from django.test import (  # noqa: F401
    SimpleTestCase,
    TestCase,
    TransactionTestCase,
    tag,
)
from django.utils import timezone
from panta import factories, models
from panta.constants import (
    BLANK,
    CHANGE_REASONS,
    HISTORICAL_UNIT_PERIOD,
    IN_REVIEW,
    IN_TRANSLATION,
    LANGUAGE_RATIOS,
    REVIEW_DONE,
    TRANSLATION_DONE,
    TRUSTEE_DONE,
)
from panta.management import Segments
from panta.utils import get_system_user
from path.factories import UserFactory


class TransactionTests(TransactionTestCase):
    def test(self):
        user = UserFactory()
        segment = factories.TranslatedSegmentFactory(locked_by=user)
        qs = models.TranslatedSegment.objects.all()
        result = Segments().conclude(qs)
        self.assertEqual(result['unlocked'], 1)
        self.assertEqual(result['new'], 0)
        self.assertEqual(result['updated'], 0)
        self.assertEqual(segment.history.count(), 1)


class ConcludeSegmentsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.users = UserFactory.create_batch(3)
        cls.user = cls.users[0]
        works_dict = factories.create_work(
            segments=5,
            translations=1,
            completeness=(50, 50),
            additional_languages=False,
        )
        cls.original = works_dict['original']
        cls.translation = works_dict['translations'][0]
        cls._first_segment = cls.translation.segments.first()
        cls._last_segment = cls.translation.segments.last()
        cls.ratio = LANGUAGE_RATIOS[cls.translation.language]

    def get_min_content(self, segment: models.OriginalSegment, fill='+') -> str:
        """
        Returns content with minimal length for a complete translation.
        """
        return int(len(segment.content) * self.ratio + 1) * fill

    def setUp(self):
        self.first_segment = deepcopy(self._first_segment)
        self.last_segment = deepcopy(self._last_segment)

    def test_history_type_of_first_historical_record(self):
        self.assertEqual(self.first_segment.history.latest().history_type, '~')

    def test_nothing_edited(self):
        segments = self.translation.segments.all()
        self.assertEqual(segments.model.history.count(), 2)
        result = Segments().conclude(segments)
        self.assertEqual(result['unlocked'], 0)
        self.assertEqual(segments.model.history.count(), 2)

        last_modified = self.first_segment.last_modified
        self.first_segment.refresh_from_db()
        self.assertEqual(self.first_segment.last_modified, last_modified)
        last_modified = self.last_segment.last_modified
        self.last_segment.refresh_from_db()
        self.assertEqual(self.last_segment.last_modified, last_modified)

    def test_content_unchanged(self):
        # Initial
        empty_segment = self.last_segment
        empty_segment.locked_by = self.user
        empty_segment.save_without_historical_record()
        result = Segments().conclude(self.translation.segments.all())
        self.assertEqual(result['unlocked'], 1)
        self.assertEqual(result['new'], 0)
        self.assertEqual(result['updated'], 0)
        self.assertEqual(models.TranslatedSegment.history.count(), 2)
        last_modified = empty_segment.last_modified
        empty_segment.refresh_from_db()
        self.assertGreater(empty_segment.last_modified, last_modified)

        # Segment with historical record
        self.first_segment.locked_by = self.user
        self.first_segment.save_without_historical_record()
        Segments().conclude(self.translation.segments.all())
        self.assertEqual(models.TranslatedSegment.history.count(), 2)
        self.first_segment.refresh_from_db()
        self.assertEqual(self.first_segment.progress, BLANK)

    def test_first_history_entry(self):
        empty_segment = self.last_segment
        empty_segment.content = '1'
        empty_segment.locked_by = self.user
        empty_segment.save_without_historical_record()

        Segments().conclude(self.translation.segments.all())
        self.assertEqual(models.TranslatedSegment.history.count(), 3)
        history = list(empty_segment.history.all())
        self.assertEqual(len(history), 1)
        history = history[0]
        self.assertEqual(history.id, empty_segment.pk)
        self.assertEqual(history.history_date, empty_segment.last_modified)
        self.assertEqual(history.history_change_reason, 'New translation')
        self.assertEqual(history.history_user_id, self.user.pk)
        # Type has to be "changed" although it's the first historical record
        # of this segment because the segment was not created at this point
        # but earlier (in bulk).
        self.assertEqual(history.history_type, '~')
        self.assertEqual(history.content, '1')
        empty_segment.refresh_from_db()
        self.assertEqual(empty_segment.progress, IN_TRANSLATION)

        # Second edit of same user and within unit period
        empty_segment.content = 'Second edit'
        empty_segment.locked_by = self.user
        empty_segment.save_without_historical_record()

        result = Segments().conclude(self.translation.segments.all())
        self.assertEqual(result['unlocked'], 1)
        self.assertEqual(result['new'], 0)
        self.assertEqual(result['updated'], 1)
        self.assertEqual(models.TranslatedSegment.history.count(), 3)
        history = list(empty_segment.history.all())
        self.assertEqual(len(history), 1)
        history = history[0]
        self.assertEqual(history.history_date, empty_segment.last_modified)
        self.assertEqual(history.history_change_reason, 'New translation')
        self.assertEqual(history.history_user_id, self.user.pk)
        self.assertEqual(history.history_type, '~')
        self.assertEqual(history.content, 'Second edit')
        last_modified = empty_segment.last_modified
        empty_segment.refresh_from_db()
        self.assertGreater(empty_segment.last_modified, last_modified)

    def test_second_history_entry(self):
        segment = self.first_segment
        segment.content = 'Second edit'
        segment.locked_by = self.user
        segment.save_without_historical_record()

        Segments().conclude(self.translation.segments.all())
        self.assertEqual(models.TranslatedSegment.history.count(), 3)
        history = list(segment.history.all())
        self.assertEqual(len(history), 2)
        history = history[0]
        self.assertEqual(history.id, segment.pk)
        self.assertEqual(history.history_date, segment.last_modified)
        self.assertEqual(history.history_change_reason, 'Edit translation')
        self.assertEqual(history.history_user_id, self.user.pk)
        self.assertEqual(history.history_type, '~')
        self.assertEqual(history.content, 'Second edit')

        # Third edit, same user and within unit period
        segment.content = 'Third edit'
        segment.locked_by = self.user
        segment.save_without_historical_record()

        Segments().conclude(self.translation.segments.all())
        self.assertEqual(models.TranslatedSegment.history.count(), 3)
        history = list(segment.history.all())
        self.assertEqual(len(history), 2)
        history = history[0]
        self.assertEqual(history.id, segment.pk)
        self.assertEqual(history.history_date, segment.last_modified)
        self.assertEqual(history.history_change_reason, 'Edit translation')
        self.assertEqual(history.history_user_id, self.user.pk)
        self.assertEqual(history.history_type, '~')
        self.assertEqual(history.content, 'Third edit')

    def test_multiple_history_entries(self):
        empty_segment = self.last_segment
        history = []
        data = (
            ('First edit', self.users[0], 1000),
            ('Second edit', None, 100),
            ('Third edit', self.users[1], 50),
            ('Fourth edit', self.users[2], 5),
            ('Fifth edit', self.users[2], 2),
            ('Sixth edit', self.users[2], 0),
        )
        for i, h in enumerate(data, start=1):
            empty_segment.add_to_history(
                relative_id=i,
                content=h[0],
                history_user=h[1],
                history_date=timezone.now() - datetime.timedelta(days=h[2]),
                history_change_reason='edit',
                add_to=history,
            )

        models.TranslatedSegment.history.bulk_create(history)

        empty_segment.content = 'Seventh edit'
        empty_segment.locked_by = self.users[2]
        empty_segment.save_without_historical_record()

        another_segment = self.first_segment
        another_segment.content = 'Second edit'
        another_segment.locked_by = self.user
        another_segment.save_without_historical_record()

        result = Segments().conclude(self.translation.segments.all())
        self.assertEqual(result['unlocked'], 2)
        self.assertEqual(result['new'], 1)
        self.assertEqual(result['updated'], 1)
        self.assertEqual(models.TranslatedSegment.history.count(), 9)
        history = list(empty_segment.history.all())
        self.assertEqual(len(history), 6)
        most_recent = history[0]
        self.assertEqual(most_recent.history_date, empty_segment.last_modified)
        self.assertEqual(most_recent.history_change_reason, 'Edit translation')
        self.assertEqual(most_recent.history_user_id, self.users[2].pk)
        self.assertEqual(most_recent.history_type, '~')
        self.assertEqual(most_recent.content, 'Seventh edit')

        # All segments are unlocked
        qs = models.TranslatedSegment.objects.filter(locked_by__isnull=False)
        self.assertFalse(qs.exists())

    def test_most_recent_history_record_is_a_delete(self):
        segment = self.first_segment
        segment._history_user = self.user
        segment.changeReason = CHANGE_REASONS['delete']
        segment.save()
        segment.content = 'A fresh translation'
        segment.locked_by = self.user
        segment.save_without_historical_record()
        Segments().conclude(self.translation.segments.all())
        self.assertEqual(segment.history.count(), 3)
        self.assertEqual(
            segment.history.get(relative_id=2).history_change_reason,
            CHANGE_REASONS['delete'],
        )
        self.assertEqual(
            segment.history.get(relative_id=3).content, 'A fresh translation'
        )

    def test_most_recent_history_record_is_a_restore(self):
        segment = self.first_segment
        segment._history_user = self.user
        segment.changeReason = CHANGE_REASONS['restore'].format(id=100)
        segment.save()
        segment.content = 'We had this version in the past already'
        segment.locked_by = self.user
        segment.save_without_historical_record()
        Segments().conclude(self.translation.segments.all())
        self.assertEqual(segment.history.count(), 3)
        self.assertEqual(
            segment.history.get(relative_id=2).history_change_reason,
            'Restore #100',
        )
        self.assertEqual(
            segment.history.get(relative_id=3).content,
            'We had this version in the past already',
        )

    def test_not_in_unit_period(self):
        segment = self.first_segment
        segment.history.filter(pk=segment.history.latest().pk).update(
            history_user=self.user,
            history_date=F('history_date') - HISTORICAL_UNIT_PERIOD,
        )
        segment.content = 'Changed'
        segment.locked_by = self.user
        segment.save_without_historical_record()
        Segments().conclude(self.translation.segments.all())
        self.assertEqual(segment.history.count(), 2)

    def test_not_same_user(self):
        segment = self.first_segment
        segment.content = 'Change'
        segment.locked_by = self.users[0]
        segment.save_without_historical_record()
        Segments().conclude(self.translation.segments.all())
        segment.content = 'Another change'
        segment.locked_by = self.users[1]
        segment.save_without_historical_record()
        Segments().conclude(self.translation.segments.all())
        self.assertEqual(segment.history.count(), 3)

    def test_last_historical_segment_with_votes(self):
        """
        A new historical segment should always be created if the last
        historical segment has votes. (Otherwise, they became overridden if new
        votes came the next time or they were associated with the wrong text.)
        """
        segment = self.first_segment
        # The user edits the segment
        segment._history_user = self.user
        segment.changeReason = CHANGE_REASONS['change']
        segment.save()
        # Another user votes the segment
        factories.VoteFactory(segment=segment, user=self.users[1])
        record = segment.history.latest()
        # The user edits the segment again
        segment.content = 'Change'
        segment.locked_by = self.user
        segment.keep_votes_when_skipping_history = False
        segment.save_without_historical_record()
        Segments().conclude(self.translation.segments.all())
        # A new historical segment is expected
        self.assertEqual(segment.history.count(), 3)
        self.assertTrue(record.votes.exists())
        self.assertFalse(segment.history.latest().votes.exists())

    def test_clear_content(self):
        segment = self.first_segment
        segment.content = ''
        segment.locked_by = self.user
        segment.progress = 99
        segment.save_without_historical_record()
        Segments().conclude(self.translation.segments.all())
        history = segment.history.latest()
        self.assertEqual(history.history_change_reason, 'Clear translation')
        segment.refresh_from_db()
        self.assertEqual(segment.progress, BLANK)

    # Progress

    # BLANK and IN_TRANSLATION are tested above

    def test_progress_complete(self):
        segments = self.translation.segments.all().select_related('original')
        segment_1, segment_2, segment_3 = segments[:3]
        # blank
        segment_1.content = self.get_min_content(segment_1.original, 'a')
        segment_1.locked_by = self.user
        segment_1.save_without_historical_record()
        # in_translation
        segment_2.content = self.get_min_content(segment_2.original, 'b')
        segment_2.locked_by = self.user
        segment_2.progress = IN_TRANSLATION
        segment_2.clean()
        segment_2.save_without_historical_record()
        # above
        segment_3.content = self.get_min_content(segment_3.original, 'c')
        segment_3.locked_by = self.user
        segment_3.progress = TRUSTEE_DONE
        segment_3.save_without_historical_record()
        models.Vote.objects.create(
            segment=segment_3, user=self.user, role='trustee', value=1
        )

        result = Segments().conclude(self.translation.segments.all())
        self.assertEqual(result, {'unlocked': 3, 'new': 3, 'updated': 0})
        segment_1, segment_2, segment_3 = self.translation.segments.all()[:3]
        self.assertEqual(segment_1.progress, TRANSLATION_DONE)
        self.assertEqual(segment_2.progress, TRANSLATION_DONE)
        # Other states are not overridden
        self.assertEqual(segment_3.progress, TRUSTEE_DONE)

    def test_progress_complete_has_some_tolerance(self):
        segment = self.first_segment
        # Less
        original = segment.original
        original.content = 300 * '.'
        original.save_without_historical_record()
        segment.content = self.get_min_content(original)
        segment.locked_by = self.user
        segment.save_without_historical_record()
        Segments().conclude(self.translation.segments.all())
        segment.refresh_from_db()
        self.assertEqual(segment.progress, TRANSLATION_DONE)
        # More
        segment.content = segment.original.content + ' This is the addition.'
        segment.locked_by = self.user
        segment.save_without_historical_record()
        Segments().conclude(self.translation.segments.all())
        segment.refresh_from_db()
        self.assertEqual(segment.progress, TRANSLATION_DONE)

    def test_progress_in_review(self):
        segment = self.last_segment
        segment.content = 'a'
        segment.locked_by = self.user
        segment.save_without_historical_record()
        models.Vote.objects.create(
            segment=segment, value=1, role='reviewer', user=self.user
        )
        Segments().conclude(self.translation.segments.all())
        segment.refresh_from_db()
        self.assertEqual(segment.progress, IN_REVIEW)
        # Progress shouldn't get overridden
        models.Vote.objects.all().delete()
        segment.locked_by = self.user
        segment.save_without_historical_record()
        Segments().conclude(self.translation.segments.all())
        segment.refresh_from_db()
        self.assertEqual(segment.progress, IN_REVIEW)

    def test_progress_review_done(self):
        segment = self.last_segment
        segment.content = 'b'
        segment.locked_by = self.user
        segment.save_without_historical_record()
        models.Vote.objects.create(
            segment=segment, value=3, role='reviewer', user=self.user
        )
        Segments().conclude(self.translation.segments.all())
        segment.refresh_from_db()
        self.assertEqual(segment.progress, REVIEW_DONE)
        # Progress should be set to "in review" when you delete the votes
        models.Vote.objects.all().delete()
        segment.locked_by = self.user
        segment.save_without_historical_record()
        Segments().conclude(self.translation.segments.all())
        segment.refresh_from_db()
        self.assertEqual(segment.progress, IN_REVIEW)

    def test_progress_trustee_done(self):
        segment = self.last_segment
        segment.content = 'c'
        segment.locked_by = self.user
        segment.save_without_historical_record()
        models.Vote.objects.create(
            segment=segment, value=1, role='trustee', user=self.user
        )
        Segments().conclude(self.translation.segments.all())
        segment.refresh_from_db()
        self.assertEqual(segment.progress, TRUSTEE_DONE)
        # Progress should be set to "in review" when you delete the votes
        models.Vote.objects.all().delete()
        segment.locked_by = self.user
        segment.save_without_historical_record()
        Segments().conclude(self.translation.segments.all())
        segment.refresh_from_db()
        self.assertEqual(segment.progress, IN_REVIEW)

    def test_progress_with_multiple_segments(self):
        segments = self.translation.segments.all().select_related('original')
        for s, length in zip(segments, (0, 2, 5, 300, 301)):
            s.locked_by = self.user
            if length == 5:
                s.progress = IN_TRANSLATION
                s.content = length * '+'
            elif length == 300:
                s.content = self.get_min_content(s.original)
            elif length == 301:
                s.progress = TRANSLATION_DONE
                s.content = self.get_min_content(s.original) + '1'
            else:
                s.content = length * '+'
            s.save_without_historical_record()
        result = Segments().conclude(self.translation.segments.all())
        self.assertEqual(result, {'unlocked': 5, 'new': 5, 'updated': 0})
        expected = [BLANK] + 2 * [IN_TRANSLATION] + 2 * [TRANSLATION_DONE]
        for s, state in zip(self.translation.segments.all(), expected):
            self.assertEqual(s.progress, state)
            self.assertIsNone(s.locked_by)

    def test_progress_with_accepted_deepl_translation(self):
        segment = self.first_segment
        segment.locked_by = self.user
        segment.save_without_historical_record()
        segment.add_to_history('+', history_user=get_system_user('AI'))
        result = Segments().conclude(self.translation.segments.all())
        self.assertEqual(result, {'unlocked': 1, 'new': 0, 'updated': 0})
        segment.refresh_from_db()
        self.assertIn(segment.progress, (IN_TRANSLATION, TRANSLATION_DONE))


class SimpleTests(SimpleTestCase):
    maxDiff = None

    def test_add_to_update_list(self):
        matrix = (
            # Blank
            (1, BLANK, BLANK),
            (2, BLANK, IN_TRANSLATION),
            (3, BLANK, TRANSLATION_DONE),
            (4, BLANK, IN_REVIEW),
            (5, BLANK, REVIEW_DONE),
            (6, BLANK, TRUSTEE_DONE),
            # In translation
            (7, IN_TRANSLATION, BLANK),
            (8, IN_TRANSLATION, IN_TRANSLATION),
            (9, IN_TRANSLATION, TRANSLATION_DONE),
            (10, IN_TRANSLATION, IN_REVIEW),
            (11, IN_TRANSLATION, REVIEW_DONE),
            (12, IN_TRANSLATION, TRUSTEE_DONE),
            # Translation done
            (13, TRANSLATION_DONE, BLANK),
            (14, TRANSLATION_DONE, IN_TRANSLATION),
            (15, TRANSLATION_DONE, TRANSLATION_DONE),
            (16, TRANSLATION_DONE, IN_REVIEW),
            (17, TRANSLATION_DONE, REVIEW_DONE),
            (18, TRANSLATION_DONE, TRUSTEE_DONE),
            # In review
            (19, IN_REVIEW, BLANK),
            (20, IN_REVIEW, IN_TRANSLATION),
            (21, IN_REVIEW, TRANSLATION_DONE),
            (22, IN_REVIEW, IN_REVIEW),
            (23, IN_REVIEW, REVIEW_DONE),
            (24, IN_REVIEW, TRUSTEE_DONE),
            # Review done
            (25, REVIEW_DONE, BLANK),
            (26, REVIEW_DONE, IN_TRANSLATION),
            (27, REVIEW_DONE, TRANSLATION_DONE),
            (28, REVIEW_DONE, IN_REVIEW),
            (29, REVIEW_DONE, REVIEW_DONE),
            (30, REVIEW_DONE, TRUSTEE_DONE),
            # Trustee done
            (31, TRUSTEE_DONE, BLANK),
            (32, TRUSTEE_DONE, IN_TRANSLATION),
            (33, TRUSTEE_DONE, TRANSLATION_DONE),
            (34, TRUSTEE_DONE, IN_REVIEW),
            (35, TRUSTEE_DONE, REVIEW_DONE),
            (36, TRUSTEE_DONE, TRUSTEE_DONE),
        )
        instance = Segments()

        def determine_progress(self):
            return self.current

        for i, previous, current in matrix:
            segment = models.TranslatedSegment(pk=i, progress=previous)
            segment.current = current
            # Override the method (because it's not that easy to subclass a
            # model)
            segment.determine_progress = determine_progress.__get__(segment)
            instance.add_to_update_list(segment)

        expected = {
            BLANK: [1, 7, 13, 19, 25, 31],
            IN_TRANSLATION: [2, 8, 14],
            TRANSLATION_DONE: [3, 9, 15],
            IN_REVIEW: [4, 10, 16, 20, 21, 22, 26, 27, 28, 32, 33, 34],
            REVIEW_DONE: [5, 11, 17, 23, 29, 35],
            TRUSTEE_DONE: [6, 12, 18, 24, 30, 36],
        }

        self.assertEqual(instance.states, expected)
