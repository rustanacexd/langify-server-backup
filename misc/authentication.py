import requests
from requests.exceptions import HTTPError
from rest_framework.authentication import (
    BaseAuthentication,
    SessionAuthentication as DefaultSessionAuthentication,
    get_authorization_header,
)
from rest_framework.exceptions import AuthenticationFailed

from django.db import transaction
from django.utils import dateformat, timezone
from django.utils.encoding import smart_text
from path.models import OIDCUser, User


class SessionAuthentication(DefaultSessionAuthentication):
    """
    Responds with a '401 Unauthenticated' to unauthenticated users.

    (Instead of a '403 Permission Denied')
    """

    def authenticate_header(self, request):
        return 'Session'


@transaction.atomic
def create_oidc_user_from_claims(claims):
    """ Creates an ``OIDCUser`` instance using the claims extracted from an id_token. """
    sub = claims['sub']
    email = claims['email']
    username = claims['preferred_username']

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        if User.objects.filter(username=username).exists():
            new_username = '_old_' + dateformat.format(timezone.now(), 'U')
            User.objects.filter(username=username).update(username=new_username)
        user = User.objects.create_user(username, email=email)

    if hasattr(user, 'oidc_user'):
        update_oidc_user_from_claims(user.oidc_user, claims)
        oidc_user = user.oidc_user
    else:
        oidc_user = OIDCUser.objects.create(user=user, sub=sub, userinfo=claims)

    return oidc_user


@transaction.atomic
def update_oidc_user_from_claims(oidc_user, claims):
    """ Updates an ``OIDCUser`` instance using the claims extracted from an id_token. """
    oidc_user.userinfo = claims
    oidc_user.save()
    should_save = False
    if not oidc_user.user.first_name:
        oidc_user.user.first_name = claims.get('given_name')
        should_save = True
    if not oidc_user.user.last_name:
        oidc_user.user.last_name = claims.get('family_name')
        should_save = True
    if should_save:
        oidc_user.user.save()


class BearerTokenAuthentication(BaseAuthentication):
    www_authenticate_realm = 'api'

    def authenticate(self, request):
        auth = get_authorization_header(request).split()
        if not auth or smart_text(auth[0].lower()) != 'bearer':
            return

        if len(auth) == 1:
            raise AuthenticationFailed(
                'Invalid authorization header; no bearer token provided'
            )
        elif len(auth) > 2:
            raise AuthenticationFailed(
                'Invalid authorization header; many bearer tokens provided'
            )

        bearer_token = smart_text(auth[1])

        try:
            userinfo_response = requests.get(
                'https://www.adventistpassport.org/userinfo',
                headers={'Authorization': 'Bearer {0}'.format(bearer_token)},
            )
            userinfo_response.raise_for_status()
        except HTTPError:
            raise AuthenticationFailed('Bearer token seems invalid or expired.')
        userinfo_response_data = userinfo_response.json()

        try:
            oidc_user = OIDCUser.objects.select_related('user').get(
                sub=userinfo_response_data.get('sub')
            )
        except OIDCUser.DoesNotExist:
            oidc_user = create_oidc_user_from_claims(userinfo_response_data)
        else:
            update_oidc_user_from_claims(oidc_user, userinfo_response_data)

        return oidc_user.user, bearer_token
