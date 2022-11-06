from django.core.management.base import BaseCommand
from panta.models import ImportantHeading, WorkStatistics


class Command(BaseCommand):
    help = (
        'Updates the headings table used for the table of contents and the '
        'statistics table of translated works.'
    )

    def handle(self, *args, **kwargs):
        headings = ImportantHeading.update()
        statistics = WorkStatistics.update()
        msg = f'Updated {headings} headings and {statistics} statistics.'
        self.stdout.write(self.style.SUCCESS(msg))
