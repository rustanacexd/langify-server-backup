from copy import deepcopy
from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, call, patch

from django.core.exceptions import ValidationError
from django.db import transaction
from django.test import SimpleTestCase, TestCase, override_settings, tag
from django.utils import timezone
from panta import factories, models
from panta.constants import (
    BLANK,
    IN_REVIEW,
    IN_TRANSLATION,
    RELEASED,
    REVIEW_DONE,
    TRANSLATION_DONE,
    TRUSTEE_DONE,
)
from panta.tests.tests_api_external import requests_mock
from path.factories import UserFactory
from path.models import User


class OriginalWorkTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.work = factories.OriginalWorkFactory(language='en', segments=3)

    def tearDown(self):
        requests_mock.reset_mock()

    @patch('panta.api.external.requests', requests_mock)
    @patch('panta.models.TranslatedWork.update_pretranslated')
    @override_settings(DEEPL_KEY='123')
    def test_get_deepl_translation(self, update_pretranslated):
        result = self.work.get_deepl_translation('de', positions=(2, 3))
        self.assertEqual(result, (2, 1))
        self.assertTrue(
            models.BaseTranslator.objects.filter(
                name='DeepL.com', type='ai'
            ).exists()
        )
        self.assertTrue(
            models.BaseTranslation.objects.filter(
                language='de', translator__name='DeepL.com'
            ).exists()
        )
        self.assertEqual(
            models.BaseTranslationSegment.objects.filter(
                content='mock',
                translation__language='de',
                translation__translator__name='DeepL.com',
            ).count(),
            2,
        )
        self.assertEqual(len(requests_mock.method_calls), 2)
        url = 'https://api.deepl.com/v1/translate'
        requests_mock.post.assert_has_calls(
            [
                call(
                    url,
                    params={
                        'text': s.content,
                        'source_lang': 'EN',
                        'target_lang': 'DE',
                        'auth_key': '123',
                        'tag_handling': 'xml',
                        'non_splitting_tags': ['span'],
                        # 'preserve_formatting': 1,
                    },
                )
                for s in self.work.segments.all()[1:]
            ]
        )
        # Same segments, another language
        result = self.work.get_deepl_translation('fr', positions=(2, 3))
        self.assertEqual(result, (2, 1))
        requests_mock.reset_mock()
        # Calling it again shouldn't process segments twice
        result = self.work.get_deepl_translation('de')
        self.assertEqual(result, (1, 1))
        self.assertEqual(len(requests_mock.method_calls), 1)
        update_pretranslated.assert_not_called()

    @patch('panta.api.external.requests', requests_mock)
    @override_settings(DEEPL_KEY='123')
    def test_get_deepl_translation_with_params(self):
        result = self.work.get_deepl_translation('fr', positions=(1,), x=1)
        self.assertEqual(result, (1, 1))
        requests_mock.post.assert_called_once_with(
            'https://api.deepl.com/v1/translate',
            params={
                'text': self.work.segments.first().content,
                'source_lang': 'EN',
                'target_lang': 'FR',
                'x': 1,
                'auth_key': '123',
                'tag_handling': 'xml',
                'non_splitting_tags': ['span'],
                # 'preserve_formatting': 1,
            },
        )

    @patch('panta.api.external.requests', requests_mock)
    @patch('panta.models.TranslatedWork.update_pretranslated')
    def test_get_deepl_translation_creates_historical_records(
        self, update_pretranslated
    ):
        trans_work = factories.TranslatedWorkFactory(
            original=self.work, language='af'
        )
        factories.TranslatedWorkFactory(original=self.work, language='sw')
        segment = trans_work.segments.first()
        segment.save()
        update_pretranslated.reset_mock()
        result = self.work.get_deepl_translation('af')
        self.assertEqual(result, (3, 1))
        history_model = models.TranslatedSegment.history.model
        self.assertEqual(history_model.objects.count(), 3)
        ai_user = User.objects.get(username='AI')
        self.assertEqual(
            history_model.objects.filter(
                id__in=trans_work.segments.values_list('pk', flat=True),
                history_change_reason='DeepL.com translation',
                history_user=ai_user,
            ).count(),
            2,
        )
        update_pretranslated.assert_called_once_with()


