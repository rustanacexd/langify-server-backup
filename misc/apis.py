import logging
from time import sleep
from unittest.mock import Mock

from mailjet_rest import Client as CoreMailjetClient
from oauthlib.oauth2 import Client
from oauthlib.oauth2.rfc6749.parameters import prepare_token_request
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests_oauthlib import OAuth2Session
from rest_framework.exceptions import ValidationError
from slack import WebClient as BaseSlackClient

from django.conf import settings
from django.utils.translation import gettext as _
from langify.routers import in_test_mode

logger = logging.getLogger(__name__)


assert '<' in settings.DEFAULT_FROM_EMAIL, (
    'The DEFAULT_FROM_EMAIL in your config.ini needs a name in the '
    'format "name <something@example.com>".'
)
FROM_NAME, FROM_EMAIL = settings.DEFAULT_FROM_EMAIL.split('<')
FROM_NAME = FROM_NAME.strip()
FROM_EMAIL = FROM_EMAIL.replace('>', '').strip()


class BaseMailingClient:
    def check_response(self, response, expected_status_code=200, data=None):
        """
        Logs errors and raises a ValidationError if the status codes differ.
        """
        if response.status_code != expected_status_code:
            logger.error(
                '{} API didn\'t response with {}.'.format(
                    self.name, expected_status_code
                ),
                extra={
                    'status_code': response.status_code,
                    'body': response.json(),
                    'data': data,
                },
            )
            msg = _('Something went wrong. Please retry later.')
            raise ValidationError(msg)


class MailjetClient(BaseMailingClient):
    """
    A wrapper around Mailjet's client for easier development.
    """

    name = 'Mailjet'
    test_outbox = []

    def __init__(self):
        self.client = CoreMailjetClient(
            auth=(settings.MAILJET_PUBLIC_KEY, settings.MAILJET_SECRET_KEY),
            version='v3.1',
        )
        self.messages = []

    def __getattr__(self, name):
        # TODO delete?
        if settings.DEBUG or settings.TEST or in_test_mode():
            return self.print_call(name)
        return getattr(self.client, name)

    def print_call(self, name):
        def _print_call(*args, **kwargs):
            info = ('Mailjet API call caught:', name, args, kwargs)
            if settings.TEST:
                self.test_outbox.append(info)
            else:
                print(*info)

        return _print_call

    def create_email(self, id, to, subject, context):
        """
        Creates and stores an e-mail to be sent later.
        """
        variables = {
            'link_doesnt_work_note': _(
                'Link doesn\'t work? '
                'Copy the following link to your browser bar:'
            ),
            'germany': _('Germany'),
            'legal_notice': _('Legal notice'),
            'privacy_policy': _('Privacy policy'),
        }
        variables.update(context)
        self.messages.append(
            {
                'From': {'Email': FROM_EMAIL, 'Name': FROM_NAME},
                'To': [{'Email': to}],
                'TemplateID': id,
                'TemplateLanguage': True,
                'Subject': subject,
                'Variables': variables,
                'TemplateErrorReporting': {
                    'Email': settings.DEFAULT_TO_EMAILS[0],
                    'Name': settings.DEFAULT_TO_EMAILS[0],
                },
            }
        )

    def send(self, sandbox=False):
        """
        Sends all stored e-mails and checks the response.

        Retries 4 times in case of errors. Only prints a notification if in
        debugging or E2E testing mode.
        """
        data = {'Messages': self.messages}
        if sandbox:
            data['SandboxMode'] = True
        if settings.DEBUG or settings.TEST or in_test_mode():
            self.print_call('send.create')(data=data)
            response = None
        else:
            attempts = 5
            for i in range(1, attempts + 2):
                try:
                    response = self.client.send.create(data=data)
                    self.check_response(response, data=data)
                except (ValidationError, RequestsConnectionError):
                    if i == attempts:
                        raise
                    sleep(i)
                else:
                    break

        self.messages = []
        return response

    def send_transactional_email(self, id, to, subject, context):
        """
        Sends an email using the mailing with given ID and checks the response.

        Only prints a notification if in debugging or E2E testing mode.
        """
        self.create_email(id, to, subject, context)
        return self.send()


class Newsletter2GoOAuth2Client(Client):
    def prepare_request_body(
        self, username, password, body='', scope=None, **kwargs
    ):
        """
        Sets the Newsletter2Go specific grant type.
        """
        prepared_token = prepare_token_request(
            'https://nl2go.com/jwt',
            body=body,
            username=username,
            password=password,
            scope=scope,
            **kwargs,
        )
        return prepared_token


class Newsletter2GoClient(BaseMailingClient):
    name = 'Newsletter2Go'
    session = None
    production_email_backend = 'django.core.mail.backends.smtp.EmailBackend'
    test_outbox = []

    def __new__(cls):
        """
        Mocks the API in case of E2E tests.
        """
        return in_test_mode() and nl2go_mock or super().__new__(cls)

    def __init__(self):
        """
        Retrieves an access token.
        """
        client_id, client_secret = settings.NL2GO_AUTH_KEY.split(':')
        client = Newsletter2GoOAuth2Client(client_id=client_id)
        self.session = OAuth2Session(client=client)
        self.session.fetch_token(
            token_url=self.url('oauth/v2/token'),
            username=settings.NL2GO_USERNAME,
            password=settings.NL2GO_PASSWORD,
            client_id=client_id,
            client_secret=client_secret,
        )

    def url(self, path):
        return 'https://api.newsletter2go.com/{}'.format(path)

    def make_mailing_transactional(self, id):
        """
        Sets the state of a mailing to active and the type to transaction.
        """
        response = self.session.patch(
            self.url('newsletters/{}'.format(id)),
            json={'state': 'active', 'type': 'transaction'},
        )
        return response

    def send_transactional_email(self, id, to, context):
        """
        Sends an email using the mailing with given ID and checks the response.

        Prints a notification in case no production e-mail backend is used.
        """
        # You have to activate the mailing before you can use it.
        if settings.EMAIL_BACKEND == self.production_email_backend:
            url = self.url('newsletters/{}/send')
            context['email'] = to
            response = self.session.post(
                url.format(id), json={'contexts': [{'recipient': context}]}
            )
            self.check_response(response)
        else:
            info = {'to': to, 'id': id, 'context': context}
            self.test_outbox.append(info)
            print('Sending an e-mail via Newsletter2Go caught:')
            print(info)


nl2go_mock = Mock(spec=Newsletter2GoClient)
nl2go_mock.session.post.return_value = Mock(status_code=201)


class SlackClient(BaseSlackClient):
    """
    Slack client with integrated authentication token.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(settings.SLACK_KEY, *args, **kwargs)

    def to_dev(self, message):
        """
        Sends a message to the "dev" channel of the "mylangify" workspace.
        """
        if settings.DEBUG:
            print('Slack message caught: "{}"'.format(message))
        elif not settings.TEST:
            self.chat_postMessage(channel='dev', text=message)
