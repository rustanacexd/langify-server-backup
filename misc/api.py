from allauth.account.models import EmailAddress, EmailConfirmationHMAC
from docutils.utils.smartquotes import smartchars
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, mixins, permissions, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

# todo: Move CurserCountPagination to the base app
from base.constants import get_languages
from base.serializers import CommentSerializer
from django.conf import settings
from django.contrib.auth.models import Group
from django.core.mail import send_mail
from django.core.management import call_command
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from frontend_urls import DEVELOPER_COMMENTS
from langify.routers import in_test_mode, set_test_mode
from panta.api.pagination import CursorCountPagination
from panta.constants import (
    LANGUAGE_SPECIFIC_REPLACE,
    SMARTY_PANTS_ATTRS,
    SMARTY_PANTS_MAPPING,
)
from path.api.serializers import SendConfirmationSerializer

from . import models
from .apis import Newsletter2GoClient


class PagePermissions(permissions.AllowAny):
    """
    Grants permission if the page is public or the user authenticated.
    """

    def has_object_permission(self, request, view, obj):
        return obj.public or request.user.is_authenticated


class PageSerializer(serializers.ModelSerializer):
    contact_btn = serializers.BooleanField(source='contact_button')

    class Meta:
        model = models.Page
        fields = ('slug', 'contact_btn', 'rendered', 'created', 'last_modified')


class PageViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    retrieve:

    Read

    Retrieves a page. Responses with *403 Permission denied* if the page is not
    public and the user not logged in.
    """

    queryset = models.Page.objects.all()
    serializer_class = PageSerializer
    permission_classes = (PagePermissions,)
    lookup_field = 'slug'

    @action(detail=False, permission_classes=(permissions.IsAuthenticated,))
    def automation(self, request):
        """
        Automation

        Lists automated text processing of all languages.
        """
        replace_text = '{}. `{}` → `{}`'
        heading = '\n## {}\n'
        parts = [
            '# Automated text processing\n',
            'Some characters and strings are automatically replaced by others.',
            'Please let us know if you wish improvements!\n',
            'Note that `␣` stands for a space.',
            heading.format('All languages'),
            '1. spaces at the beginning and end of paragraphs are removed',
            '2. *two spaces* → *one space*',
            heading.format('Some languages'),
            replace_text.format('1', "'", '’') + ' (apostrophe)',
        ]

        for code, name in get_languages(exclude=('en',), additional=False):
            parts.append(
                # Include a destination in the heading
                # see https://stackoverflow.com/a/7335839
                heading.format('{}<a name="{}"></a>'.format(name, code))
            )
            smartquotes = (
                smartchars.quotes.get(SMARTY_PANTS_MAPPING.get(code, code))
                or smartchars.quotes['en']
            )
            number = 1

            for f, r in LANGUAGE_SPECIFIC_REPLACE.get(code, {}).items():
                while ' ' in f:
                    f = f.replace(' ', '␣')
                while ' ' in r:
                    r = r.replace(' ', '␣')
                parts.append(replace_text.format(number, f, r))
                number += 1

            for attr in SMARTY_PANTS_ATTRS.get(code, ''):
                if attr == 'q':
                    parts.extend(
                        (
                            replace_text.format(number, '""', smartquotes[:2]),
                            replace_text.format(
                                number + 1, "''", smartquotes[2:]
                            ),
                        )
                    )
                    number += 1
                elif attr == 'e':
                    parts.append(replace_text.format(number, '...', '…'))
                else:
                    raise NotImplementedError(
                        'Attr. {} is missing documentation'.format(attr)
                    )
                number += 1

        response = Response(
            {
                'slug': 'automation',
                'contact_btn': False,
                'rendered': '\n'.join(parts),
                'created': None,
                'last_modified': None,
            }
        )
        return response


class DeveloperCommentSerializer(CommentSerializer):
    class Meta(CommentSerializer.Meta):
        model = models.DeveloperComment

    def create(self, validated_data):
        """
        Sends a notification e-mail to users in Group "Support".
        """
        instance = super().create(validated_data)
        recipients = Group.objects.filter(name='Support').values_list(
            'user__email', flat=True
        )
        send_mail(
            'New comment on Langify',
            '{}\n\nhttps://www.ellen4all.org/{}'.format(
                instance.content, DEVELOPER_COMMENTS
            ),
            settings.DEFAULT_FROM_EMAIL,
            recipients,
            fail_silently=True,
        )
        return instance


class IsOwnerOrReadOnlyPermissions(permissions.IsAuthenticated):
    """
    Object-level permission to only allow owners of an object to edit it.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user == request.user


