import requests
from allauth.socialaccount import app_settings
from allauth.socialaccount.models import SocialLogin
from allauth.socialaccount.providers.base import AuthAction
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from allauth.socialaccount.providers.oauth2.views import (
    OAuth2Adapter,
    OAuth2LoginView,
)
from allauth.utils import build_absolute_uri
from drf_yasg.utils import swagger_auto_schema
from rest_auth.registration.serializers import SocialLoginSerializer
from rest_auth.registration.views import SocialConnectView, SocialLoginView
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.generic import TemplateView
from panta.models import OriginalWork
from path.api.serializers import AuthUserSerializer
from path.api.views import UserResponseMixin

from . import constants, models
from .provider import WhiteEstateProvider


class WhiteEstateAdapter(OAuth2Adapter):
    provider_id = WhiteEstateProvider.id
    settings = app_settings.PROVIDERS.get(provider_id, {})

    access_token_url = constants.TOKEN_URL
    authorize_url = constants.AUTHORIZE_URL

    def complete_login(self, request, app, token, **kwargs):
        params = {'access_token': token.token}
        resp = requests.get(constants.USER_PROFILE_URL, params=params)
        extra_data = resp.json()
        extra_data.pop('ns')
        return self.get_provider().sociallogin_from_response(
            request, extra_data
        )

    def get_callback_url(self, request, app):
        if settings.DEBUG:
            protocol = 'http'
        else:
            protocol = self.redirect_uri_protocol
        return build_absolute_uri(request, constants.CALLBACK_URL, protocol)


class CallbackSerializer(SocialLoginSerializer):
    state = serializers.CharField()

    def validate_state(self, value):
        """
        Checks that the state is equal to the one stored in the session.
        """
        try:
            SocialLogin.verify_and_unstash_state(self.context['request'], value)
        except PermissionDenied:
            raise ValidationError(_('State did not match.'))
        return value


class CallbackMixin:
    adapter_class = WhiteEstateAdapter
    client_class = OAuth2Client
    serializer_class = CallbackSerializer

    @property
    def callback_url(self):
        url = self.adapter_class(self.request).get_callback_url(
            self.request, None
        )
        return url


@method_decorator(
    name='post',
    decorator=swagger_auto_schema(
        security=[],
        responses={
            200: AuthUserSerializer(),
            400: '*Validation errors*',
            404: 'Not found',
        },
    ),
)
class CallbackLogin(CallbackMixin, UserResponseMixin, SocialLoginView):
    """
    White Estate callback login

    Logs the user in with the providers data.

    Creates a new user account if it doesn't exist yet.
    """


@method_decorator(
    name='post',
    decorator=swagger_auto_schema(
        responses={200: 'Connection completed.', 400: '*Validaton errors*'}
    ),
)
class CallbackConnect(CallbackMixin, SocialConnectView):
    """
    White Estate callback connect

    Connects a provider's user account to the currently logged in user.
    """

    def get_response(self):
        return Response({'detail': _('Connection completed.')})


class URLSerializer(serializers.Serializer):
    url = serializers.URLField()


class AuthServerURL(APIView):
    adapter_class = WhiteEstateAdapter
    permission_classes = (AllowAny,)

    @swagger_auto_schema(security=[], responses={200: URLSerializer()})
    def post(self, request, format=None):
        """
        White Estate auth server

        Generates the URL to the login page of provider's authentication
        server.
        """
        # You should have CSRF protection enabled, see
        # https://security.stackexchange.com/a/104390 (point 3)
        adapter = self.adapter_class(request)
        provider = adapter.get_provider()
        app = provider.get_app(request)
        view = OAuth2LoginView()
        view.request = request
        view.adapter = adapter
        client = view.get_client(request, app)
        action = AuthAction.AUTHENTICATE
        auth_url = adapter.authorize_url
        auth_params = provider.get_auth_params(request, action)
        client.state = SocialLogin.stash_state(request)
        url = client.get_redirect_url(auth_url, auth_params)
        return Response({'url': url})


class EqualSentencesView(LoginRequiredMixin, TemplateView):
    """
    Statistics about how many works have equal sentences in other works.
    """

    template_name = 'white_estate/equal_sentences.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        works = []
        for work in OriginalWork.objects.all():
            sentences = models.Sentence.objects.filter(
                segments__work=work
            ).prefetch_related('segments__work')
            similar_works = {}
            sentences_count = 0
            for sentence in sentences:
                sentences_count += 1
                if len(sentence.segments.all()) == 1:
                    if work.title in similar_works:
                        similar_works[work.title] += 1
                    else:
                        similar_works[work.title] = 1
                    continue
                for segment in sentence.segments.all():
                    if segment.work == work:
                        continue
                    if segment.work.title in similar_works:
                        similar_works[segment.work.title] += 1
                    else:
                        similar_works[segment.work.title] = 1

            work.sentences = sentences_count
            works.append((work, similar_works))

        context['works'] = works
        return context
