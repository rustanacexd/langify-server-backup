from unittest.mock import patch

from django.test import TestCase, tag  # noqa: F401
from panta import factories


class SignalTests(TestCase):
    @patch('panta.signals.add_task_for_comments_deletion')
    def test_schedule_segment_comment_deletion(self, mocked):
        factories.SegmentCommentFactory()
        mocked.assert_called_once()
