import json
from collections import OrderedDict

from allauth.account.models import EmailAddress, EmailConfirmation
from allauth.account.utils import (
    send_email_confirmation,
    sync_user_email_addresses,
)
from allauth.socialaccount.models import SocialAccount, SocialToken
from django_countries import countries
from django_countries.serializers import CountryFieldMixin
from drf_yasg.utils import swagger_serializer_method
from rest_auth.registration.serializers import RegisterSerializer
from rest_auth.serializers import (
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetSerializer,
)
from rest_framework import serializers
from rest_framework_extensions.serializers import PartialUpdateSerializerMixin
from rest_framework_recaptcha.fields import ReCaptchaField

from base.constants import LANGUAGES, PERMISSIONS, ROLES
from base.serializers import (
    BaseUserSerializer,
    LanguageSerializer,
    PrivateContributionsSerializer,
    UserFieldSerializer,
)
from django.conf import settings
from django.contrib.admin.models import LogEntry
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.models import Group, Permission
from django.contrib.sessions.models import Session
from django.db.models import Q
from django.db.models.fields.reverse_related import ForeignObjectRel
from django.urls import reverse
from django.utils.translation import gettext as _
from misc.apis import MailjetClient
from misc.models import DeveloperComment, HistoricalPage
from panta.models import (
    HistoricalAuthor,
    HistoricalLicence,
    HistoricalOriginalSegment,
    HistoricalOriginalWork,
    HistoricalReference,
    HistoricalTranslatedSegment,
    HistoricalTranslatedWork,
    HistoricalTrustee,
    SegmentComment,
    SegmentDraft,
    TranslatedSegment,
    Trustee,
    Vote,
)
from path import models
from style_guide.models import (
    HistoricalIssue,
    HistoricalStyleGuide,
    Issue,
    IssueComment,
)


class CountrySerializer(serializers.Serializer):
    code = serializers.ChoiceField(
        choices=tuple(countries.countries.items()), allow_null=True
    )
    name = serializers.CharField(allow_null=True)
    flag = serializers.URLField(allow_null=True)
    unicode_flag = serializers.CharField(max_length=1, allow_null=True)


class PrivilegeSerializer(serializers.ModelSerializer):
    # trustee_name = serializers.StringRelatedField()

    class Meta:
        model = models.Privilege
        # TODO add trustee (no yet in router)
        fields = ('name', 'language', 'trustee')


def get_permissions_serializer():
    PerLanguagePermSerializer = type(
        'PerLanguagePermissionsSerializer',
        (serializers.Serializer,),
        OrderedDict(
            (name, serializers.BooleanField())
            for name, minimum in PERMISSIONS.items()
        ),
    )
    PermissionsSerializer = type(
        'PermissionsSerializer',
        (serializers.Serializer,),
        OrderedDict(
            # The label is cached or so in drf_yasg and had the same value
            # for all objects
            (code, type(name, (PerLanguagePermSerializer,), {})(label=name))
            for code, name in LANGUAGES
        ),
    )
    return PermissionsSerializer


class AuthUserSerializer(UserFieldSerializer):
    language = LanguageSerializer()
    permissions = get_permissions_serializer()()

    class Meta(UserFieldSerializer.Meta):
        fields = UserFieldSerializer.Meta.fields + ['language', 'permissions']


class RoleSerializer(serializers.Serializer):
    language = serializers.CharField()
    role = serializers.ChoiceField(choices=ROLES)
    edits = serializers.IntegerField(
        min_value=0, help_text='Count of all edited segments of the language.'
    )


class ThumbnailsSerializer(serializers.Serializer):
    url = serializers.URLField()
    width = serializers.IntegerField(
        min_value=models.User.thumbnail_sizes[0],
        max_value=models.User.thumbnail_sizes[-1],
    )
    height = serializers.IntegerField(
        min_value=models.User.thumbnail_sizes[0],
        max_value=models.User.thumbnail_sizes[-1],
    )


