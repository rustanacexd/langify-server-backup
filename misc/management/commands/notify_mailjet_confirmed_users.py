from allauth.account.models import EmailAddress

from django.core.management.base import BaseCommand
from django.utils.translation import gettext as _
from misc.apis import MailjetClient


class Command(BaseCommand):
    """
    Sendmessage to users who have signed up and confirmed already.
    """

    def add_arguments(self, parser):
        parser.add_argument('--target', help='target for testing')

    def handle(self, *args, **options):
        client = MailjetClient()
        subject = _("Please upgrade your Elllen4all account")
        context = {
            'heading': _("We're upgrading!"),
            'introduction': _(
                "Thank-you for being a part of the Ellen4all community."
                " To provide you with new collaboration features and increased"
                " security, we have upgraded our login system."
            ),
            'task': _(
                "To enable your new login, please click on the button below and"
                " Sign Up for your new username and password using this same"
                " email address."
            ),
            'button': _("Authentickate&trade; Me!"),
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
            for email in EmailAddress.objects.filter(verified=True):
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
