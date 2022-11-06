import json
import sys
from copy import deepcopy
from datetime import date, datetime, time, timedelta
from io import StringIO
from random import choice
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import (  # noqa: F401
    SimpleTestCase,
    TestCase,
    override_settings,
    tag,
)
from django.utils import timezone
from langify.celery import app
from misc.apis import FROM_EMAIL, FROM_NAME, MailjetClient
from panta import factories, models
from panta.constants import (
    BLANK,
    IN_REVIEW,
    IN_TRANSLATION,
    REVIEW_DONE,
    TRANSLATION_DONE,
    TRUSTEE_DONE,
)
from panta.utils import (
    add_segments_to_deepl_queue,
    assign_progress,
    get_system_user,
    notify_users,
    sanitize_content,
    sanitize_content_of_queryset,
)
from path.factories import UserFactory

User = get_user_model()


class GetSystemUserTests(TestCase):
    def test_username_not_in_list(self):
        with self.assertRaises(AssertionError):
            get_system_user('Oliver')

    def test_success(self):
        user = get_system_user('AI')
        self.assertEqual(user.username, 'AI')
        self.assertEqual(user.email, 'ai@example.com')

    def test_username_is_used_by_somebody_else(self):
        user = get_system_user('Automation')
        user.email = 'test@example.com'
        user.save_without_historical_record()
        msg = 'Somebody else has registered with the username "Automation"!'
        with self.assertRaisesMessage(AssertionError, msg):
            get_system_user('Automation')


class AddSegmentsToDeepLQueueTests(SimpleTestCase):
    key = 'next_deepl_segments'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.redis = app.broker_connection().default_channel.client

    def tearDown(self):
        self.redis.delete(self.key)

    def test(self):
        work = MagicMock(pk=1, spec=models.OriginalWork)
        work.segments.values_list.return_value = [1, 2, 3]
        result = add_segments_to_deepl_queue(work, 'x')
        self.assertEqual(result, {'added': 3, 'total': 3})
        result = self.redis.lrange(self.key, 0, -1)
        expected = [
            {'work': 1, 'language': 'x', 'position': 1},
            {'work': 1, 'language': 'x', 'position': 2},
            {'work': 1, 'language': 'x', 'position': 3},
        ]
        self.assertEqual([json.loads(i) for i in result], expected)