@tag('slow')
class TranslatedWorkTests(TestCase):
    maxDiff = None

    @classmethod
    def segments(cls):
        h2 = 'h2 '
        h3 = 'h3 '
        p = 'p '
        blueprint = (
            ('h1 p p h2 h3 ' + 9 * p + h3 + 5 * p + h2 + 20 * p + h2 + 5 * p)
            #  1      4  5             15           21            42
            + (h3 + 25 * p + h3 + 15 * p + h3 + 22 * p + h2 + p + h3 + 12 * p)
            #  48            74            90           113      115        127
        )
        # cls.segments_per_chapter = iter((14, 6, 21, 6, 26, 16, 23, 15))
        segments_per_chapter = (1, 10, 6, 21, 6, 26, 16, 23, 2, 13)
        cls.chapters = len(segments_per_chapter)
        cls.segments_per_chapter = iter(segments_per_chapter)
        return blueprint.strip()

    @classmethod
    def setUpTestData(cls):
        cls.original_work = factories.OriginalWorkFactory(
            segments=cls.segments()
        )
        cls.original_segments = tuple(cls.original_work.segments.all())
        factories.BaseTranslationSegmentFactory(
            original=cls.original_segments[0], translation__language='de'
        )
        factories.BaseTranslationSegmentFactory(
            original=cls.original_segments[0], translation__language='fr'
        )
        factories.BaseTranslationSegmentFactory(
            original=cls.original_segments[1], translation__language='jp'
        )
        cls.translated_work = factories.TranslatedWorkFactory(
            original=cls.original_work,
            trustee=cls.original_work.trustee,
            language='de',
        )

    def test_create_segments_in_advance(self):
        orig_segments = self.original_work.segments.all()
        trans_segments = self.translated_work.segments.all()
        self.assertEqual(len(orig_segments), len(trans_segments))
        for orig_s, trans_s in zip(orig_segments, trans_segments):
            self.assertEqual(orig_s.position, trans_s.position)
            self.assertEqual(orig_s.tag, trans_s.tag)
            self.assertEqual(orig_s.classes, trans_s.classes)
            self.assertEqual(orig_s.pk, trans_s.original_id)
            self.assertEqual('', trans_s.content)

    def test_create_historical_records_for_base_translations(self):
        self.assertEqual(self.original_segments[0].basetranslations.count(), 2)
        self.assertEqual(self.original_segments[1].basetranslations.count(), 1)
        self.assertEqual(
            self.original_segments[0].translations.first().history.count(), 1
        )
        self.assertFalse(
            self.original_segments[1].translations.first().history.exists()
        )

    @patch('panta.models.ImportantHeading.update_pretranslated')
    @patch('panta.models.WorkStatistics.save')
    def test_update_pretranslated(self, save, update_pretranslated):
        update_pretranslated.return_value = 1
        work = models.TranslatedWork.objects.select_related('statistics').get()
        models.ImportantHeading.objects.update(pretranslated=2)
        work.statistics.segments = 23
        work.statistics.pretranslated_count = 10
        stats = work.update_pretranslated(chapters=False, save=False)
        expected = {
            'pretranslated_count': 2,
            'pretranslated_percent': 200.0 / 23,
        }
        self.assertEqual(stats, expected)
        update_pretranslated.assert_not_called()
        self.assertEqual(work.statistics.pretranslated_count, 10)

        work.pretranslated = 5
        stats = work.update_pretranslated(chapters=False, save=False)
        expected = {
            'pretranslated_count': 5,
            'pretranslated_percent': 500.0 / 23,
        }
        self.assertEqual(stats, expected)

        stats = work.update_pretranslated(chapters=True, save=False)
        expected = {
            'pretranslated_count': self.chapters,
            'pretranslated_percent': self.chapters * 100.0 / 23,
        }
        self.assertEqual(stats, expected)
        self.assertEqual(update_pretranslated.call_count, self.chapters)

        work.statistics.pretranslated_count = 5
        work.update_pretranslated(chapters=False, save=True)
        segments_count = len(self.original_segments)
        self.assertEqual(
            work.statistics.pretranslated_percent,
            (segments_count - 1) * 100.0 / segments_count,
        )
        save.assert_not_called()

        work.statistics.pretranslated_count = 0
        work.update_pretranslated(chapters=False, save=True)
        self.assertEqual(work.statistics.pretranslated_count, 5)
        self.assertEqual(work.statistics.pretranslated_percent, 500.0 / 23)
        save.assert_called_once()


@tag('fast', 'duplicate')
class MinimumTranslatedWorkTests(TranslatedWorkTests):
    @classmethod
    def segments(cls):
        segments_per_chapter = (2,)
        cls.chapters = len(segments_per_chapter)
        cls.segments_per_chapter = iter(segments_per_chapter)
        return 'h2 p'


