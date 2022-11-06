from allauth.account.adapter import DefaultAccountAdapter

from django.utils.translation import gettext as _
from misc.apis import MailjetClient


class RestAdapter(DefaultAccountAdapter):
    def send_mail(self, template_prefix, email, context):
        """
        Sends e-mails as transactional mailings with Mailjet.
        """
        client = MailjetClient()
        if 'email_confirmation' in template_prefix:
            subject = _('Confirm your e-mail address')
            context = {
                'heading': _('Please confirm your e-mail address'),
                'introduction': _(
                    'You are one final step from using the e-mail address for '
                    'your account at ellen4all.org.'
                ),
                'task': _('Please confirm it by clicking on the green button.'),
                'button': _('Confirm'),
                'link': context['activate_url'],
                'ignore_note': _(
                    'In case you didn\'t provide this e-mail address on '
                    'ellen4all.org you can ignore this e-mail.'
                ),
            }
            client.send_transactional_email(533481, email, subject, context)
        else:
            msg = 'No mailing for {} implemented.'.format(template_prefix)
            raise NotImplementedError(msg)

    def respond_email_verification_sent(self, request, user):
        """
        We don't need this redirect.
        """
        pass
