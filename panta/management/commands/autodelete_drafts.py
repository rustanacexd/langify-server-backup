import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone
from panta.models import SegmentDraft


class Command(BaseCommand):
    help = 'Delete drafts which are older than 30 days once a day.'

    def handle(self, *args, **kwargs):
        _30_days_ago = timezone.now() - datetime.timedelta(30)
        obsolete = SegmentDraft.objects.filter(created__lte=_30_days_ago)
        # Invalid drafts will be deleted without commit after 30 days!
        deleted = obsolete.delete()

        # Inform caller
        if deleted[0]:
            self.stdout.write(
                self.style.SUCCESS('Deleted {} drafts.'.format(deleted[0]))
            )
        else:
            self.stdout.write('No drafts to delete.')