class BaseUserProfileSerializer(BaseUserSerializer):
    language = LanguageSerializer(
        required=False,
        help_text='Expects the language code or an empty string.',
    )
    roles = RoleSerializer(
        many=True,
        read_only=True,
        help_text='Languages without edits are excluded.',
    )
    thumbnails = serializers.SerializerMethodField()

    @swagger_serializer_method(ThumbnailsSerializer(many=True))
    def get_thumbnails(self, obj):
        if not obj.avatar:
            return None
        thumbnails = []
        for size in obj.thumbnail_sizes:
            thumbnails.append(
                {
                    'url': getattr(obj, f'avatar_{size}').url,
                    'width': size,
                    'height': size,
                }
            )
        return thumbnails


class UserRequestSerializer(
    CountryFieldMixin, PartialUpdateSerializerMixin, BaseUserProfileSerializer
):

    id = serializers.ReadOnlyField(source='public_id')
    # The `.update()` method does not support writable nested fields
    # by default. Write an explicit `.update()` method for serializer
    # `path.api.serializers.UserRequestSerializer`
    privileges = PrivilegeSerializer(many=True, read_only=True)
    age = serializers.ReadOnlyField()

    class Meta:
        model = models.User
        fields = (
            'url',
            'id',
            'username',
            'first_name',
            'last_name',
            'email',
            'password',
            'is_active',
            'avatar',
            'avatar_crop',
            'thumbnail',
            'thumbnails',
            'address',
            'address_2',
            'zip_code',
            'city',
            'state',
            'phone',
            'born',
            # 'reputation',
            'age',
            'privileges',
            # 'groups',
            'last_login',
            'date_joined',
            'language',
            'roles',
            'country',
            'description',
            'experience',
            'education',
            'subscribed_edits',
            'show_full_name',
            'show_country',
            'show_age',
            'show_description',
            'show_experience',
            'show_education',
        )
        read_only_fields = (
            'id',
            'username',
            'reputation',
            'last_login',
            'date_joined',
            'age',
        )
        extra_kwargs = {
            # 'first_name': {'allow_blank': False},
            # 'last_name': {'allow_blank': False},
            'is_active': {'write_only': True},
            'password': {
                'required': False,
                # TODO #98
                # 'style': {'input_type': 'password'},
                'write_only': True,
            },
            'language': {'help_text': 'Empty string is allowed.'},
        }

    def validate(self, data):
        """
        Validates that the password is correct before restricting processing.
        """
        # Pop the password that it won't be saved
        password = data.pop('password', None)
        if data.get('is_active') is False:
            if not password:
                raise serializers.ValidationError(
                    _('Please enter your password to confirm your decision')
                )
            if not self.context['request'].user.check_password(password):
                raise serializers.ValidationError(
                    _('Your password was invalid')
                )
        return data


class UserResponseSerializer(UserRequestSerializer):
    age = serializers.IntegerField(min_value=0, required=False)
    country = CountrySerializer(required=False)

    class Meta(UserRequestSerializer.Meta):
        fields = UserRequestSerializer.Meta.fields + (
            'age',
            'contributions',
            'is_verified',
        )

    @swagger_serializer_method(PrivateContributionsSerializer)
    def get_contributions(self, obj):
        # TODO cache
        aggregates = super().get_contributions(obj)
        aggregates.update(
            {
                'developer_comments': obj.dev_comments,
                'segment_comments': obj.seg_comments,
            }
        )
        return aggregates