class TranslatedWorkTableOfContentsTests(TestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        owork = factories.OriginalWorkFactory(segments='h1 h2 p p h3 p p p h2')
        #                                                1  2 3 4  5 6 7 8  9
        obj = factories.TranslatedWorkFactory(original=owork)
        obj.segments.filter(position__lte=2).update(
            content='New content',
            progress=TRANSLATION_DONE,
            last_modified=timezone.now(),
        )
        obj.segments.filter(position__gt=2, position__lte=5).update(
            progress=IN_REVIEW, last_modified=timezone.now()
        )
        obj.segments.filter(position__gt=5, position__lte=7).update(
            progress=REVIEW_DONE, last_modified=timezone.now()
        )
        obj.segments.filter(position=8).update(
            progress=TRUSTEE_DONE, last_modified=timezone.now()
        )
        cls.segments = tuple(obj.segments.select_related('original'))
        user_1 = UserFactory()
        user_2 = UserFactory()
        models.TranslatedSegment.history.bulk_create(
            (
                cls.segments[0].add_to_history(history_user=user_1, save=False),
                cls.segments[1].add_to_history(history_user=user_1, save=False),
                cls.segments[2].add_to_history(history_user=user_1, save=False),
                cls.segments[3].add_to_history(history_user=user_2, save=False),
                cls.segments[4].add_to_history(history_user=user_2, save=False),
                cls.segments[5].add_to_history(save=False),
            )
        )
        models.ImportantHeading.update()
        # Test that the headings are sorted
        heading = models.ImportantHeading.objects.all()[1]
        heading.delete()
        heading.pk = None  # This tells Django to 'INSERT'
        heading.save()
        cls._obj = models.TranslatedWork.objects.for_response().get()

    def setUp(self):
        self.obj = deepcopy(self._obj)

    def test_table_of_contents(self):
        expected = (
            {
                'first_position': None,
                'position': 2,
                'tag': 'h2',
                'classes': [],
                'content': 'New content',
                'translation_done': None,
                'review_done': None,
                'trustee_done': None,
                'segments_count': None,
            },
            {
                'first_position': 1,
                'position': 5,
                'tag': 'h3',
                'classes': [],
                'content': self.segments[4].original.content,
                'translation_done': 8,
                'review_done': 3,
                'trustee_done': 1,
                'segments_count': 8,
            },
            {
                'first_position': 9,
                'position': 9,
                'tag': 'h2',
                'classes': [],
                'content': self.segments[8].original.content,
                'translation_done': 0,
                'review_done': 0,
                'trustee_done': 0,
                'segments_count': 1,
            },
        )
        with self.assertNumQueries(1):
            self.assertEqual(
                tuple(self.obj.table_of_contents.values(*expected[0])), expected
            )


class TranslatedSegmentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.obj = factories.TranslatedSegmentFactory()
        cls.original = factories.OriginalSegmentFactory(
            work=cls.obj.original.work, position=2
        )
        cls.vote = factories.VoteFactory(segment=cls.obj)

    def test_create_and_update_same_instance_with_progress_released(self):
        segment = factories.TranslatedSegmentFactory(
            progress=RELEASED, work=self.obj.work, original=self.original
        )
        self.assertEqual(segment._loaded_content, segment.content)
        self.vote.segment = segment
        self.vote.save()

        segment.tag = 'abc'
        segment.save()
        self.assertEqual(segment._loaded_content, segment.content)
        self.assertTrue(segment.votes.exists())
        self.assertEqual(segment.history.count(), 2)
        record = segment.history.latest()
        self.assertEqual(segment.progress, RELEASED)
        self.assertEqual(record.votes.count(), 1)
        self.assertEqual(self.vote.historical_segments.count(), 1)

        segment.content = 'Something new'
        segment.save()
        self.assertEqual(segment._loaded_content, 'Something new')
        self.assertFalse(segment.votes.exists())
        self.assertEqual(segment.history.count(), 3)
        record = segment.history.latest()
        self.assertEqual(record.content, 'Something new')
        self.assertEqual(record.votes.count(), 1)
        self.assertEqual(self.vote.historical_segments.count(), 2)

        segment.save()
        self.assertEqual(segment._loaded_content, 'Something new')
        self.assertEqual(segment.history.count(), 4)
        record = segment.history.latest()
        self.assertEqual(record.votes.count(), 0)
        self.assertEqual(self.vote.historical_segments.count(), 2)

        segment.content = 'This comes next!'
        self.vote.segment = segment
        self.vote.save()
        segment.save_without_historical_record()
        self.assertEqual(segment._loaded_content, 'This comes next!')
        self.assertTrue(segment.votes.exists())
        self.assertEqual(segment.history.count(), 4)

        segment.save()
        self.assertEqual(self.vote.historical_segments.count(), 3)

        segment.content = '3rd'
        segment.save()
        self.assertEqual(self.vote.historical_segments.count(), 4)

    def test_create_and_update_same_instance_with_progress_lt_released(self):
        segment = factories.TranslatedSegmentFactory(
            work=self.obj.work, original=self.original
        )
        self.assertEqual(segment._loaded_content, segment.content)
        self.vote.segment = segment
        self.vote.save()

        segment.tag = 'abc'
        segment.save()
        self.assertEqual(segment._loaded_content, segment.content)
        self.assertTrue(segment.votes.exists())
        self.assertEqual(segment.history.count(), 2)
        record = segment.history.latest()
        self.assertEqual(record.votes.count(), 1)
        self.assertEqual(self.vote.historical_segments.count(), 1)

        segment.content = 'Something new'
        segment.save()
        self.assertEqual(segment._loaded_content, 'Something new')
        self.assertTrue(segment.votes.exists())
        self.assertEqual(segment.history.count(), 3)
        record = segment.history.latest()
        self.assertEqual(record.content, 'Something new')
        self.assertEqual(record.votes.count(), 1)
        self.assertEqual(self.vote.historical_segments.count(), 2)

        segment.save()
        self.assertEqual(segment._loaded_content, 'Something new')
        self.assertEqual(segment.history.count(), 4)
        record = segment.history.latest()
        self.assertEqual(record.votes.count(), 1)
        self.assertEqual(self.vote.historical_segments.count(), 3)

        segment.content = 'This comes next!'
        self.vote.segment = segment
        self.vote.save()
        segment.save_without_historical_record()
        self.assertEqual(segment._loaded_content, 'This comes next!')
        self.assertTrue(segment.votes.exists())
        self.assertEqual(segment.history.count(), 4)

        segment.save()
        self.assertEqual(self.vote.historical_segments.count(), 4)

        segment.content = '3rd'
        segment.save()
        self.assertEqual(self.vote.historical_segments.count(), 5)

    def test_create_and_update_same_instance_without_history(self):
        segment = factories.TranslatedSegmentFactory.build(
            progress=RELEASED, work=self.obj.work, original=self.original
        )
        self.assertFalse(hasattr(segment, '_loaded_content'))
        segment.save_without_historical_record()
        self.assertEqual(segment._loaded_content, segment.content)
        self.vote.segment = segment
        self.vote.save()

        segment.content = 'Something new'
        segment.save_without_historical_record()
        self.assertEqual(segment._loaded_content, 'Something new')
        self.assertTrue(segment.votes.exists())

        segment.tag = 'abc'
        segment.save_without_historical_record()
        self.assertTrue(segment.votes.exists())

        segment.content = 'This comes next!'
        segment.save()
        self.assertEqual(segment._loaded_content, 'This comes next!')
        self.assertFalse(segment.votes.exists())

    def test_retrieve_and_save(self):
        models.TranslatedSegment.objects.update(progress=RELEASED)
        segment = models.TranslatedSegment.objects.get()
        self.assertEqual(segment._loaded_content, segment.content)
        self.assertTrue(segment.votes.exists())
        segment.content = 'Something new'
        segment.save()
        self.assertFalse(segment.votes.exists())
        segment.content = 'This comes next!'
        segment.save_without_historical_record()

    def test_content_not_retrieved_but_updated(self):
        segment = models.TranslatedSegment.objects.defer('content').get()
        self.assertNotIn('content', segment.__dict__)
        self.assertNotIn('content', segment.__dict__)
        segment.tag = 'abc'
        segment.save(update_fields=('tag',))
        segment.content = 'Something new'
        with self.assertRaises(AssertionError):
            # Excluding content should actually not raise this error.
            # But I don't use update_fields and it's nice for testing.
            # However, should be changed in case we need it.
            # ...It turned out that there is a strange behavior. See todo in
            # the save() method.
            with transaction.atomic():
                segment.save(update_fields=('tag',))
        segment.content = 'This comes next!'
        with self.assertRaises(AssertionError):
            # This behavior could be changed but you should improve your query
            # anyway. So raising an error here is no bad practice.
            segment.save_without_historical_record()


class SimpleTranslatedSegmentTests(SimpleTestCase):
    def get_segment(self, content='', original_content=None):
        segment = models.TranslatedSegment(
            content=content,
            work=models.TranslatedWork(language='de'),
            original=models.OriginalSegment(
                content=original_content or 100 * 'a'
            ),
        )
        segment.reviewers_vote = None
        segment.trustees_vote = None
        return segment

    def assert_state(self, content, state, original_content=None):
        segment = self.get_segment(content, original_content)
        self.assertEqual(segment.determine_progress(), state)

    def test__getattr__(self):
        segment = models.TranslatedSegment()
        expected = "'TranslatedSegment' object has no attribute 'trustees_vote'"
        with self.assertRaisesMessage(AttributeError, expected):
            segment.trustees
        segment.translators_vote = None
        segment.reviewers_vote = None
        segment.trustees_vote = None
        segment.user_translator_vote = None
        segment.user_reviewer_vote = None
        segment.user_trustee_vote = None
        expected = {'vote': 0, 'user': 0}
        self.assertEqual(segment.translators, expected)
        self.assertEqual(segment.reviewers, expected)
        self.assertEqual(segment.trustees, expected)

    def test_has_minimum_vote(self):
        segment = models.TranslatedSegment()
        segment.translators_vote = None
        self.assertTrue(segment.has_minimum_vote('translator', -1))
        self.assertTrue(segment.has_minimum_vote('translator', 0))
        self.assertFalse(segment.has_minimum_vote('translator', 1))
        segment.translators_vote = -4
        self.assertTrue(segment.has_minimum_vote('translator', -5))
        self.assertTrue(segment.has_minimum_vote('translator', -4))
        self.assertFalse(segment.has_minimum_vote('translator', 4))

    def test_can_edit(self):
        segment = models.TranslatedSegment()
        segment.progress = IN_TRANSLATION
        segment.reviewers_vote = -3
        segment.trustees_vote = 0
        self.assertTrue(segment.can_edit('translator'))
        self.assertTrue(segment.can_edit('reviewer'))
        self.assertTrue(segment.can_edit('trustee'))
        segment.progress = IN_REVIEW
        self.assertFalse(segment.can_edit('translator'))
        self.assertTrue(segment.can_edit('reviewer'))
        self.assertTrue(segment.can_edit('trustee'))
        segment.progress = IN_TRANSLATION
        segment.reviewers_vote = 1
        self.assertFalse(segment.can_edit('translator'))
        self.assertTrue(segment.can_edit('reviewer'))
        self.assertTrue(segment.can_edit('trustee'))
        segment.reviewers_vote = -3
        segment.trustees_vote = 1
        self.assertFalse(segment.can_edit('translator'))
        self.assertFalse(segment.can_edit('reviewer'))
        self.assertTrue(segment.can_edit('trustee'))
        segment.progress = IN_REVIEW
        segment.reviewers_vote = 100
        segment.trustees_vote = 100
        self.assertFalse(segment.can_edit('translator'))
        self.assertFalse(segment.can_edit('reviewer'))
        self.assertTrue(segment.can_edit('trustee'))

    def test_voting_done(self):
        segment = self.get_segment()
        segment.translators_vote = 0
        segment.reviewers_vote = 0
        segment.trustees_vote = 0
        self.assertTrue(segment.voting_done('translator'))
        self.assertFalse(segment.voting_done('reviewer'))
        self.assertFalse(segment.voting_done('trustee'))

        segment.translators_vote = 1
        segment.reviewers_vote = 1
        segment.trustees_vote = 1
        self.assertTrue(segment.voting_done('translator'))
        self.assertFalse(segment.voting_done('reviewer'))
        self.assertTrue(segment.voting_done('trustee'))

        segment.translators_vote = 2
        segment.reviewers_vote = 2
        segment.trustees_vote = 5
        self.assertTrue(segment.voting_done('translator'))
        self.assertTrue(segment.voting_done('reviewer'))
        self.assertTrue(segment.voting_done('trustee'))

    def test_can_vote(self):
        segment = self.get_segment()
        segment.progress = IN_TRANSLATION
        segment.translators_vote = None
        segment.reviewers_vote = 1
        self.assertTrue(segment.can_vote('translator'))
        self.assertTrue(segment.can_vote('reviewer'))
        self.assertFalse(segment.can_vote('trustee'))

        segment.reviewers_vote = 2
        self.assertTrue(segment.can_vote('translator'))
        self.assertTrue(segment.can_vote('reviewer'))
        self.assertTrue(segment.can_vote('trustee'))

        segment.progress = BLANK
        self.assertFalse(segment.can_vote('translator'))
        self.assertFalse(segment.can_vote('reviewer'))
        self.assertFalse(segment.can_vote('trustee'))

    # determine_progress

    def test_blank(self):
        self.assert_state('', BLANK)

    def test_html_is_ignored_in_original(self):
        self.assert_state(60 * 'i', TRANSLATION_DONE, 60 * '<em>i</em>')

    def test_html_is_ignored_in_translation(self):
        self.assert_state(51 * '<em>i</em>', IN_TRANSLATION)

    def test_short_text(self):
        self.assert_state(19 * 'b', TRANSLATION_DONE, 40 * 'c')

    def test_in_translation(self):
        self.assert_state('d', IN_TRANSLATION)

    def test_translation_done(self):
        self.assert_state(95 * 'e', TRANSLATION_DONE)

    def test_in_review(self):
        segment = self.get_segment(content='a')
        segment.reviewers_vote = 1
        self.assertEqual(segment.determine_progress(), IN_REVIEW)

    def test_review_done(self):
        segment = self.get_segment(content='a')
        segment.reviewers_vote = 3
        self.assertEqual(segment.determine_progress(), REVIEW_DONE)

    def test_trustee_done(self):
        segment = self.get_segment(content='a')
        segment.trustees_vote = 1
        self.assertEqual(segment.determine_progress(), TRUSTEE_DONE)

    def test_determine_progress_by_votes(self):
        segment = self.get_segment()
        segment.progress = BLANK
        self.assertEqual(segment.determine_progress(content=False), None)
        segment.progress = IN_TRANSLATION
        self.assertEqual(segment.determine_progress(content=False), None)
        segment.reviewers_vote = 1
        self.assertEqual(segment.determine_progress(content=False), IN_REVIEW)
        segment.reviewers_vote = 3
        self.assertEqual(segment.determine_progress(content=False), REVIEW_DONE)
        segment.trustees_vote = 1
        self.assertEqual(
            segment.determine_progress(content=False), TRUSTEE_DONE
        )

    def test_determine_progress_by_votes_with_additional(self):
        segment = self.get_segment()
        vote = models.Vote(role='reviewer', value=-1)
        segment.progress = BLANK
        self.assertEqual(
            segment.determine_progress(content=False, additional=vote), None
        )
        vote.value = 1
        self.assertEqual(
            segment.determine_progress(content=False, additional=vote), None
        )
        self.assertEqual(
            segment.determine_progress(content=False, additional=vote),
            IN_REVIEW,
        )
        # self.assertEqual(
        #     segment.determine_progress(content=False, additional=vote),
        #     IN_REVIEW,
        # )
        self.assertEqual(
            segment.determine_progress(content=False, additional=vote),
            REVIEW_DONE,
        )
        vote.role = 'trustee'
        self.assertEqual(
            segment.determine_progress(content=False, additional=vote),
            TRUSTEE_DONE,
        )


class SegmentDraftTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.segment = factories.TranslatedSegmentFactory()

    def test_clean(self):
        draft = models.SegmentDraft(
            content='Lorem ipsum',
            segment_id=self.segment.pk,
            work_id=self.segment.work_id,
            owner_id=self.user.pk,
        )
        msg = 'This segment is currently locked by another user.'
        with self.assertRaisesMessage(ValidationError, msg):
            draft.full_clean()


class HistoricalTranslatedSegmentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.segment = factories.TranslatedSegmentFactory()
        cls.obj = cls.segment.history.first()

    def test_increment_per_segment(self):
        segment_2 = factories.TranslatedSegmentFactory()
        self.assertEqual(segment_2.history.first().relative_id, 1)
        self.segment.save()
        self.assertEqual(self.segment.history.latest().relative_id, 2)

    def test_increment_relative_id_at_creation_only(self):
        self.assertEqual(self.obj.relative_id, 1)
        self.segment.save()
        self.assertEqual(self.segment.history.latest().relative_id, 2)
        self.obj.history_change_reason = 'relative_id should stay 1'
        self.obj.save()
        self.obj.refresh_from_db()
        self.assertEqual(self.obj.relative_id, 1)
        self.assertEqual(
            self.obj.history_change_reason, 'relative_id should stay 1'
        )


class VoteTests(SimpleTestCase):
    def test__str__(self):
        vote = models.Vote(value=1)
        self.assertEqual(str(vote), '+1')
        vote.value = -2
        self.assertEqual(str(vote), '-2')

    def test_action_revoke_false(self):
        vote = models.Vote(value=-2)
        self.assertEqual(vote.action, 'disapproved')
        vote.value = -1
        self.assertEqual(vote.action, 'disapproved')
        vote.value = 1
        self.assertEqual(vote.action, 'approved')
        vote.value = 2
        self.assertEqual(vote.action, 'approved')

    def test_action_revoke_true(self):
        vote = models.Vote(value=-2, revoke=True)
        self.assertRaises(AssertionError, lambda: vote.action)
        vote.value = -1
        self.assertEqual(vote.action, 'revoked approval')
        vote.value = 1
        self.assertEqual(vote.action, 'revoked disapproval')
        vote.value = 2
        self.assertRaises(AssertionError, lambda: vote.action)


class ImportantHeadingTests(TestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        owork = factories.OriginalWorkFactory(
            segments='h1 h2 p h3 p p p h2 p h4 p p h5 p h6',
            #          1  2 3  4 5 6 7  8
        )
        cls.work = factories.TranslatedWorkFactory(original=owork)
        cls.work.segments.filter(position__lte=2).update(
            content='Translated content',
            progress=TRANSLATION_DONE,
            last_modified=timezone.now(),
        )
        cls.work.segments.filter(position__gt=2, position__lte=5).update(
            progress=IN_REVIEW, last_modified=timezone.now()
        )
        cls.work.segments.filter(position__gt=5, position__lte=7).update(
            progress=REVIEW_DONE, last_modified=timezone.now()
        )
        cls.work.segments.filter(position=8).update(
            progress=TRUSTEE_DONE, last_modified=timezone.now()
        )
        cls.segments = tuple(cls.work.segments.select_related('original'))
        bt = factories.BaseTranslationFactory(language=cls.work.language)
        models.BaseTranslationSegment.objects.bulk_create(
            (models.BaseTranslationSegment(original=s.original, translation=bt))
            for s in cls.segments[:2]
        )

        history_objects = (
            s.add_to_history('+', save=False) for s in cls.segments
        )
        models.TranslatedSegment.history.bulk_create(history_objects)

        cls.data = (
            {
                'segment_id': cls.segments[1].pk,
                'number': None,
                'first_position': None,
                'position': 2,
                'tag': 'h2',
                'classes': [],
                'content': 'Translated content',
                'translation_done': None,
                'review_done': None,
                'trustee_done': None,
                'work_id': cls.work.pk,
                'segments_count': None,
                'date': cls.segments[1].last_modified,
            },
            {
                'segment_id': cls.segments[3].pk,
                'number': 1,
                'first_position': 1,
                'position': 4,
                'tag': 'h3',
                'classes': [],
                'content': cls.segments[3].original.content,
                'translation_done': 7,
                'review_done': 2,
                'trustee_done': 0,
                'work_id': cls.work.pk,
                'segments_count': 7,
                # The most recent date of the chapter
                'date': cls.segments[5].last_modified,
            },
            {
                'segment_id': cls.segments[7].pk,
                'number': 2,
                'first_position': 8,
                'position': 8,
                'tag': 'h2',
                'classes': [],
                'content': cls.segments[7].original.content,
                'translation_done': 1,
                'review_done': 1,
                'trustee_done': 1,
                'work_id': cls.work.pk,
                'segments_count': 8,
                'date': cls.segments[7].last_modified,
            },
        )

    def test_get_headings(self):
        expected = (
            {
                'pk': self.segments[7].pk,
                'position': 8,
                'tag': 'h2',
                'classes': [],
            },
            {
                'pk': self.segments[3].pk,
                'position': 4,
                'tag': 'h3',
                'classes': [],
            },
            {
                'pk': self.segments[1].pk,
                'position': 2,
                'tag': 'h2',
                'classes': [],
            },
            {
                'pk': self.segments[0].pk,
                'position': 1,
                'tag': 'h1',
                'classes': [],
            },
        )
        result = models.ImportantHeading.get_headings(self.work).values(
            *expected[0]
        )
        with self.assertNumQueries(1):
            self.assertEqual(tuple(result), expected)

    def test_insert(self):
        """
        Tests the creation of the headings and their relations.
        """
        models.ImportantHeading.objects.all().delete()
        with self.assertNumQueries(17):
            result = models.ImportantHeading.insert(self.work)
        self.assertEqual(len(result), 3)

        headings = models.ImportantHeading.objects.all()
        self.assertEqual(tuple(headings.values(*self.data[0])), self.data)
        self.assertEqual(
            tuple(headings[1].segments.values_list('position', flat=True)),
            (1, 2, 3, 4, 5, 6, 7),
        )
        self.assertEqual(
            tuple(headings[2].segments.values_list('position', flat=True)),
            (8, 9, 10, 11, 12, 13, 14, 15),
        )
        history = models.TranslatedSegment.history
        history_qs = history.order_by('id').values_list('id', flat=True)
        self.assertEqual(
            tuple(history_qs.filter(chapter=headings[1])),
            tuple(headings[1].segments.values_list('pk', flat=True)),
        )
        self.assertEqual(
            tuple(history_qs.filter(chapter=headings[2])),
            tuple(headings[2].segments.values_list('pk', flat=True)),
        )

        with_pretranslated = models.ImportantHeading.objects.filter(
            pretranslated=2
        ).count()
        self.assertEqual(with_pretranslated, 1)

    def test_update(self):
        segment_1 = self.segments[1]
        segment_1.content = '<b><i>Some HTML <a href="a">included</a></i><b>'
        segment_1.progress = TRUSTEE_DONE
        segment_1.save_without_historical_record()

        with self.assertNumQueries(1):
            result = models.ImportantHeading.update()
        self.assertEqual(result, 3)
        headings = models.ImportantHeading.objects.all()
        expected = deepcopy(self.data)
        expected[0]['content'] = 'Some HTML included'
        expected[0]['date'] = segment_1.last_modified
        expected[1]['review_done'] = 3
        expected[1]['trustee_done'] = 1
        expected[1]['date'] = segment_1.last_modified
        self.assertEqual(tuple(headings.values(*expected[0])), expected)

        segment_8 = self.segments[8]
        segment_8.progress = TRANSLATION_DONE
        segment_8.save_without_historical_record()

        result = models.ImportantHeading.update()
        self.assertEqual(result, 1)

        expected[2]['translation_done'] = 2
        expected[2]['date'] = segment_8.last_modified
        self.assertEqual(tuple(headings.values(*expected[0])), expected)

    @patch('panta.models.ImportantHeading.save')
    def test_update_pretranslated(self, save):
        factories.BaseTranslationSegmentFactory()
        heading = models.ImportantHeading.objects.all()[1]
        pretranslated = heading.update_pretranslated()
        self.assertEqual(pretranslated, 2)
        save.assert_called_once()

        save.reset_mock()
        heading.update_pretranslated()
        save.assert_not_called()


class SimpleImportantHeadingTests(SimpleTestCase):
    maxDiff = None

    def check(self, blueprint_segments, *blueprint_headings, **kwargs):
        blueprint_segments = blueprint_segments.split()
        headings = []
        for i, t in enumerate(blueprint_segments, start=1):
            if t != 'p':
                orig = models.OriginalSegment(content=kwargs.get('content', ''))
                headings.append(
                    models.TranslatedSegment(position=i, tag=t, original=orig)
                )

        expected = []
        for blueprint in blueprint_headings:
            values = (
                eval(v) if v.isdigit() or v == 'None' else v
                for v in blueprint.strip().split()
            )
            expected.append(
                dict(
                    number=next(values),
                    first_position=next(values),
                    position=next(values),
                    tag=next(values),
                    segments_count=next(values),
                )
            )

        with patch('panta.models.ImportantHeading.get_headings') as mock:
            headings.reverse()
            mock.return_value = headings
            work = MagicMock(spec=models.TranslatedWork())
            work.MANUSCRIPT = models.TranslatedWork.MANUSCRIPT
            if 'type' in kwargs:
                work.type = kwargs['type']
            work.segments_count = len(blueprint_segments)
            path = (
                'django.db.models.fields.related_descriptors.router'
                '.allow_relation'
            )
            with patch(path):
                result = models.ImportantHeading.insert(work, save=False)

        self.assertEqual(
            [{k: getattr(h, k) for k in expected[0]} for h in result], expected
        )

    def test_h2_and_h3_only(self):
        self.check(
            'h2 p p p h3 p p h2 p p p p h3 p p p h3',
            # no,  first_pos, pos, tag, count
            ' 1    1          1    h2   4    ',
            ' 2    5          5    h3   3    ',
            ' 3    8          8    h2   5    ',
            ' 4    13         13   h3   4    ',
            ' 5    17         17   h3   1    ',
        )

    def test_h1_and_h3_only(self):
        self.check(
            'h3 p p h1 p p p h3 p p p p p h3 p p h3',
            # no,  first_pos, pos, tag, count
            ' 1    1          1    h3   3    ',
            ' 2    4          4    h1   4    ',
            ' 3    8          8    h3   6    ',
            ' 4    14         14   h3   3    ',
            ' 5    17         17   h3   1    ',
        )

    def test_all_heading_levels_in_a_row(self):
        self.check(
            'h1 h2 h3 h3 h1',
            # no,  first_pos, pos, tag, count
            ' None None       1    h1   None ',
            ' None None       2    h2   None ',
            ' 1    1          3    h3   3    ',
            ' 2    4          4    h3   1    ',
            ' 3    5          5    h1   1    ',
        )

    def test_exclude_the_title(self):
        self.check(
            'h1 p p p h3 p p h2 p p p p h3 p p p h3',
            # no,  first_pos, pos, tag, count
            ' 1    1          5    h3   7    ',
            ' 2    8          8    h2   5    ',
            ' 3    13         13   h3   4    ',
            ' 4    17         17   h3   1    ',
        )

    def test_include_title_if_it_is_only_heading(self):
        self.check(
            'h1 p p p',
            # no,  first_pos, pos, tag, count
            ' 1    1          1    h1   4    ',
        )

    def test_exclude_year_in_manuscripts(self):
        self.check(
            'h2 h1 p p p',
            # no,  first_pos, pos, tag, count
            ' 1    1          2    h1   5    ',
            type=models.TranslatedWork.MANUSCRIPT,
            content='1234',
        )

    def test_include_h1_if_it_is_not_title_only(self):
        self.check(
            'h1 p p p h2 p p p h3 p p p p p h1 p p p h3',
            # no,  first_pos, pos, tag, count
            ' 1    1          1    h1   4    ',
            ' 2    5          5    h2   4    ',
            ' 3    9          9    h3   6    ',
            ' 4    15         15   h1   4    ',
            ' 5    19         19   h3   1    ',
        )

    def test_missing_heading_at_beginning(self):
        """
        Tests that this case is not supported.
        """
        # Reason: We didn't get the first 3 segments.
        self.check(
            'p p p h3 p p p h2 p p p p h3 p p p h3',
            # no,  first_pos, pos, tag, count
            ' 1    4          4    h3   4    ',
            ' 2    8          8    h2   5    ',
            ' 3    13         13   h3   4    ',
            ' 4    17         17   h3   1    ',
        )

    def test_include_previous_headings(self):
        """
        Tests that segments of the previous chapter are included in the current
        chapter if these are a few only and the current heading is lower in
        hierarchy than the last one.
        """
        self.check(
            'h1 p h2 p p h3 p p p h2 h1 h2 p h2 h2 h1 p p h3',
            # Number      1        2     3    4  5         6
            # Position    6       10    12   14 15        19
            # ---------------------------------
            # no,  first_pos, pos, tag, count
            ' None None       1    h1   None ',
            ' None None       3    h2   None ',
            ' 1    1          6    h3   9    ',
            ' 2    10         10   h2   1    ',
            ' None None       11   h1   None ',
            ' 3    11         12   h2   3    ',
            ' 4    14         14   h2   1    ',
            ' 5    15         15   h2   1    ',
            ' None None       16   h1   None ',
            ' 6    16         19   h3   4    ',
        )


class WorkStatisticsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        works = factories.create_work('h2 p h2', 1)
        cls.work = works['translations'][0]
        cls._obj = models.WorkStatistics.objects.get()

        # Headings
        heading_1, heading_2 = models.ImportantHeading.objects.all()
        heading_1.pretranslated = 2
        heading_1.translation_done = 7
        heading_1.review_done = 5
        heading_1.trustee_done = 2
        heading_1.save()
        heading_2.translation_done = 4
        heading_2.review_done = 3
        heading_2.trustee_done = 0
        heading_2.save()
        cls.heading = heading_2

        # History
        segments = tuple(models.TranslatedSegment.objects.all()[:3])
        # Multiple historical segments of different segments
        user = User.objects.first()
        kw = {'history_type': '+', 'history_user': user, 'save': False}
        history_objects = [
            s.add_to_history(relative_id=1, **kw) for s in segments
        ]
        # Multiple historical segments of same segment
        segment = segments[0]
        user = UserFactory()
        for i in range(2, 4):
            segment.add_to_history(
                relative_id=i, history_user=user, add_to=history_objects
            )
        models.TranslatedSegment.history.bulk_create(history_objects)

    def setUp(self):
        self.obj = deepcopy(self._obj)

    def test_insert(self):
        models.WorkStatistics.objects.all().delete()
        obj = models.WorkStatistics.insert(self.work)
        expected = {
            'work_id': self.work.pk,
            'segments': 3,
            'pretranslated_count': 2,
            'translated_count': 0,
            'reviewed_count': 0,
            'authorized_count': 0,
            'pretranslated_percent': 200 / 3,
            'translated_percent': 0,
            'reviewed_percent': 0,
            'authorized_percent': 0,
            'contributors': 0,
            'last_activity': None,
        }
        for k, v in expected.items():
            self.assertEqual(getattr(obj, k), v)

    def test_update(self):
        # First update
        with self.assertNumQueries(1):
            count = models.WorkStatistics.update()
        self.assertEqual(count, 1)
        expected = {
            'segments': 3,
            'translated_count': 11,
            'reviewed_count': 8,
            'authorized_count': 2,
            'translated_percent': Decimal('366.67'),
            'reviewed_percent': Decimal('266.67'),
            'authorized_percent': Decimal('66.67'),
            'contributors': 2,
            'last_activity': self.heading.date,
        }
        self.obj.refresh_from_db()
        for k, v in expected.items():
            self.assertEqual(getattr(self.obj, k), v)

        # Update without changes
        models.ImportantHeading.objects.filter(pk=self.heading.pk).update(
            date=timezone.now() - timedelta(days=1)
        )
        count = models.WorkStatistics.update()
        self.assertEqual(count, 0)

        # Update with changes
        now = timezone.now()
        models.ImportantHeading.objects.filter(translation_done=7).update(
            translation_done=20, review_done=0, trustee_done=0, date=now
        )
        count = models.WorkStatistics.update()
        self.assertEqual(count, 1)
        expected = {
            'translated_count': 24,
            'reviewed_count': 3,
            'authorized_count': 0,
            'translated_percent': 800,
            'reviewed_percent': 100,
            'authorized_percent': 0,
            'contributors': 2,
            'last_activity': now,
        }
        self.obj.refresh_from_db()
        for k, v in expected.items():
            self.assertEqual(getattr(self.obj, k), v)

    @patch('panta.models.ImportantHeading.update_pretranslated')
    def test_update_pretranslated(self, update_pretranslated):
        update_pretranslated.return_value = 2
        self.assertEqual(self.obj.pretranslated_count, 0)
        self.assertEqual(self.obj.pretranslated_percent, 0)
        with self.assertNumQueries(3):
            models.WorkStatistics.update_pretranslated(self.work.language)
        self.obj.refresh_from_db()
        self.assertEqual(self.obj.pretranslated_count, 4)
        self.assertEqual(self.obj.pretranslated_percent, Decimal('133.33'))
