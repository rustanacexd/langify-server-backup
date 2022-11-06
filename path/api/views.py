import datetime
import os
import zipfile

from allauth.account.adapter import get_adapter
from allauth.account.models import EmailAddress
from allauth.account.utils import user_pk_to_url_str
from djangorestframework_camel_case.parser import CamelCaseJSONParser
from drf_yasg.utils import swagger_auto_schema
from rest_auth.registration.views import (
    RegisterView as BaseRegisterView,
    VerifyEmailView,
)
from rest_auth.views import (
    LoginView,
    LogoutView as RestAuthLogoutView,
    PasswordResetView,
)
from rest_framework import (
    exceptions,
    generics,
    mixins,
    parsers,
    permissions,
    status,
    viewsets,
)
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.serializers import ValidationError
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView
from sendfile import sendfile

from django.conf import settings
from django.contrib.auth import logout
from django.core.mail import send_mail
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from panta.api.permissions import FlagUserPermissions
from path import models

from . import serializers


class UnderscoreBeforeNumberParser(CamelCaseJSONParser):
    json_underscoreize = {'no_undersore_before_numer': True}


class AuthRateThrottle(UserRateThrottle):
    scope = 'auth'


@method_decorator(
    name='post',
    decorator=swagger_auto_schema(
        security=[],
        responses={
            200: 'Verification e-mail sent.',
            400: '*Validation errors*',
            429: '*Too many requests*',
        },
    ),
)
class RegisterView(BaseRegisterView):
    """
    Register

    Join the community.

    Max. 100 requests per hour allowed (in combination with some other
    endpoints).
    """

    throttle_classes = (AuthRateThrottle,)