class CommunityUserProfileSerializer(BaseUserProfileSerializer):
    id = serializers.ReadOnlyField(source='public_id')
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()
    country = serializers.SerializerMethodField(required=False)
    description = serializers.SerializerMethodField()
    experience = serializers.SerializerMethodField()
    education = serializers.SerializerMethodField()

    def get_first_name(self, obj) -> str:
        if obj.show_full_name:
            return obj.first_name
        return ''

    def get_last_name(self, obj) -> str:
        if obj.show_full_name:
            return obj.last_name
        return ''

    def get_age(self, obj) -> int:
        if obj.show_age:
            return obj.age
        return None

    @swagger_serializer_method(CountrySerializer)
    def get_country(self, obj):
        if obj.show_country:
            country = obj.country
        else:
            country = {}
        return CountrySerializer(country).data

    def get_description(self, obj) -> str:
        if obj.show_description:
            return obj.description
        return ''

    def get_experience(self, obj) -> str:
        if obj.show_experience:
            return obj.experience
        return ''

    def get_education(self, obj) -> str:
        if obj.show_education:
            return obj.education
        return ''

    class Meta:
        model = models.User
        fields = (
            'url',
            'id',
            'username',
            'first_name',
            'last_name',
            'thumbnail',
            'thumbnails',
            'age',
            'date_joined',
            'language',
            'roles',
            'country',
            'description',
            'experience',
            'education',
            'is_verified',
            'show_full_name',
            'show_country',
            'show_age',
            'show_description',
            'show_experience',
            'show_education',
        )


class PasswordUserSerializer(UserRequestSerializer):
    class Meta(UserRequestSerializer):
        model = models.User
        fields = ('password',)
        validators = ()


class SignupSerializer(RegisterSerializer):
    """
    Signup with a terms and conditions field.
    """

    terms = serializers.BooleanField()
    recaptcha_token = ReCaptchaField()


class SimpleLoginSerializer(LoginSerializer):
    """
    Distinguishes between username and e-mail address automatically.
    """

    username = serializers.CharField(help_text=_('Username or e-mail address'))
    # "Delete" e-mail field
    email = None

    def validate(self, attrs):
        # An @ is not allowed in usernames
        if '@' in attrs.get('username'):
            attrs['email'] = attrs.pop('username')

        # Copied from rest_auth 0.9.3
        username = attrs.get('username')
        email = attrs.get('email')
        password = attrs.get('password')
        # Authentication through either username or email
        user = self._validate_username_email(username, email, password)
        # Did we get back an active user?
        if user:
            if not user.is_active:
                msg = _('User account is disabled.')
                raise serializers.ValidationError(msg)
        else:
            msg = _('Unable to log in with provided credentials.')
            raise serializers.ValidationError(msg)
        # If required, is the email verified?
        # Modifications ----
        try:
            email_address = user.emailaddress_set.get(email=user.email)
            verified = email_address.verified
        except EmailAddress.DoesNotExist:
            # Create an EmailAddress for the user
            sync_user_email_addresses(user)
            verified = False
        if not verified:
            send_email_confirmation(self.context['request'], user)
            msg = _(
                'Your e-mail address is not verified yet. '
                'We just sent you an e-mail with a confirmation link. '
                'Please check your mailbox.'
            )
            raise serializers.ValidationError(msg)

        attrs['user'] = user
        return attrs


class EmailAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailAddress
        # fields = ('url', 'id', 'email', 'verified', 'primary')
        fields = ('id', 'email', 'verified', 'primary')
        read_only_fields = ('verified',)


class SendConfirmationSerializer(serializers.Serializer):
    email = serializers.EmailField()


class TransactionalPasswordResetForm(PasswordResetForm):
    def send_mail(
        self,
        subject_template_name,
        email_template_name,
        context,
        from_email,
        to_email,
        html_email_template_name=None,
    ):
        """
        Sends transactional e-mails via Mailjet.
        """
        subject = _('Reset password')
        link = '{protocol}://{domain}{url}'.format(
            protocol=context['protocol'],
            domain=context['domain'],
            url=reverse(
                'password_reset_confirm',
                kwargs={'uidb64': context['uid'], 'token': context['token']},
            ),
        )
        context = {
            'heading': _('Password forgotten?'),
            'introduction': _('Don\'t worry.'),
            'task': _('Just click on the green button and enter a new one.'),
            'button': _('Reset password'),
            'link': link,
            'ignore_note': _(
                'In case you didn\'t request a password reset on '
                'ellen4all.org you can ignore this e-mail.'
            ),
        }
        client = MailjetClient()
        client.send_transactional_email(533_481, to_email, subject, context)

    def get_users(self, email):
        users = tuple(super().get_users(email))
        if users:
            return users
        msg = _('"{email}" was not found in our system.')
        raise serializers.ValidationError({'email': msg.format(email=email)})