class NotifyUsersTests(TestCase):
    maxDiff = None
    outbox = MailjetClient.test_outbox

    @classmethod
    def setUpTestData(cls):
        if sys.version_info[:3] < (3, 6, 0):
            today = datetime.combine(date.today(), time.min)
            yesterday = datetime.combine(
                date.today() - timedelta(days=1), choice((time.min, time.max))
            )
            day_before_yesterday = datetime.combine(
                date.today() - timedelta(days=2), time.max
            )
        else:
            today = datetime.combine(
                date.today(), time.min, tzinfo=timezone.utc
            )
            yesterday = datetime.combine(
                date.today() - timedelta(days=1),
                choice((time.min, time.max)),
                tzinfo=timezone.utc,
            )
            day_before_yesterday = datetime.combine(
                date.today() - timedelta(days=2), time.max, tzinfo=timezone.utc
            )

        segments = 'p h1 p p h2 p p p h3 p p h4 p p h2 p p p h2 p p p p p p p p'
        #           1         5         10          15         20        25
        works = factories.create_work(segments, 2, completeness=(90, 100))
        translation_1, translation_2 = works['translations']
        user_1, user_2 = UserFactory.create_batch(2)
        segments = tuple(translation_1.segments.all().select_related('work'))
        for segment in segments:
            if segment.position <= 5:
                segment._history_date = yesterday
            elif segment.position <= 10:
                segment._history_date = today
            elif segment.position <= 15:
                segment._history_date = day_before_yesterday
            else:
                break
            segment.save()
            vote = factories.VoteFactory(user=user_1)
            vote.historical_segments.add(segment.history.earliest())
            if segment.position == 3:
                vote = factories.VoteFactory(user=user_2)
                vote.historical_segments.add(segment.history.earliest())
            if segment.position == 4:
                factories.VoteFactory(user=user_2, segment=segment)
            if segment.position == 5:
                factories.VoteFactory(user=user_1, segment=segment)

        segment = translation_2.segments.last()
        segment._history_date = yesterday
        segment.save()
        vote = factories.VoteFactory(user=user_1)
        vote.historical_segments.add(segment.history.earliest())

        cls.user_1 = user_1
        cls.user_2 = user_2
        cls.translation_1 = translation_1
        cls.translation_2 = translation_2
        cls.t1_segments = segments
        cls.t2_segment = segment

    def setUp(self):
        self.outbox.clear()

    def get_segment(self, segment, chapter):
        if segment.content:
            diff = '<p>{}</p>\n'.format(segment.content)
        else:
            diff = '<p/>\n'
        segment = {
            'button': 'Open chapter {}'.format(chapter),
            'diff': diff,
            'reference': segment.reference,
            'url': (
                f'https://www.ellen4all.org/editor/{segment.work.language}/'
                f'{segment.work.pk}/chapter/{chapter}/paragraph/1/'
            ),
        }
        return segment

    def get_message(self, user, works):
        message = {
            'From': {'Email': FROM_EMAIL, 'Name': FROM_NAME},
            'Subject': 'Edits of translations you voted for',
            'TemplateErrorReporting': {
                'Email': 'admin@example.com',
                'Name': 'admin@example.com',
            },
            'TemplateID': 640_058,
            'TemplateLanguage': True,
            'To': [{'Email': user.email}],
            'Variables': {
                'germany': 'Germany',
                'heading': 'List of edited texts',
                'introduction': (
                    'We are excited that people like you were diligent and '
                    'reviewed our translations! Below you find the texts that '
                    'were edited recently. Help us by coming over and vote for '
                    'the edits!'
                ),
                'legal_notice': 'Legal notice',
                'link_doesnt_work_note': (
                    'Link doesn\'t work? Copy the following link to your '
                    'browser bar:'
                ),
                'privacy_policy': 'Privacy policy',
                'unsubscribe_note': (
                    'You received this e-mail because you voted for '
                    'translations on Ellen4all.org. Therefore, we assume you '
                    'want to get this notification. If you do not want this '
                    'type of e-mail notification anymore, please reply to this '
                    'message with a short note saying so.'
                ),
                'works': works,
            },
        }
        return message

    @override_settings(DEFAULT_TO_EMAILS=('admin@example.com',))
    def test(self):
        result = notify_users(sandbox=True)
        self.assertEqual(set(result[0]), {self.user_1, self.user_2})
        self.assertEqual(
            tuple(result[1]), self.t1_segments[:4] + (self.t2_segment,)
        )
        message_1 = self.get_message(
            self.user_1,
            [
                {
                    'segments': [
                        self.get_segment(s, 1) for s in self.t1_segments[:4]
                    ],
                    'title': self.translation_1.title,
                },
                {
                    'segments': [self.get_segment(self.t2_segment, 4)],
                    'title': self.translation_2.title,
                },
            ],
        )
        message_2 = self.get_message(
            self.user_2,
            [
                {
                    'segments': [self.get_segment(self.t1_segments[2], 1)],
                    'title': self.translation_1.title,
                }
            ],
        )
        email = self.outbox[0][3]['data']['Messages'][0]['To'][0]['Email']
        if email == self.user_1.email:
            messages = [message_1, message_2]
        else:
            messages = [message_2, message_1]
        self.assertEqual(
            self.outbox[0][3]['data'],
            {'Messages': messages, 'SandboxMode': True},
        )

    def test_only_subscribed_users_are_included(self):
        User.objects.filter(pk=self.user_1.pk).update(subscribed_edits=False)
        result = notify_users(sandbox=True)
        self.assertEqual(set(result[0]), {self.user_2})
        self.assertEqual(tuple(result[1]), self.t1_segments[2:3])
        self.assertEqual(len(self.outbox[0][3]['data']['Messages']), 1)

    def test_to(self):
        notify_users(to='me@example.com', sandbox=True)
        self.assertEqual(
            self.outbox[0][3]['data']['Messages'][0]['To'][0]['Email'],
            'me@example.com',
        )

    # TODO test diff


class SanitizeContentTests(SimpleTestCase):

    # HTML

    def test_nbsp2space(self):
        self.assertEqual(
            sanitize_content('&nbsp;I&nbsp;want a space at the end!&nbsp;'),
            'I want a space at the end!',
        )

    def test_b2strong(self):
        self.assertEqual(
            sanitize_content('hello <b>Lini</b>'), 'hello <strong>Lini</strong>'
        )

    def test_i2em(self):
        self.assertEqual(sanitize_content('<i>italic</i>'), '<em>italic</em>')

    def test_p_is_removed(self):
        self.assertEqual(
            sanitize_content('<p>hello</p> Michael'), 'hello Michael'
        )

    def test_div_is_removed(self):
        self.assertEqual(sanitize_content('<div>bye</div>'), 'bye')

    def test_br_is_removed_when_empty(self):
        self.assertEqual(sanitize_content('<br>'), '')
        self.assertEqual(sanitize_content('<br/>'), '')

    def test_br_is_kept_when_not_empty(self):
        self.assertEqual(sanitize_content('Headline<br>'), 'Headline<br>')
        self.assertEqual(sanitize_content('Headline<br/>'), 'Headline<br/>')

    # Text

    def test_de_dash2ndash(self):
        self.assertEqual(sanitize_content('T- and rs - ', 'de'), 'T- and rs –')

    def test_de_ellipsis(self):
        self.assertEqual(sanitize_content('. ......... .', 'de'), '. … .')
        self.assertEqual(sanitize_content('.… ….', 'de'), '… …')

    def test_strip(self):
        self.assertEqual(sanitize_content('  word '), 'word')

    def test_successive_spaces_are_removed(self):
        self.assertEqual(sanitize_content('we  want   you'), 'we want you')

    def test_typographic_quotes_de(self):
        self.assertEqual(sanitize_content('"M \'m\' m"', 'de'), '„M ‚m‘ m“')

    def test_apostrophe_de(self):
        # todo: It should result in "Lukas’ d’L ’07" (i.e. 3 vs. 1 apostrophe)
        self.assertEqual(
            sanitize_content('Lukas\' d\'L \'07', 'de'), 'Lukas‘ d’L ‚07'
        )

    def test_a_lot(self):
        self.assertEqual(
            sanitize_content(
                ' hi<b>-<i>"L....i"</i></b><div> </div>.… - ', 'de'
            ),
            'hi<strong>-<em>„L…i“</em></strong> … –',
        )


