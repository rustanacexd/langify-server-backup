from allauth.account.models import EmailAddress

from django.core.management.base import BaseCommand
from django.utils.translation import gettext as _
from misc.apis import MailjetClient


class Command(BaseCommand):
    """
    Send a belated welcome message to users who have signed up while Mailjet was down.
    """

    def add_arguments(self, parser):
        parser.add_argument('--target', help='target for testing')

    def handle(self, *args, **options):
        client = MailjetClient()
        subject = _(
            "You're approved! Here's how to activate your Ellen4all account"
        )
        context = {
            'heading': _("You're approved"),
            'introduction': _(
                "Thanks for volunteering to contribute to the translation of"
                " Ellen G. White's writings!"
            ),
            'task': _(
                "Your request has been approved, and you can now create an"
                " account using the button below: "
            ),
            'button': _("Let's Go!"),
            'link': 'https://www.ellen4all.org/new-signup/',
            'ignore_note': _(
                "If the above button doesn't work for you, please go to:"
            ),
        }

        if options['target']:
            client.send_transactional_email(
                533_481, options['target'], subject, context
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfuly emailed #{options["target"]} in mailjet'
                )
            )
        else:
            for email in EmailAddress.objects.filter(verified=False):
                client.send_transactional_email(
                    533_481, email.email, subject, context
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfuly emailed #{email.email} in mailjet'
                    )
                )

            self.stdout.write(
                self.style.SUCCESS('Successfully queued all emails in mailjet')
            )