class TransactionalPasswordResetSerializer(PasswordResetSerializer):
    password_reset_form_class = TransactionalPasswordResetForm


class PasswordResetConfirmSerializer(PasswordResetConfirmSerializer):
    def validate(self, attrs):
        from django.utils.encoding import force_text
        from django.contrib.auth.tokens import default_token_generator
        from django.contrib.auth import get_user_model
        from rest_framework.exceptions import ValidationError
        from django.utils.http import urlsafe_base64_decode as uid_decoder

        UserModel = get_user_model()
        self._errors = {}

        # Decode the uidb64 to uid to get User object
        try:
            uid = force_text(uid_decoder(attrs['uid']))
            self.user = UserModel._default_manager.get(pk=uid)
        except (TypeError, ValueError, OverflowError, UserModel.DoesNotExist):
            raise ValidationError({'uid': ['Invalid value']})

        self.custom_validation(attrs)
        # Construct SetPasswordForm instance
        self.set_password_form = self.set_password_form_class(
            user=self.user, data=attrs
        )
        if not self.set_password_form.is_valid():
            raise serializers.ValidationError(self.set_password_form.errors)
        if not default_token_generator.check_token(self.user, attrs['token']):
            raise ValidationError(
                {'token': ['Your password reset link is expired']}
            )

        return attrs


# Personal data
# =============
class PersonalDataBaseSerializer(serializers.ModelSerializer):
    include_reverse_fields = False

    def __init__(self, *args, **kwargs):
        """
        Checks additionally that all fields are considered.
        """
        if settings.DEBUG or settings.TEST:
            fields = set(self.Meta.fields)
            excluded = set(self.Meta.excluded)
            assert not fields & excluded, 'Fields don\'t match for {}'.format(
                self
            )
            all_fields = fields | excluded
            model_fields = set()
            for field in self.Meta.model._meta.get_fields():
                is_many = getattr(field, 'multiple', False)
                is_reverse = isinstance(field, ForeignObjectRel)
                if is_many:
                    if self.include_reverse_fields or not is_reverse:
                        model_fields.add(field.get_accessor_name())
                else:
                    model_fields.add(field.name)
            exceptions = set(getattr(self.Meta, 'exceptions', set()))
            assert model_fields == all_fields - exceptions, (
                self.Meta.model,
                model_fields ^ (all_fields - exceptions),
            )
        super().__init__(*args, **kwargs)

    def hide(self, obj):
        return _('(Value not displayed for safety reasons)')


# allauth.account


class EmailConfirmationSerializer(PersonalDataBaseSerializer):
    key = serializers.SerializerMethodField(method_name='hide')

    class Meta:
        model = EmailConfirmation
        fields = ('id', 'created', 'sent', 'key')
        excluded = ('email_address',)


class PersonalDataEmailAddressSerializer(PersonalDataBaseSerializer):
    emailconfirmation_set = EmailConfirmationSerializer(
        many=True, read_only=True
    )

    include_reverse_fields = True

    class Meta:
        model = EmailAddress
        fields = ('id', 'email', 'verified', 'primary', 'emailconfirmation_set')
        excluded = ('user',)


class HistoricalEmailAddressSerializer(PersonalDataBaseSerializer):
    user = serializers.StringRelatedField()
    history_user = serializers.StringRelatedField()

    class Meta:
        model = models.HistoricalEmailAddress
        # Users are included because the data subject could be one of both
        fields = (
            'id',
            'email',
            'verified',
            'user',
            'history_id',
            'history_change_reason',
            'history_date',
            'history_type',
            'history_user',
        )
        excluded = ()


# allauth.socialaccount