@patch('sys.stdout', new_callable=StringIO)
class SanitizeContentOfQuerysetTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        factories.create_work(2, 1, ('de',), (0, 0))
        cls.segments = models.TranslatedSegment.objects.all()
        segment = cls.segments[0]
        segment.content = 'Test ......... '
        segment.save_without_historical_record()
        cls._segment = segment

    def setUp(self):
        self.segment = deepcopy(self._segment)

    def test_content_is_sanitized(self, stdout):
        sanitize_content_of_queryset(self.segments)
        self.segment.refresh_from_db()
        self.assertEqual(self.segment.content, 'Test …')
        self.assertIn('Sanitized', stdout.getvalue())

    def test_history_has_correct_information(self, stdout):
        sanitize_content_of_queryset(self.segments)
        self.assertEqual(self.segment.history.count(), 1)
        record = self.segment.history.select_related('history_user').latest()
        self.assertEqual(record.history_user.username, 'Automation')
        self.assertEqual(record.history_change_reason, 'Automated edit')
        self.assertEqual(models.TranslatedSegment.history.count(), 1)

    def test_locked_segments_are_skipped(self, stdout):
        user = UserFactory()
        self.segment.locked_by = user
        self.segment.save_without_historical_record()
        sanitize_content_of_queryset(self.segments)
        self.assertFalse(models.TranslatedSegment.history.exists())
        self.segment.refresh_from_db()
        self.assertEqual(self.segment.content, 'Test ......... ')
        self.assertEqual(self.segment.locked_by_id, user.pk)
        output = stdout.getvalue()
        self.assertIn('Skipped', output)
        self.assertNotIn('Sanitized', output)

    def test_only_modified_segments_are_saved(self, stdout):
        self.assertFalse(models.TranslatedSegment.history.exists())
        with self.assertNumQueries(13):
            sanitize_content_of_queryset(self.segments)
        self.assertEqual(models.TranslatedSegment.history.count(), 1)
        with self.assertNumQueries(4):
            sanitize_content_of_queryset(self.segments)


class AssignProgressTests(TestCase):
    def test(self):
        works = factories.create_work(
            segments=12,
            translations=1,
            completeness=(0, 0),
            additional_languages=False,
        )
        segments = works['translations'][0].segments.all()
        # In translation
        segments.filter(position__in=(5, 6, 7)).update(content='x')
        # Translation done
        segments.filter(position__in=(8, 9)).update(content=500 * 'y')
        # In review
        segment = segments.get(position=10)
        segment.content = 'z'
        segment.save_without_historical_record()
        factories.VoteFactory(segment=segment, role='reviewer', value=1)
        # Review done
        segment = segments.get(position=11)
        segment.content = 's'
        segment.save_without_historical_record()
        factories.VoteFactory(segment=segment, role='reviewer', value=3)
        # Trustee done
        segment = segments.get(position=12)
        segment.content = 't'
        segment.save_without_historical_record()
        factories.VoteFactory(segment=segment, role='trustee', value=1)

        with self.assertNumQueries(7):
            updated = assign_progress(segments)
        self.assertEqual(updated, 12)

        with self.assertNumQueries(2):
            updated = assign_progress(segments.filter(position__lte=4))
        self.assertEqual(updated, 4)

        expected = (
            BLANK,
            BLANK,
            BLANK,
            BLANK,
            IN_TRANSLATION,
            IN_TRANSLATION,
            IN_TRANSLATION,
            TRANSLATION_DONE,
            TRANSLATION_DONE,
            IN_REVIEW,
            REVIEW_DONE,
            TRUSTEE_DONE,
        )
        self.assertEqual(
            tuple(segments.values_list('progress', flat=True)), expected
        )
