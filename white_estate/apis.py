from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session

from django.conf import settings


class EGWWritingsClient:
    api_url = 'https://a.egwwritings.org/'
    folders = {}

    def __init__(self):
        self.client = OAuth2Session(
            client=BackendApplicationClient(client_id=settings.EGW_CLIENT_ID)
        )
        self.client.fetch_token(
            token_url='https://cpanel.egwwritings.org/o/token/',
            client_id=settings.EGW_CLIENT_ID,
            client_secret=settings.EGW_CLIENT_SECRET,
            scope='writings search',
        )

    def get(self, url, json=True, **kwargs):
        """
        Retrieves data for given URL and keyword arguments.
        """
        if not url.startswith(self.api_url):
            url = '{}{}'.format(self.api_url, url.lstrip('/'))
        response = self.client.get(url, params=kwargs)
        assert response.status_code == 200, (
            f'Response was {response.status_code} instead of 200.\n'
            f'URL: {response.url}\n'
            f'Text: {response.text}'
        )
        if json:
            return response.json()
        return response.content

    def get_id_for_book(self, query, language='en'):
        received = self.get('search/suggestions/', query=query, lang=[language])
        assert len(received) == 1
        return received[0]['para_id'].split('.')[0]

    def get_folders(self, language='en'):
        if not self.folders:
            url = f'content/languages/{language}/folders'
            self.folders = self.get(url)
        return self.folders