class SocialTokenSerializer(PersonalDataBaseSerializer):
    app = serializers.StringRelatedField()
    token_secret = serializers.SerializerMethodField(method_name='hide')

    class Meta:
        model = SocialToken
        fields = ('id', 'app', 'token', 'token_secret', 'expires_at')
        excluded = ('account',)


class SocialAccountSerializer(PersonalDataBaseSerializer):
    socialtoken_set = SocialTokenSerializer(many=True, read_only=True)

    include_reverse_fields = True

    class Meta:
        model = SocialAccount
        ref_name = 'PersonalDataSocialAccount'
        fields = (
            'id',
            'provider',
            'uid',
            'last_login',
            'date_joined',
            'extra_data',
            'socialtoken_set',
        )
        excluded = ('user',)


# admin


class LogEntrySerializer(PersonalDataBaseSerializer):
    content_type = serializers.StringRelatedField()
    change_message = serializers.SerializerMethodField()

    class Meta:
        model = LogEntry
        fields = (
            'id',
            'action_time',
            'object_id',
            'content_type',
            'object_repr',
            'action_flag',
            'change_message',
        )
        excluded = ('user',)

    def get_change_message(self, obj) -> dict:
        if obj.change_message:
            return json.loads(obj.change_message)


# auth


class GroupSerializer(PersonalDataBaseSerializer):
    class Meta:
        model = Group
        fields = ('id', 'name')
        excluded = ('permissions',)


class PermissionSerializer(PersonalDataBaseSerializer):
    class Meta:
        model = Permission
        fields = ('id', 'name', 'content_type', 'codename')
        excluded = ()


# sessions


class SessionSerializer(PersonalDataBaseSerializer):
    session_key = serializers.SerializerMethodField(method_name='hide')
    expire_date = serializers.DateTimeField(source='get_expiry_date')

    class Meta:
        model = Session
        fields = ('session_key', 'expire_date')
        # ToDo: Maybe add session_data back to fields
        excluded = ('session_data',)


# guardian's GroupObjectPermission, UserObjectPermission?

# misc


class DeveloperCommentSerializer(PersonalDataBaseSerializer):
    class Meta:
        model = DeveloperComment
        ref_name = 'PersonalDataDeveloperComment'
        fields = ('id', 'created', 'last_modified', 'content', 'to_delete')
        excluded = ('user',)


class IssueCommentSerializer(PersonalDataBaseSerializer):
    class Meta:
        model = IssueComment
        ref_name = 'PersonalDataIssueComment'
        fields = (
            'id',
            'created',
            'last_modified',
            'content',
            'to_delete',
            'issue',
        )
        excluded = ('user',)


class HistoricalPageSerializer(PersonalDataBaseSerializer):
    class Meta:
        model = HistoricalPage
        fields = (
            'id',
            'created',
            'last_modified',
            'slug',
            'public',
            'contact_button',
            'content',
            'history_id',
            'history_change_reason',
            'history_date',
            'history_type',
        )
        excluded = ('history_user',)


# panta


class VoteSerializer(PersonalDataBaseSerializer):
    class Meta:
        model = Vote
        ref_name = 'PersonalDataVote'
        fields = (
            'id',
            'date',
            'segment',
            'historical_segments',
            'role',
            'value',
            'revoke',
        )
        excluded = ('user',)


class HistoricalAuthorSerializer(PersonalDataBaseSerializer):
    class Meta:
        model = HistoricalAuthor
        fields = (
            'id',
            'created',
            'last_modified',
            'prefix',
            'first_name',
            'last_name',
            'suffix',
            'born',
            'bio',
            'history_id',
            'history_change_reason',
            'history_date',
            'history_type',
        )
        excluded = ('history_user',)


class HistoricalLicenceSerializer(PersonalDataBaseSerializer):
    class Meta:
        model = HistoricalLicence
        fields = (
            'id',
            'created',
            'last_modified',
            'title',
            'description',
            'history_id',
            'history_change_reason',
            'history_date',
            'history_type',
        )
        excluded = ('history_user',)


