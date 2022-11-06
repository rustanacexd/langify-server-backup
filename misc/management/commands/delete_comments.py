from django.core.management.base import BaseCommand
from django.utils import timezone
from misc.models import DeveloperComment
from panta.models import SegmentComment


class Command(BaseCommand):
    """
    Deletes comments with an expired TTL. Fallback for the Celery tasks.
    """

    help = 'Delete comments scheduled for deletion.'

    def handle(self, *args, **kwargs):
        now = timezone.now()
        x, count = DeveloperComment.objects.filter(to_delete__lte=now).delete()
        dev = SegmentComment.objects.filter(to_delete__lte=now).delete()
        count.update(dev[1])
        # Inform caller
        self.stdout.write(self.style.SUCCESS('Deleted: {}'.format(count)))
