from drf_yasg.utils import swagger_serializer_method
from rest_framework import serializers

from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.utils.html import escape
from django.utils.translation import gettext as _

from .constants import COMMENT_DELETION_DELAY, LANGUAGES_DICT


class RelativeHyperlinkedRelatedField(serializers.HyperlinkedRelatedField):
    def get_url(self, obj, view_name, request, format):
        return super().get_url(obj, view_name, None, format)


class RelativeHyperlinkedIdentityField(
    serializers.HyperlinkedIdentityField, RelativeHyperlinkedRelatedField
):
    pass


class RelativeHyperlinkedSerializer(serializers.HyperlinkedModelSerializer):
    serializer_related_field = RelativeHyperlinkedRelatedField
    serializer_url_field = RelativeHyperlinkedIdentityField


class LanguageSerializer(serializers.Serializer):
    code = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    rtl = serializers.SerializerMethodField()

    def get_code(self, obj) -> str:
        if isinstance(obj, str):
            return obj
        return obj[0]

    def get_name(self, obj) -> str:
        if isinstance(obj, str):
            return LANGUAGES_DICT[obj]
        return obj[1]

    def get_rtl(self, obj) -> bool:
        if isinstance(obj, str):
            code = obj
        else:
            code = obj[0]
        base_code = code.split('-')[0]
        return base_code in settings.LANGUAGES_BIDI

    def to_representation(self, obj):
        if not obj:
            return None
        return super().to_representation(obj)

    def to_internal_value(self, data):
        """
        Expects the language code as string.
        """
        if data and str(data) not in LANGUAGES_DICT:
            msg = _('"{value}" is not a valid language code.')
            raise serializers.ValidationError(msg.format(value=escape(data)))
        return data

    def run_validators(self, value):
        """
        We shouldn't need this. Validation is done above.

        Default implementation raises an error.
        """


class PublicContributionsSerializer(serializers.Serializer):
    edits = serializers.IntegerField(min_value=0)


class PrivateContributionsSerializer(PublicContributionsSerializer):
    developer_comments = serializers.IntegerField(min_value=0)
    segment_comments = serializers.IntegerField(min_value=0)


class BaseUserSerializer(RelativeHyperlinkedSerializer):
    url = RelativeHyperlinkedIdentityField(
        view_name='community_user_profile',
        lookup_field='username',
        read_only=True,
    )
    thumbnail = serializers.ReadOnlyField(source='get_avatar')
    contributions = serializers.SerializerMethodField()

    @swagger_serializer_method(PublicContributionsSerializer)
    def get_contributions(self, obj):
        # TODO cache
        if obj.is_active:
            return {'edits': obj.edits}
        return {}


class UserFieldSerializer(BaseUserSerializer):
    """
    Minimal user serializer which hides deleted users.
    """

    id = serializers.SerializerMethodField(source='public_id')
    url = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = [
            'url',
            'id',
            'username',
            'first_name',
            'last_name',
            'contributions',
            'thumbnail',
        ]

    def get_id(self, obj) -> str:
        if obj.is_active:
            return obj.public_id
        return None

    @swagger_serializer_method(serializers.URLField)
    def get_url(self, obj):
        if obj.is_active:
            url = reverse(
                'community_user_profile', kwargs={'username': obj.username}
            )
            return url
        return None

    def get_username(self, obj) -> str:
        if obj.is_active:
            return obj.username
        return _(obj.deleted_username)

    def get_first_name(self, obj) -> str:
        if obj.show_full_name and obj.is_active:
            return obj.first_name
        return ''

    def get_last_name(self, obj) -> str:
        if obj.show_full_name and obj.is_active:
            return obj.last_name
        return ''


class CommentSerializer(RelativeHyperlinkedSerializer):
    user = UserFieldSerializer(read_only=True)
    delete = serializers.NullBooleanField(
        required=False,
        write_only=True,
        help_text=(
            'True to mark the comment for deletion or false to remove the '
            'mark. Null is ignored.'
        ),
    )

    def to_internal_value(self, data):
        """
        Set the final deletion date.
        """
        validated_data = super().to_internal_value(data)
        delete = validated_data.get('delete')
        if delete is True:
            to_delete = timezone.now() + COMMENT_DELETION_DELAY
            validated_data['to_delete'] = to_delete
            del validated_data['delete']
        elif delete is False:
            validated_data['to_delete'] = None
            del validated_data['delete']
        return validated_data

    class Meta:
        fields = [
            'id',
            'user',
            'created',
            'last_modified',
            'delete',
            'to_delete',
            'content',
        ]
        read_only_fields = ('to_delete', 'user')