class HistoricalOriginalSegmentSerializer(PersonalDataBaseSerializer):
    class Meta:
        model = HistoricalOriginalSegment
        fields = (
            'id',
            'created',
            'last_modified',
            'position',
            'page',
            'tag',
            'classes',
            'content',
            'reference',
            'key',
            'work',
            'history_id',
            'history_change_reason',
            'history_date',
            'history_type',
        )
        excluded = ('history_user',)


class HistoricalOriginalWorkSerializer(PersonalDataBaseSerializer):
    trustee = serializers.StringRelatedField()
    author = serializers.StringRelatedField()
    licence = serializers.StringRelatedField()

    class Meta:
        model = HistoricalOriginalWork
        fields = (
            'id',
            'created',
            'last_modified',
            'key',
            'title',
            'subtitle',
            'abbreviation',
            'type',
            'description',
            'language',
            'private',
            'published',
            'edition',
            'isbn',
            'publisher',
            'trustee',
            'author',
            'licence',
            'history_id',
            'history_change_reason',
            'history_date',
            'history_type',
        )
        excluded = ('history_user',)


class HistoricalReferenceSerializer(PersonalDataBaseSerializer):
    class Meta:
        model = HistoricalReference
        fields = (
            'id',
            'created',
            'last_modified',
            'title',
            'type',
            'abbreviation',
            'author',
            'published',
            'language',
            'history_id',
            'history_change_reason',
            'history_date',
            'history_type',
        )
        excluded = ('history_user',)


class HistoricalTranslatedSegmentSerializer(PersonalDataBaseSerializer):
    class Meta:
        model = HistoricalTranslatedSegment
        fields = (
            'id',
            'content',
            'relative_id',
            'chapter',
            'work',
            'history_id',
            'history_change_reason',
            'history_date',
            'history_type',
        )
        excluded = ('history_user', 'history_relation')


class HistoricalTranslatedWorkSerializer(PersonalDataBaseSerializer):
    trustee = serializers.StringRelatedField()
    original = serializers.StringRelatedField()

    class Meta:
        model = HistoricalTranslatedWork
        fields = (
            'id',
            'created',
            'last_modified',
            'title',
            'subtitle',
            'abbreviation',
            'type',
            'description',
            'language',
            'private',
            'protected',
            'trustee',
            'original',
            'history_id',
            'history_change_reason',
            'history_date',
            'history_type',
        )
        excluded = ('history_user',)


class HistoricalTrusteeSerializer(PersonalDataBaseSerializer):
    class Meta:
        model = HistoricalTrustee
        fields = (
            'id',
            'name',
            'description',
            'code',
            'history_id',
            'history_change_reason',
            'history_date',
            'history_type',
        )
        excluded = ('history_user',)


class SegmentCommentSerializer(PersonalDataBaseSerializer):
    work = serializers.StringRelatedField()

    class Meta:
        model = SegmentComment
        ref_name = 'PersonalDataSegmentComment'
        fields = (
            'id',
            'created',
            'last_modified',
            'work',
            'position',
            'content',
            'role',
            'vote',
            'to_delete',
        )
        excluded = ('user',)


class SegmentDraftSerializer(PersonalDataBaseSerializer):
    segment = serializers.StringRelatedField()
    work = serializers.StringRelatedField()

    class Meta:
        model = SegmentDraft
        ref_name = 'PersonalDataSegmentDraft'
        fields = ('id', 'created', 'content', 'segment', 'work', 'position')
        excluded = ('owner',)


class TranslatedSegmentSerializer(PersonalDataBaseSerializer):
    work = serializers.StringRelatedField()
    original = serializers.StringRelatedField()
    locked_by = serializers.StringRelatedField()
    chapter = serializers.StringRelatedField()

    class Meta:
        model = TranslatedSegment
        ref_name = 'PersonalDataTranslatedSegment'
        fields = (
            'id',
            'created',
            'last_modified',
            'position',
            'page',
            'tag',
            'classes',
            'content',
            'reference',
            'chapter',
            'work',
            'original',
            'locked_by',
            'progress',
        )
        excluded = ('important_heading',)