@method_decorator(
    name='patch',
    decorator=swagger_auto_schema(
        request_body=serializers.UserRequestSerializer,
        responses={200: serializers.UserResponseSerializer},
    ),
)
@method_decorator(
    name='put',
    decorator=swagger_auto_schema(
        request_body=serializers.UserRequestSerializer,
        responses={200: serializers.UserResponseSerializer},
    ),
)
class OwnUserView(generics.RetrieveUpdateDestroyAPIView):
    """
    API endpoint for users.

    get:
    Retrieve

    Retrieves information of the logged in user.

    put:
    Update

    For `password` and `isActive` see "PATCH".

    patch:
    Update

    Responses with the user object or a restricted processing message.

    The password is required if you set `isActive` to false. This restricts
    processing with immediate effect: The user gets logged out and can't
    use the account anymore.

    You can't change the password with this endpoint.

    delete:
    Delete

    Sets the user to inactive, logs out and informs admins to tidy up.

    `password` is required.

    Right now redirects to the home page. This might change.
    """

    queryset = (
        models.User.objects.filter(is_active=True)
        .prefetch_related('privileges__trustee')
        .annotate(
            edits=Count('historicaltranslatedsegments', distinct=True),
            dev_comments=Count('developercomments', distinct=True),
            seg_comments=Count('segmentcomments', distinct=True),
        )
    )
    serializer_class = serializers.UserResponseSerializer
    parser_classes = (
        # TODO Do we need JSONParser and FormParser?
        UnderscoreBeforeNumberParser,
        # parsers.FormParser,
        parsers.MultiPartParser,
    )

    def get_object(self):
        if self.request.method == 'GET':
            return self.queryset.get(pk=self.request.user.pk)
        return self.request.user

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        user = self.get_object()
        serializer = serializers.UserRequestSerializer(
            user,
            data=request.data,
            partial=partial,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        saved_user = serializer.save()

        if getattr(user, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            user._prefetched_objects_cache = {}

        if not saved_user.is_active:
            logout(request)
            return Response(_('Processing restricted'))

        return Response(serializer.data)

    # TODO change this to perform_destroy if I don't redirect
    def destroy(self, request, *args, **kwargs):
        # We cannot rely on a ProtectedError when we delete users to find
        # those who contributed somewhere because
        # django-simple-history uses on_delete=models.SET_NULL!
        instance = self.get_object()
        instance.changeReason = 'delete user'
        data = {'password': request.data.get('password'), 'is_active': False}
        serializer = self.get_serializer(instance, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        logout(request)
        # TODO log this
        body = (
            'Public ID: {}\n\nKeep this e-mail for 1 year in order to be '
            'able to delete the user again in case we have to restore a '
            'backup.'
        )
        send_mail(
            'User deletion requested',
            body.format(instance.public_id),
            settings.DEFAULT_FROM_EMAIL,
            settings.DEFAULT_TO_EMAILS,
        )
        return redirect('/')


class PersonalDataView(generics.RetrieveAPIView):
    """
    Personal data

    Lists all models with personal data of the (authenticated) user.

    Should be used to meet the needs of article 15 (3) GDPR concerning
    data of the database. See also recital 63.
    (Passwords, keys and session data are not included because they could
    affect our rights and freedoms, according to article 15 (4) GDPR.)
    """

    serializer_class = serializers.PersonalDataSerializer

    def get_object(self):
        return self.request.user


class ExportPersonalDataView(generics.CreateAPIView):
    """
    Export data

    Securely retrieves the authenticated user's personal data as zip file.

    Meets the needs of article 20 (1) GDPR concerning data of the database.
    See also recital 68 and (working paper) WP 242 rev.01 of the article 29
    data protection working party.
    """

    serializer_class = serializers.PasswordUserSerializer

    @swagger_auto_schema(responses={200: 'http://example.com'})
    def create(self, request, *args, **kwargs):
        user = request.user
        # Check password
        serializer = self.get_serializer(user, data=request.data)
        serializer.is_valid(raise_exception=True)
        # ZIP file
        filename = 'ellen4all.org_{name}_{id}_{date}.{{ext}}'.format(
            name=user.username,
            id=user.public_id,
            date=datetime.date.today().isoformat(),
        )
        path = os.path.join(settings.SENDFILE_ROOT, filename.format(ext='zip'))
        info = _(
            'Literary works and their translations are copyrighted by the '
            'Ellen G. White Estate®. You shall not adversely affect the '
            'rights and freedoms of the Ellen G. White Estate® or others '
            '(see article 20 (4) GDPR).'
        )
        try:
            with zipfile.ZipFile(path, 'x', zipfile.ZIP_DEFLATED) as f:
                ctx = {'request': request}
                data = self.get_renderers()[0].render(
                    serializers.PersonalDataSerializer(user, context=ctx).data
                )
                obj = b'{"info":"%(info)s","data":%(data)s}' % {
                    b'info': info.encode(),
                    b'data': data,
                }
                f.writestr(filename.format(ext='json'), obj)
        except FileExistsError:
            pass
        # Secure download
        return sendfile(request, path)


class CommunityUserProfileView(generics.RetrieveAPIView):
    """
    User retrieve

    Retrieves a user. Accessible for authenticated users.
    """

    queryset = models.User.objects.filter(is_active=True)
    serializer_class = serializers.CommunityUserProfileSerializer
    lookup_field = 'username'


class UserResponseMixin:
    def get_response(self):
        """
        Returns a response with the user object.
        """
        serializer = serializers.AuthUserSerializer(
            self.user, context={'request': self.request}
        )
        return Response(serializer.data)


CONFIRM_EMAIL_MSG = _('E-mail address confirmed successfully.')


class ConfirmEmailView(UserResponseMixin, VerifyEmailView):
    """
    Confirm e-mail address

    Confirms e-mail address, tries to log in and responses with a user object.

    Responses with a

    1. user object if the user is logged in (this only works when confirming
       the e-mail address immediately after signing up, assuming users didn’t
       close their browser or used some sort of private browsing mode),
    2. success message if confirmation was successful but login not,
    3. 404 if the key expired or was used already
       (execpt the user is logged in).
    """

    def get(self, request, *args, **kwargs):
        raise exceptions.MethodNotAllowed(request.method)

    @swagger_auto_schema(
        security=[],
        responses={
            200: serializers.AuthUserSerializer(),
            400: '*Currently, this is a 200 response!* ' + CONFIRM_EMAIL_MSG,
            404: 'Not found',
        },
    )
    def post(self, request, *args, **kwargs):
        # Copied from rest_auth 0.9.3
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.kwargs['key'] = serializer.validated_data['key']
        confirmation = self.get_object()
        email_address = confirmation.confirm(self.request)
        # Login (works only if the session contains the user key)
        self.login_on_confirm(confirmation)
        if request.user.username:
            # User is logged in
            self.user = request.user
            return self.get_response()
        if email_address:
            # E-mail address was verified
            return Response({'detail': CONFIRM_EMAIL_MSG})
        raise exceptions.NotFound()


@method_decorator(
    name='post',
    decorator=swagger_auto_schema(
        security=[],
        responses={
            200: serializers.AuthUserSerializer(),
            400: '*Validation errors*',
            404: 'Not found',
            429: '*Too many requests*',
        },
    ),
)
class LoginUserView(UserResponseMixin, LoginView):
    """
    Login

    Logs the user in, sets a session cookie and responses with a user object.

    A user's verified e-mail address and `isActive` are required.
    Sends a confirmation e-mail and responses with an appropriate error
    message if the first case is false.

    Max. 100 requests per hour allowed (in combination with some other
    endpoints).
    """

    throttle_classes = (AuthRateThrottle,)


@method_decorator(
    name='post',
    decorator=swagger_auto_schema(operation_id='Logout', responses={200: 'OK'}),
)
class LogoutView(RestAuthLogoutView):
    @swagger_auto_schema(auto_schema=None)
    def get(self, request, *args, **kwargs):
        raise exceptions.MethodNotAllowed(request.method)


@method_decorator(
    name='post',
    decorator=swagger_auto_schema(
        security=[],
        responses={
            200: 'Password reset e-mail has been sent.',
            400: '*Validation errors*',
            429: '*Too many requests*',
        },
    ),
)
class TransactionalPasswordResetView(PasswordResetView):
    """
    Password reset

    Sends a link to the e-mail address where the user can enter a new password
    via Mailjet.

    Max. 100 requests per hour allowed (in combination with some other
    endpoints).
    """

    serializer_class = serializers.TransactionalPasswordResetSerializer
    throttle_classes = (AuthRateThrottle,)


@method_decorator(
    name='get',
    decorator=swagger_auto_schema(
        responses={
            200: serializers.AuthUserSerializer(),
            205: 'Not authenticated',
        }
    ),
)
class LittleUserView(generics.RetrieveAPIView):
    """
    Auth User

    Retrieves the little user object of the currently authenticated user.

    Has the headers `version` and `released` containing information about
    the last software release of our website (authentication doesn't matter).

    **Notes**

    - Responses with a 205 status code if the user isn't authenticated
    - `contributions` may be an empty object (in all user objects)
    """

    serializer_class = serializers.AuthUserSerializer
    permission_classes = (permissions.AllowAny,)

    def get_object(self):
        return self.request.user

    def retrieve(self, request, *args, **kwargs):
        if self.get_object().username:
            response = super().retrieve(request, *args, **kwargs)
        else:
            response = Response({'detail': _('Not authenticated')}, status=205)
        response['version'] = settings.VERSION
        response['released'] = settings.RELEASED.isoformat()
        return response


@method_decorator(
    name='post',
    decorator=swagger_auto_schema(
        security=[],
        responses={
            200: 'Confirmation e-mail sent.',
            400: '*Validation errors*',
            429: '*Too many requests*',
        },
    ),
)
class ResendConfirmationView(generics.CreateAPIView):
    """
    Resend confirmation e-mail

    Sends a confirmation e-mail.

    Responses with a `400` if the e-mail address doesn't exist or is confirmed
    already.

    Max. 100 requests per hour allowed (in combination with some other
    endpoints).
    """

    # Minimize hits as far as possible
    queryset = EmailAddress.objects.filter(user__is_active=True, verified=False)
    serializer_class = serializers.SendConfirmationSerializer
    permission_classes = (permissions.AllowAny,)
    throttle_classes = (AuthRateThrottle,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            email = self.get_queryset().get(
                email=serializer.validated_data['email']
            )
        except self.queryset.model.DoesNotExist:
            msg = _(
                '"{email}" is confirmed already or was not found in our system.'
            )
            raise exceptions.ValidationError(
                {'email': msg.format(email=serializer.validated_data['email'])}
            )
        email.send_confirmation(request)
        # For automated login
        get_adapter(request).stash_user(request, user_pk_to_url_str(email.user))
        return Response({'detail': _('Confirmation e-mail sent.')})


class EmailAddressViewSet(
    mixins.ListModelMixin,
    # mixins.CreateModelMixin,
    # mixins.UpdateModelMixin,
    # mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    API endpoint for e-mail addresses of the authenticated user.

    list:
    E-mail addresses list

    Lists the e-mail addresses of the authenticated user.
    """

    serializer_class = serializers.EmailAddressSerializer

    def get_queryset(self):
        return self.request.user.emailaddress_set.all()

    @swagger_auto_schema(deprecated=True)
    @action(
        detail=False,
        methods=['post'],
        url_path='send-confirmation',
        serializer_class=serializers.SendConfirmationSerializer,
    )
    def send_confirmation(self, request):
        """
        Send confirmation link

        Sends a confirmation e-mail.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = get_object_or_404(
            self.get_queryset(), email=serializer.validated_data['email']
        )
        if email.verified:
            msg = _('{email} is verified already.').format(email=email.email)
            return Response({'detail': msg}, status=400)
        email.send_confirmation(request)
        return Response({'detail': _('Confirmation e-mail sent.')})


class FlagUserAPIView(APIView):
    permission_classes = (FlagUserPermissions,)

    def delete(self, request, public_id=None):
        flagger = self.request.user
        try:
            target = models.User.objects.get(public_id=public_id)
            if flagger.pk == target.pk:
                raise ValidationError('You can not unflag yourself.')

        except models.User.DoesNotExist:
            raise NotFound()

        flagger.unflag(target)

        return Response({}, status=status.HTTP_200_OK)

    def post(self, request, public_id=None):
        flagger = self.request.user

        try:
            target = models.User.objects.get(public_id=public_id)
            if flagger.pk == target.pk:
                raise ValidationError('You can not flag yourself.')

        except models.User.DoesNotExist:
            raise NotFound()

        reason = request.data.get('reason')
        flagger.flag(target, reason)

        send_mail(
            'New user flagged on Langify',
            f'{flagger.email} flagged {target.email} because of {reason}.',
            settings.DEFAULT_FROM_EMAIL,
            settings.DEFAULT_TO_EMAILS,
            fail_silently=True,
        )

        return Response({}, status=status.HTTP_201_CREATED)