class DeveloperCommentViewSet(viewsets.ModelViewSet):
    """
    API endpoint for comments.

    create: Creates comment and sends notification to developers.
    """

    queryset = models.DeveloperComment.objects.all()
    serializer_class = DeveloperCommentSerializer
    permission_classes = (IsOwnerOrReadOnlyPermissions,)
    pagination_class = CursorCountPagination
    ordering = ('-created',)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class LanguageNewsletterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    name = serializers.CharField(required=False)
    language = serializers.CharField(required=False)


@method_decorator(
    name='post',
    decorator=swagger_auto_schema(
        security=[],
        operation_id='Newsletter subscribe',
        responses={201: 'Created', 400: '*Validation errors*'},
    ),
)
class LanguageNewsletterView(generics.CreateAPIView):
    """
    Sends a double-opt in e-mail and adds the address to the newsletter list.
    """

    serializer_class = LanguageNewsletterSerializer
    permission_classes = (permissions.AllowAny,)

    def perform_create(self, serializer):
        payload = serializer.validated_data.copy()
        payload['first_name'] = payload.pop('name', '')
        client = Newsletter2GoClient()
        response = client.session.post(
            client.url('forms/submit/3x7ujs37-cd3sza7r-13ie'),
            json={'recipient': payload},
        )
        try:
            client.check_response(response, 201, data=serializer.validated_data)
        except ValidationError:
            if response.status_code == 200:
                result = response.json()['value'][0]['result']
                if result['error']['recipients']['duplicate']:
                    msg = _('Your e-mail address is registered already.')
                    raise ValidationError(msg)
            elif response.status_code == 400:
                raise ValidationError(response.json())
            raise


class E2ETestsSerializer(serializers.Serializer):
    test = serializers.BooleanField()


class KeySerializer(serializers.Serializer):
    key = serializers.CharField()


class E2ETestsViewSet(viewsets.GenericViewSet):
    """
    Endpoint for end-to-end testing.
    """

    serializer_class = E2ETestsSerializer
    permission_classes = (permissions.AllowAny,)
    pagination_class = None

    @swagger_auto_schema(security=[], responses={200: E2ETestsSerializer()})
    def create(self, request, *args, **kwargs):
        """
        Switch

        Turns end-to-end testing mode on or off.

        #### Notes

        - Requires `DEBUG: true` in *config.ini*.
        - Flushes the E2E tests database when POSTing `false`.
        - To migrate, always run:
          `manage.py migrate --database default --database e2e_tests`
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        test_mode = serializer.validated_data['test']
        set_test_mode(test_mode)
        if not test_mode:
            call_command(
                'flush', interactive=False, database='e2e_tests', verbosity=0
            )
        return Response(serializer.data)

    @swagger_auto_schema(security=[], responses={200: E2ETestsSerializer()})
    def list(self, request):
        """
        Status

        Retrieves the current status whether the backend is in end-to-end
        testing mode or not.
        """
        return Response({'test': in_test_mode()})

    @swagger_auto_schema(
        security=[],
        responses={
            200: KeySerializer(),
            400: '*Validation errors*',
            404: 'Not found',
        },
    )
    @action(
        detail=False,
        methods=['post'],
        url_path='email-confirmation-key',
        queryset=EmailAddress.objects.all(),
        serializer_class=SendConfirmationSerializer,
    )
    def email_confirmation_key(self, request):
        """
        E-mail confirmation

        Retrieves a valid key for e-mail confirmation.

        Requires `DEBUG: true` in *config.ini*.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = get_object_or_404(
            self.get_queryset(), email=serializer.validated_data['email']
        )
        return Response({'key': EmailConfirmationHMAC(email).key})