class TrusteeSerializer(PersonalDataBaseSerializer):
    class Meta:
        model = Trustee
        ref_name = 'PersonalDataTrustee'
        fields = ('id', 'name', 'description', 'code')
        excluded = ('members',)


# path


class HistoricalUserSerializer(CountryFieldMixin, PersonalDataBaseSerializer):
    password = serializers.SerializerMethodField(method_name='hide')
    history_user = serializers.StringRelatedField()

    class Meta:
        model = models.HistoricalUser
        owner_fields = (
            'password',  # TODO remove from versioning?
            'last_login',
            'is_superuser',
            'is_staff',
            'is_active',
            'date_joined',
            'username',
            'first_name',
            'last_name',
            'pseudonym',
            'name_display',
            'email',
            'avatar',
            'avatar_crop',
            'address',
            'address_2',
            'zip_code',
            'city',
            'state',
            'country',
            'phone',
            'language',
            'born',
            'description',
            'experience',
            'education',
            'is_verified',
            'subscribed_edits',
            'show_full_name',
            'show_country',
            'show_age',
            'show_description',
            'show_experience',
            'show_education',
            'history_id',
            'history_change_reason',
            'history_date',
            'history_user',
            'history_type',
        )
        # ToDo: username might not be ideal here
        minimal_fields = ('username', 'password', 'history_user')
        fields = owner_fields
        excluded = ('id',)

    @property
    def _readable_fields(self):
        """
        Stops fields caching.
        """
        return self.fields.values()

    def to_representation(self, data):
        """
        Adjusts fields and returns a primitive data structure.

        Includes most fields if user is the owner. Hides most fields otherwise.
        Deletes _field cache because the fields may change for every object.
        """
        if self.context['request'].user.pk == data.id:
            self.Meta.fields = self.Meta.owner_fields
        else:
            self.Meta.fields = self.Meta.minimal_fields
        try:
            del self._fields
        except AttributeError:
            pass
        return super().to_representation(data)


# path's Privilege?


class ReputationSerializer(PersonalDataBaseSerializer):
    class Meta:
        model = models.Reputation
        fields = ('id', 'score', 'language')
        excluded = ('user',)


# style_guide


class HistoricalStyleGuideSerializer(PersonalDataBaseSerializer):
    class Meta:
        model = HistoricalStyleGuide
        fields = (
            'id',
            'created',
            'last_modified',
            'title',
            'content',
            'language',
            'history_id',
            'history_change_reason',
            'history_date',
            'history_type',
        )
        excluded = ('history_user',)


class HistoricalStyleGuideIssueSerializer(PersonalDataBaseSerializer):
    class Meta:
        model = HistoricalIssue
        fields = (
            'id',
            'title',
            'content',
            'style_guide',
            'is_from_style_guide',
            'diff',
            'history_id',
            'history_change_reason',
            'history_date',
            'history_type',
        )
        excluded = ('history_user',)


class IssuesSerializer(PersonalDataBaseSerializer):
    style_guide = serializers.StringRelatedField()

    class Meta:
        model = Issue
        fields = (
            'id',
            'created',
            'last_modified',
            'title',
            'content',
            'diff',
            'style_guide',
            'is_from_style_guide',
        )
        excluded = ('user', 'tags')


