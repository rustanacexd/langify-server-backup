import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone
from panta.management import Segments
from panta.models import TranslatedSegment


class Command(BaseCommand):
    help = 'Release locked segments after 3 min inactivity and update history.'

    def handle(self, *args, **kwargs):
        # TODO Optimize: use cache
        segments = TranslatedSegment.objects.filter(
            last_modified__lte=timezone.now() - datetime.timedelta(minutes=3),
            locked_by_id__isnull=False,
        )
        result = Segments().conclude(segments)

        # Inform caller
        msg = (
            'Released {unlocked} locked segment(s), created {new} and '
            'updated {updated} historical records'
        )
        self.stdout.write(msg.format_map(result))
