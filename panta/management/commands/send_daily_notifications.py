from django.core.management.base import BaseCommand
from panta.utils import notify_users


class Command(BaseCommand):
    help = (
        'Sends an e-mail notification to users who voted on segments that were '
        'edited recently.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--to',
            dest='to',
            help='Sends e-mails not to the user but to the given address',
        )
        parser.add_argument(
            '--sandbox',
            action='store_true',
            dest='sandbox',
            help='Tells Mailjet to not send the e-mails',
        )

    def handle(self, *args, to=None, sandbox=False, **kwargs):
        users, segments = notify_users(to=to, sandbox=sandbox)
        # Inform caller
        self.stdout.write(
            self.style.SUCCESS(
                '{} users about {} changed segments notified'.format(
                    len(users), len(segments)
                )
            )
        )