class PersonalDataSerializer(UserRequestSerializer, PersonalDataBaseSerializer):
    """
    Serializer for all personal data of a user.
    """

    password = serializers.SerializerMethodField(method_name='hide')
    groups = GroupSerializer(many=True, read_only=True)
    user_permissions = PermissionSerializer(many=True, read_only=True)
    emailaddress_set = PersonalDataEmailAddressSerializer(
        many=True, read_only=True
    )
    historicalemailaddresses = serializers.SerializerMethodField()
    socialaccount_set = SocialAccountSerializer(many=True, read_only=True)
    logentry_set = LogEntrySerializer(many=True, read_only=True)
    developercomments = DeveloperCommentSerializer(many=True, read_only=True)
    historicalpages = HistoricalPageSerializer(many=True, read_only=True)
    historicalauthors = HistoricalAuthorSerializer(many=True, read_only=True)
    historicallicences = HistoricalLicenceSerializer(many=True, read_only=True)
    historicaloriginalsegments = HistoricalOriginalSegmentSerializer(
        many=True, read_only=True
    )
    historicaloriginalworks = HistoricalOriginalWorkSerializer(
        many=True, read_only=True
    )
    historicalreferences = HistoricalReferenceSerializer(
        many=True, read_only=True
    )
    historicaltranslatedsegments = HistoricalTranslatedSegmentSerializer(
        many=True, read_only=True
    )
    historicaltranslatedworks = HistoricalTranslatedWorkSerializer(
        many=True, read_only=True
    )
    historicaltrustees = HistoricalTrusteeSerializer(many=True, read_only=True)
    votes = VoteSerializer(many=True, read_only=True)
    segmentcomments = SegmentCommentSerializer(many=True, read_only=True)
    drafts = SegmentDraftSerializer(many=True, read_only=True)
    translatedsegment_set = TranslatedSegmentSerializer(
        many=True, read_only=True
    )
    trustee_memberships = TrusteeSerializer(many=True, read_only=True)
    historicalusers = HistoricalUserSerializer(many=True, read_only=True)
    reputations = ReputationSerializer(many=True, read_only=True)
    session = serializers.SerializerMethodField()
    historicalstyleguides = HistoricalStyleGuideSerializer(
        many=True, read_only=True
    )
    historicalissues = HistoricalStyleGuideIssueSerializer(
        many=True, read_only=True
    )
    issues = IssuesSerializer(many=True, read_only=True)
    issuecomments = IssueCommentSerializer(many=True, read_only=True)

    include_reverse_fields = True
    age = serializers.ReadOnlyField()

    class Meta:
        model = models.User
        fields = (
            'id',
            'username',
            'first_name',
            'last_name',
            'pseudonym',
            'name_display',
            'email',
            'password',
            'is_active',
            'is_staff',
            'is_superuser',
            'avatar',
            'avatar_crop',
            'thumbnails',
            'address',
            'address_2',
            'zip_code',
            'city',
            'state',
            'phone',
            'born',
            'age',
            'privileges',
            'subscribed_edits',
            'last_login',
            'date_joined',
            'language',
            'country',
            'description',
            'experience',
            'education',
            'is_verified',
            'show_full_name',
            'show_country',
            'show_age',
            'show_description',
            'show_experience',
            'show_education',
            'groups',
            'user_permissions',
            'emailaddress_set',
            'historicalemailaddresses',
            'socialaccount_set',
            'logentry_set',
            'developercomments',
            'historicalpages',
            'historicalauthors',
            'historicallicences',
            'historicaloriginalsegments',
            'historicaloriginalworks',
            'historicalreferences',
            'historicaltranslatedsegments',
            'historicaltranslatedworks',
            'historicaltrustees',
            'votes',
            'segmentcomments',
            'drafts',
            'translatedsegment_set',
            'trustee_memberships',
            'historicalusers',
            'reputations',
            'session',
            'historicalstyleguides',
            'historicalissues',
            'issues',
            'issuecomments',
        )
        read_only_fields = fields
        excluded = (
            'public_id',
            'userobjectpermission_set',
            'flagged_user',
            'flagger_user',
            'flags',
            'flagged_by',
            'issuereactions',
        )
        exceptions = ('thumbnails', 'session', 'age')

    @swagger_serializer_method(SessionSerializer)
    def get_session(self, obj):
        return SessionSerializer(self.context['request'].session).data

    @swagger_serializer_method(HistoricalEmailAddressSerializer)
    def get_historicalemailaddresses(self, obj):
        objects = models.HistoricalEmailAddress.objects.filter(
            Q(user_id=obj.pk) | Q(history_user_id=obj.pk)
        )
        serializer = HistoricalEmailAddressSerializer(objects, many=True)
        return serializer.data
