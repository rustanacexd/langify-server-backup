from allauth.socialaccount.providers.base import ProviderAccount
from allauth.socialaccount.providers.oauth2.provider import OAuth2Provider

from . import constants


class WhiteEstateAccount(ProviderAccount):
    def get_profile_url(self):
        return constants.USER_PROFILE_URL

    def __str__(self):
        data = self.account.extra_data
        return data.get('name') or data.get('username') or super().__str__()


class WhiteEstateProvider(OAuth2Provider):
    id = 'white-estate'
    name = 'Ellen G. White Estate'
    account_class = WhiteEstateAccount

    def get_default_scope(self):
        return ['user_info']

    def extract_uid(self, data):
        return str(data['id'])

    def extract_common_fields(self, data):
        return dict(
            username=data.get('username'),
            name=data.get('name'),
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            email=data.get('email'),
        )


provider_classes = [WhiteEstateProvider]
