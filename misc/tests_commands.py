from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.test import TestCase, tag  # noqa: F401
from django.utils import timezone
from misc.factories import DeveloperCommentFactory
from panta.factories import SegmentCommentFactory


class DeleteCommentsTests(TestCase):
    def get_regex(self, count):
        dev = 'misc.DeveloperComment'
        segment = 'panta.SegmentComment'
        msg = "Deleted: {{'{model_1}': {count}, '{model_2}': {count}}}\n"
        return '({}|{})'.format(
            msg.format(model_1=dev, model_2=segment, count=count),
            msg.format(model_1=segment, model_2=dev, count=count),
        )

    @classmethod
    def setUpTestData(cls):
        cls.dev_comment = DeveloperCommentFactory()
        cls.seg_comment = SegmentCommentFactory()

    def test_delete_marked_comments(self):
        self.dev_comment.to_delete = timezone.now()
        self.dev_comment.save()
        self.seg_comment.to_delete = timezone.now()
        self.seg_comment.save()
        out = StringIO()
        call_command('delete_comments', '--no-color', stdout=out)
        self.assertRegex(out.getvalue(), self.get_regex(count=1))

    def test_keep_comments_not_marked(self):
        out = StringIO()
        call_command('delete_comments', '--no-color', stdout=out)
        self.assertRegex(out.getvalue(), self.get_regex(count=0))

    def test_keep_comments_recently_marked(self):
        self.dev_comment.to_delete = timezone.now() + timedelta(seconds=2)
        self.dev_comment.save()
        self.seg_comment.to_delete = timezone.now() + timedelta(minutes=1)
        self.seg_comment.save()
        out = StringIO()
        call_command('delete_comments', '--no-color', stdout=out)
        self.assertRegex(out.getvalue(), self.get_regex(count=0))
