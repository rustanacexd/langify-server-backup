from datetime import datetime

from drf_yasg.utils import swagger_serializer_method
from rest_framework import serializers
from rest_framework.reverse import reverse

from base.constants import ROLES, get_languages
from base.exceptions import JsonValidationError
from base.serializers import (
    CommentSerializer,
    LanguageSerializer,
    RelativeHyperlinkedSerializer,
    UserFieldSerializer,
)
from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext as _
from panta import constants, models
from panta.constants import BLANK, IN_REVIEW, TRUSTEE_DONE
from panta.utils import sanitize_content

SEGMENT_CHANGED_ERROR_MESSAGE = _(
    'Somebody worked on this text in the meantime. '
    'Your data was just updated automatically.'
)


class RequestResponseModelSerializer(serializers.ModelSerializer):
    """
    ModelSerializer with different fields in request and response.
    """

    # Be aware that read only attributes are normally not set for 'is_response'.
    # Therefore, avoid to use it for the serialization of requests.

    # todo: As soon as we use OpenAPI 3, we can do both, request and response
    # with read only fields

    is_response = False

    def __new__(cls, *args, **kwargs):
        """
        Workaround for some drf_yasg (1.12) caching.
        """
        if kwargs.get('is_response', False):
            cls = type('Response{}'.format(cls.__name__), (cls,), {})
        return super().__new__(cls, *args, **kwargs)

    # For some reason it didn't work to add/override (i.e. 'many_init') class
    # methods to set 'is_response'.

    def __init__(self, *args, **kwargs):
        self.is_response = kwargs.pop('is_response', False)
        super().__init__(*args, **kwargs)

    def get_field_names(self, declared_fields, info):
        """
        Returns Meta.request_fields or Meta.response_fields.

        Removes some assertions of the default implementation.
        """
        if self.is_response:
            return self.Meta.response_fields
        return self.Meta.request_fields

    def convert_to_response(self):
        """
        Applies response field changes.
        """
        self.is_response = True
        # Clear cache
        del self.fields


class RequestResponseSerializer(serializers.Serializer):
    """
    Serializer with different fields in request and response.
    """

    def __new__(cls, *args, **kwargs):
        """
        Workaround for some drf_yasg caching.
        """
        if kwargs.get('is_response', False):
            cls = type('Response{}'.format(cls.__name__), (cls,), {})
        return super().__new__(cls, *args, **kwargs)

    def __init__(self, *args, **kwargs):
        """
        Uses Meta.request_fields or Meta.response_fields to adjust the fields.
        """
        is_response = kwargs.pop('is_response', False)
        super().__init__(*args, **kwargs)
        if is_response:
            exclude = self.Meta.request_fields
        else:
            exclude = self.Meta.response_fields
        for field in exclude:
            self.fields.pop(field)

    def convert_to_response(self):
        raise NotImplementedError


class SegmentHyperlinkField(serializers.HyperlinkedRelatedField):
    read_only = True

    def get_url(self, obj, view_name, request, format):
        url = reverse(
            view_name,
            kwargs={
                'parent_query_lookup_work': obj.work_id,
                'position': obj.position,
            },
            request=request,
            format=format,
        )
        return url


class TrusteeSerializer(RelativeHyperlinkedSerializer):
    class Meta:
        model = models.Trustee
        fields = ('url', 'id', 'name', 'description', 'code')
        read_only_fields = ('code',)


class LanguageCountSerializer(serializers.Serializer):
    code = serializers.ChoiceField(
        choices=sorted([l[0] for l in get_languages(exclude=('en',))])
    )
    name = serializers.ChoiceField(
        choices=[l[1] for l in get_languages(exclude=('en',))]
    )
    count = serializers.IntegerField(
        min_value=0, help_text='Count of the translated works'
    )


class HeadingSerializer(serializers.ModelSerializer):
    number = serializers.IntegerField(min_value=1)
    limit = serializers.IntegerField(min_value=1)
    url = serializers.URLField()

    class Meta:
        model = models.OriginalSegment
        fields = (
            'id',
            'position',
            'tag',
            'classes',
            'content',
            'number',
            'limit',
            'url',
        )


class OriginalWorkSerializer(RelativeHyperlinkedSerializer):
    tags = serializers.StringRelatedField(many=True, read_only=True)
    table_of_contents = serializers.SerializerMethodField()

    @swagger_serializer_method(HeadingSerializer(many=True))
    def get_table_of_contents(self, obj):
        contents = list(obj.table_of_contents)
        count = len(contents)
        for i, heading in enumerate(contents):
            if i + 1 < count:
                limit = contents[i + 1]['position'] - heading['position']
            else:
                limit = obj.segments.count() - heading['position'] + 1
            url = '{}?limit={}&position={}'.format(
                reverse('originalsegment-list', args=(obj.pk,)),
                limit,
                heading['position'],
            )
            heading.update({'number': i + 1, 'limit': limit, 'url': url})
        return contents

    def validate_trustee(self, trustee):
        """
        Restrict to trustees where the user is a member.
        """
        user = self.context['request']._request.user
        if not trustee.members.filter(pk=user.pk).exists():
            raise serializers.ValidationError(
                _('You do not have permission to select this trustee.')
            )
        return trustee

    class Meta:
        model = models.OriginalWork
        fields = (
            'url',
            'id',
            'title',
            'subtitle',
            'abbreviation',
            'type',
            'description',
            'language',
            'trustee',
            'private',
            'created',
            'last_modified',
            'tags',
            # Differing
            'author',
            'published',
            'edition',
            'licence',
            'isbn',
            'publisher',
            'table_of_contents',
        )
        read_only_fields = ('abbreviation',)
        # todo: allow adding a work with an abbr.


class RequiredApprovalsSerializer(serializers.Serializer):
    translator = serializers.IntegerField(min_value=0, allow_null=True)
    reviewer = serializers.IntegerField(min_value=0, allow_null=True)
    trustee = serializers.IntegerField(min_value=0, allow_null=True)


class MinimalOriginalWorkSerializer(RelativeHyperlinkedSerializer):
    class Meta:
        model = models.OriginalWork
        fields = ('url', 'title', 'key')


class ChapterSerializer(serializers.ModelSerializer):
    segments = serializers.IntegerField(
        source='segments_count', min_value=0, required=False, allow_null=True
    )
    url = serializers.SerializerMethodField()

    @swagger_serializer_method(serializers.URLField(allow_blank=True))
    def get_url(self, obj):
        if not obj.first_position:
            return ''
        url = '{}?limit={}&position={}'.format(
            reverse('translatedsegment-list', args=(obj.work_id,)),
            obj.segments_count,
            obj.first_position,
        )
        return url

    class Meta:
        model = models.ImportantHeading
        fields = (
            'number',
            'url',
            'first_position',
            'position',
            'tag',
            'content',
            'pretranslated',
            'translation_done',
            'review_done',
            'trustee_done',
            'segments',
        )


class WorkStatisticsSerializer(serializers.ModelSerializer):
    pretranslated = serializers.IntegerField(
        source='pretranslated_count', min_value=0
    )
    translation_done = serializers.IntegerField(
        source='translated_count', min_value=0
    )
    review_done = serializers.IntegerField(source='reviewed_count', min_value=0)
    trustee_done = serializers.IntegerField(
        source='authorized_count', min_value=0
    )

    class Meta:
        model = models.WorkStatistics
        fields = (
            'pretranslated',
            'translation_done',
            'review_done',
            'trustee_done',
            'segments',
            'contributors',
        )


class TranslatedWorkSerializer(RelativeHyperlinkedSerializer):
    original = MinimalOriginalWorkSerializer(read_only=True)
    language = LanguageSerializer(read_only=True)
    author = serializers.CharField(
        source='original.author.name', read_only=True
    )
    tags = serializers.StringRelatedField(
        source='combined_tags',
        many=True,
        read_only=True,
        help_text='Includes tags of the original.',
    )
    required_approvals = RequiredApprovalsSerializer(read_only=True)
    statistics = WorkStatisticsSerializer(read_only=True)
    table_of_contents = ChapterSerializer(many=True, read_only=True)

    class Meta:
        model = models.TranslatedWork
        fields = (
            'url',
            'id',
            'title',
            'subtitle',
            'author',
            'abbreviation',
            'type',
            'description',
            'statistics',
            'language',
            'trustee',
            'private',
            'created',
            'last_modified',
            'tags',
            # Differing
            'original',
            'protected',
            'required_approvals',
            'table_of_contents',
        )
        read_only_fields = (
            'abbreviation',
            'type',
            'language',
            'trustee',
            'private',
            'original',
            'protected',
        )


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Tag
        fields = ('slug', 'name')


class WorkTypesSerializer(serializers.Serializer):
    slug = serializers.SlugField()
    name = serializers.CharField()
    count = serializers.IntegerField()


class PublishedSerializer(serializers.Serializer):
    min = serializers.IntegerField(allow_null=True)
    max = serializers.IntegerField(allow_null=True)


class TranslatedWorkFiltersSerializer(serializers.Serializer):
    types = WorkTypesSerializer(many=True)
    tags = TagSerializer(many=True)
    years = PublishedSerializer()


class TranslatedSegmentSwitchedSerializer(serializers.Serializer):
    prior_segment_id = serializers.IntegerField(allow_null=True, required=False)
    current_segment_id = serializers.IntegerField(
        allow_null=True, required=False
    )


class AuthorSerializer(RelativeHyperlinkedSerializer):
    name = serializers.ReadOnlyField()

    class Meta:
        model = models.Author
        fields = '__all__'


class LicenceSerializer(RelativeHyperlinkedSerializer):
    class Meta:
        model = models.Licence
        fields = '__all__'


class ReferenceSerializer(RelativeHyperlinkedSerializer):
    class Meta:
        model = models.Reference
        fields = '__all__'


class OriginalSegmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.OriginalSegment
        fields = (
            'id',
            'position',
            'page',
            'tag',
            'classes',
            'content',
            'reference',
            'work',
            'created',
            'last_modified',
        )
        read_only_fields = fields


class SegmentDraftSerializer(serializers.ModelSerializer):
    # I tried to get rid of defining (source and) queryset but that's buggy
    # because get_attribute isn't called always before accessing queryset
    segment_id = serializers.PrimaryKeyRelatedField(
        source='segment', queryset=models.TranslatedSegment.objects
    )

    class Meta:
        model = models.SegmentDraft
        fields = ('content', 'segment_id', 'created')
        read_only_fields = fields


class not_used_SegmentDraftSerializer(serializers.Serializer):
    segment_id = serializers.IntegerField()
    created = serializers.DateTimeField(read_only=True)
    content = serializers.CharField()

    def create(self, validated_data):
        """
        Lock segment and save draft.
        """
        user_id = validated_data['user_id']
        try:
            segment = models.TranslatedSegment.objects.select_for_update().get(
                Q(locked_by_id=None) | Q(locked_by_id=user_id),
                pk=validated_data['segment_id'],
            )
        except models.TranslatedSegment.DoesNotExist:
            raise serializers.ValidationError(
                _('Currently somebody else works on this segment.')
            )
        segment.locked_by_id = validated_data['user_id']
        segment.save()

        draft, created = models.SegmentDraft.objects.get_or_create(
            # position=segment.position,
            segment_id=validated_data['segment_id'],
            owner_id=validated_data['user_id'],
            work_id=segment.work_id,
        )
        change_counts = created or draft.last_modified <= segment.last_modified
        if change_counts and segment.content != validated_data['content']:
            raise serializers.ValidationError(
                _(
                    'Your content does not reflect the newest version. '
                    'Please reload your website.'
                )
            )
        snapshots = [
            {
                'created': timezone.now().isoformat(),
                'content': validated_data['content'],
            }
        ]
        # TODO
        # https://www.postgresql.org/docs/10/static/arrays.html#ARRAYS-MODIFYING
        # draft.snapshots = snapshot + F('snapshots')
        # draft.snapshots = Func(
        #    Func([snapshot], template='ARRAY%(expressions)s'),
        #    Func(F('snapshots'), template='ARRAY%(expressions)s'),
        #    template='SELECT %(expressions)s',
        #    arg_joiner=' || ',
        # )
        snapshots.extend(draft.snapshots)
        # import pdb;pdb.set_trace()
        import json

        draft.snapshots = json.dumps(snapshots)
        draft.save()


class VoteStatisticsSerializer(serializers.Serializer):
    vote = serializers.IntegerField(help_text='Accumulated votes.')
    user = serializers.IntegerField(help_text='Vote of the user.')


class SegmentStatisticSerializer(serializers.Serializer):
    # Comments
    comments = serializers.IntegerField(
        min_value=0, help_text='Number of comments.'
    )
    last_commented = serializers.DateTimeField(
        source='last_comment_date',
        # source='last_comment.created',
    )
    # History
    records = serializers.IntegerField(
        source='historical_records',
        min_value=0,
        help_text='Number of historical records.',
    )
    last_edited = serializers.DateTimeField(
        source='last_historical_record.history_date',
        allow_null=True,
        help_text='Date of the latest historical record.',
    )
    last_edited_by = UserFieldSerializer(
        source='last_historical_record.history_user', allow_null=True
    )
    # Votes
    translators = VoteStatisticsSerializer()
    reviewers = VoteStatisticsSerializer()
    trustees = VoteStatisticsSerializer()

    def to_representation(self, obj: models.TranslatedSegment):
        """
        Returns None in case the statistics where not retrieved.
        """
        if obj.has_statistics:
            return super().to_representation(obj)
        return None


class BaseTranslationSegmentSerializer(serializers.ModelSerializer):
    translator = serializers.CharField(source='translation.translator.name')
    info = serializers.SerializerMethodField()

    def get_info(self, obj) -> str:
        if obj.translation.translator.type == 'tm':
            text = (
                'This translation comes from the translation memory. That '
                'means the same or similar text was translated elsewhere '
                'already.'
            )
        elif obj.translation.translator.type == 'ai':
            text = (
                'This translation was created by '
                f'{obj.translation.translator.name}, an artificial '
                'intelligence.'
            )
        else:
            text = 'This translation was created by a third party.'
        return text

    class Meta:
        model = models.BaseTranslationSegment
        fields = ('translator', 'info', 'content')


class RetrieveTranslatedSegmentSerializer(serializers.ModelSerializer):
    original = serializers.CharField(source='original.content')
    reference = serializers.CharField(source='original.reference')
    chapter = serializers.IntegerField(
        source='chapter.number', allow_null=settings.TEST
    )
    chapter_position = serializers.IntegerField(
        allow_null=settings.TEST, help_text='Position within the chapter.'
    )
    work_abbreviation = serializers.SerializerMethodField(
        help_text='Abbreviation of the original work.'
    )
    ai = serializers.SerializerMethodField()
    locked_by = UserFieldSerializer()
    progress = serializers.IntegerField(
        min_value=BLANK,
        max_value=TRUSTEE_DONE,
        help_text='\n'.join(
            ('- `{}`: {}'.format(*s) for s in models.PROGRESS_STATES)
        ),
    )
    statistics = SegmentStatisticSerializer(source='*', read_only=True)
    translator_can_edit = serializers.SerializerMethodField()
    reviewer_can_edit = serializers.SerializerMethodField()
    reviewer_can_vote = serializers.SerializerMethodField(
        help_text='ToDo: Revokes are always allowed.'
    )
    trustee_can_vote = serializers.SerializerMethodField(
        help_text='ToDo: Revokes are always allowed.'
    )

    @swagger_serializer_method(BaseTranslationSegmentSerializer)
    def get_ai(self, obj: models.TranslatedSegment):
        # Convert it to tuple to prevent another query
        instances = tuple(
            filter(
                lambda bt: bt.translation.language == obj.work.language,
                obj.original.basetranslations.all(),
            )
        )
        if not instances:
            # No AI translation available
            return None
        assert len(instances) == 1, 'All other AIs should be filtered out.'
        serializer = BaseTranslationSegmentSerializer(instances[0])
        return serializer.data

    def get_translator_can_edit(self, obj) -> bool:
        return obj.can_edit('translator')

    def get_reviewer_can_edit(self, obj) -> bool:
        return obj.can_edit('reviewer')

    def get_reviewer_can_vote(self, obj) -> bool:
        return obj.can_vote('reviewer')

    def get_trustee_can_vote(self, obj) -> bool:
        return obj.can_vote('trustee')

    def get_work_abbreviation(self, obj) -> str:
        return obj.original.reference.split()[0]

    def to_representation(self, obj):
        """
        Removes the statistics key in case they where not retrieved.
        """
        ret = super().to_representation(obj)
        if ret.get('statistics') is None:
            ret.pop('statistics', None)
        return ret

    class Meta:
        model = models.TranslatedSegment
        fields = (
            'id',
            'position',
            'page',
            'tag',
            'classes',
            'content',
            'reference',
            'chapter',
            'chapter_position',
            'work_abbreviation',
            'work',
            'original',
            'ai',
            'progress',
            'translator_can_edit',
            'reviewer_can_edit',
            'reviewer_can_vote',
            'trustee_can_vote',
            'locked_by',
            'created',
            'last_modified',
            'statistics',
        )

        read_only_fields = (
            'tag',
            'classes',
            'content',
            'locked_by',
            'reference',
            'chapter',
            'chapter_position',
            'work_abbreviation',
            'work',
            'original',
            'ai',
            'progress',
        )
        extra_kwargs = {
            # 'original': {'lookup_field': 'position'},
        }


class LeanTranslatedSegmentSerializer(RetrieveTranslatedSegmentSerializer):
    class Meta(RetrieveTranslatedSegmentSerializer.Meta):
        fields = (
            'id',
            'position',
            'page',
            'tag',
            'classes',
            'content',
            'reference',
            'chapter',
            'chapter_position',
            'work_abbreviation',
            'work',
            'original',
            'ai',
            'progress',
            'locked_by',
            'created',
            'last_modified',
        )


class UpdateTranslatedSegmentSerializer(
    RequestResponseModelSerializer, RetrieveTranslatedSegmentSerializer
):
    last_modified = serializers.DateTimeField(
        help_text='Also required with `PATCH`.'
    )

    def get_value_or_raise_required(self, field, data):
        """
        Pops the value from data or raises a ValidationError.
        """
        try:
            return data.pop(field)
        except KeyError:
            raise serializers.ValidationError(
                {field: [_('This field is required.')]}
            )

    def to_internal_value(self, data):
        """
        Replaces and removes HTML and text characters and strings.
        """
        content = self.get_value_or_raise_required('content', data)
        data['content'] = sanitize_content(content, self.instance.work.language)
        return super().to_internal_value(data)

    def validate(self, data):
        # TODO
        # Check that you can't edit a segment in case
        # - it's private and you aren't a member
        # - you don't have the required permission for that language
        user = self.context['request'].user

        def get_segment():
            serializer = RetrieveTranslatedSegmentSerializer(
                self.instance.get_fresh_obj_with_stats(user)
            )
            return serializer.data

        # Translators are not allowed to edit the translation after a reviewer
        # approved and reviewers are not allowed to edit after a trustee
        # approved
        roles = reversed([r[0] for r in ROLES])
        role = None
        for r in roles:
            if not self.instance.can_edit(r):
                break
            role = r
        user.check_role(role, self.instance.work)

        # Check that the user has the newest version
        timestamp = self.get_value_or_raise_required('last_modified', data)
        if self.instance.locked_by_id is None:
            # todo: maybe even segment.last_modified != timestamp

            # This check is deactivated because it lead to the undesired
            # behaviour that a delayed saving was declined after you switched
            # segments
            # TODO Make the check more robust and activate it again
            # if self.instance.last_modified > timestamp:
            if False and timestamp:
                raise JsonValidationError(
                    {
                        'non_field_errors': [SEGMENT_CHANGED_ERROR_MESSAGE],
                        'segment': get_segment(),
                    }
                )

        # Check that nobody else edits the segment at the moment
        elif self.instance.locked_by_id != user.pk:
            raise JsonValidationError(
                {
                    'non_field_errors': [
                        _('Currently somebody else works on this segment.')
                    ],
                    'segment': get_segment(),
                }
            )

        return data

    def update(self, instance, validated_data):
        """
        Creates draft and saves segment.
        """
        user = self.context['request'].user
        drafts = []

        # Build initial draft
        # TODO cache!
        user_draft_exists = models.SegmentDraft.objects.filter(
            segment=instance, owner=user
        ).exists()
        # TODO add timestamp and create a new initial draft if
        # somebody else edited the segment in between
        # Is this possible at all? (with select_for_update?)

        if not user_draft_exists:
            drafts.append(
                models.SegmentDraft(
                    segment=instance,
                    owner=user,
                    content=instance.content,  # This is the old content
                    work=instance.work,
                    position=instance.position,
                )
            )

        # Build current draft
        drafts.append(
            models.SegmentDraft(
                segment=instance,
                owner=user,
                content=validated_data['content'],
                work=instance.work,
                position=instance.position,
            )
        )

        # Save drafts
        models.SegmentDraft.objects.bulk_create(drafts)

        # Save segment
        instance.content = validated_data['content']
        # Lock segment
        instance.locked_by = user
        instance.keep_votes_when_skipping_history = False
        # TODO with fields or even update
        instance.save_without_historical_record()
        instance.keep_votes_when_skipping_history = True

        # Add statistics
        if instance.votes_moved:
            instance = instance.get_fresh_obj_with_stats(user)
        # The 'edits' of the user are loaded separately in case the statistics
        # are not included because the user instance comes from the request
        # (causing another DB hit)

        # Add response fields
        self.convert_to_response()

        return instance

    class Meta:
        model = models.TranslatedSegment
        request_fields = ('content', 'last_modified')
        response_fields = request_fields + ('locked_by', 'statistics')


class VoteSerializer(
    RequestResponseModelSerializer, RelativeHyperlinkedSerializer
):
    type = serializers.ReadOnlyField(source=None, default='vote')
    timestamp = serializers.DateTimeField(
        write_only=True,
        help_text='The date when the segment was edited the last time.',
    )
    comment = serializers.CharField(write_only=True, required=False)
    user = UserFieldSerializer(read_only=True)

    # Request/response only fields
    set_to = serializers.IntegerField(min_value=-1, max_value=1)
    action = serializers.ChoiceField(
        choices=(
            'approved',
            'disapproved',
            'revoked approval',
            'revoked disapproval',
        )
    )
    assessment = serializers.IntegerField(min_value=-1, max_value=1)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        view = self.context.get('view')
        if view:
            self.segment = view.get_object()
            self.user = self.context['request'].user

    def validate_comment(self, content):
        """
        Validates that the user has permission to comment.
        """
        self.user.check_perms(self.segment.work, 'add_comment')
        return content

    def validate(self, data):
        """
        Validates that

        - the user has required permission and role
        - the segment isn't empty
        - the segment has required votes
        - the segment isn't locked
        - the timestamp is up-to-date
        - the user has a vote to revoke if requested
        - the user didn't vote yet (in given role and direction)
        """
        work = self.segment.work
        set_to = data.pop('set_to')

        # Permissions
        if data['role'] == 'translator':
            if set_to in (0, 1):
                # Revoking a vote doesn't have it's own permission.
                # Assuming following permission is the lowest in rank,
                # tie them to this permission (for now).
                self.user.check_perms(work, 'approve_translation')
            elif set_to == -1:
                # TODO What if a person votes this, and it is in review already
                # and brings this segment into a position where it can't
                # be reviewed
                self.user.check_perms(work, 'disapprove_translation')
            else:
                raise ValueError('set_to is invalid')
        else:
            self.user.check_role(data['role'], work)

        # Empty segments and required votes missing
        if not self.segment.can_vote(data['role']):
            if self.segment.progress == BLANK:
                # todo: Maybe change this to progress == IN_TRANSLATION
                # (when we have a reliable method to determine completeness)
                raise serializers.ValidationError(
                    _('Sorry, you can\'t vote empty paragraphs.')
                )
            if data['role'] == 'reviewer':
                previous_role = 'translator'
                group = _('translators')
            else:
                previous_role = 'reviewer'
                group = _('reviewers')
            required = self.segment.work.required_approvals[previous_role]
            msg = _(
                'Operation failed. There are not enough votes from {group} '
                '(currently {current} of required {required}).'
            )
            raise serializers.ValidationError(
                msg.format(
                    group=group,
                    current=getattr(
                        self.segment, '{}s_vote'.format(previous_role)
                    ),
                    required=required,
                )
            )

        # Locked segment
        if self.segment.locked_by_id is not None:
            # Also to reduce race conditions, see TranslatedSegment.save()
            raise serializers.ValidationError(
                _(
                    'Somebody is currently working on this paragraph. During '
                    'that time, you can\'t vote it.'
                )
            )

        # Timestamp outdated
        if data.pop('timestamp') < self.segment.last_modified:
            raise serializers.ValidationError(
                {'timestamp': SEGMENT_CHANGED_ERROR_MESSAGE}
            )

        # No vote to revoke, voted already and calculation of value and revoke

        # Table to check how to find out if somebody voted already
        # ------------------------------------------------------------------
        # Values     | revoke == False           | revoke == True
        #            | Allowed     | Not allowed | Allowed     | Not allowed
        # -----------|-------------|-------------|-------------|------------
        # -2 -1 = -3 |             | x           | Not applicable
        # -2 +0 = -2 | x           |             | Not applicable
        # -2 +1 = -1 | x           |             | Not applicable
        # -1 -1 = -2 |             | x           | x           |
        # -1 +0 = -1 | x           |             | 1)          |
        # -1 +1 =  0 | x           |             | x           |
        #  1 -1 =  0 | x           |             | x           |
        #  1 +0 =  1 | x           |             | 1)          |
        #  1 +1 =  2 |             | x           | x           |
        #  2 -1 =  1 | x           |             | Not applicable
        #  2 +0 =  2 | x           |             | Not applicable
        #  2 +1 =  3 |             | x           | Not applicable
        #
        # Notes:
        # - Revoke and the first number are from the last vote
        # - The second number is the set_to field from the request
        # 1) Error is raised in the second if clause below

        revoke = False
        error_message_nothing_to_revoke = serializers.ValidationError(
            _('There is no vote to revoke.')
        )
        votes = models.Vote.objects.filter(
            segment=self.segment, role=data['role'], user=self.user
        )
        try:
            last_vote = votes.latest()
        except models.Vote.DoesNotExist:
            # First vote
            if set_to == 0:
                raise error_message_nothing_to_revoke
        else:
            # Vote(s) existing
            if last_vote.revoke:
                if set_to == 0:
                    # Last vote was a revoke, too
                    raise error_message_nothing_to_revoke
            else:
                # Make sure user votes with one vote only (see table above)
                if abs(last_vote.value + set_to) > abs(last_vote.value):
                    raise serializers.ValidationError(
                        _('Sorry, you voted already and have one vote only.')
                    )
                # Opposite vote
                set_to *= 2
                # Revokes
                if set_to == 0:
                    set_to = -1 if last_vote.value > 0 else 1
                    revoke = True
        data['value'] = set_to
        data['revoke'] = revoke

        return data

    def create(self, validated_data):
        """
        Creates and returns vote and comment if applicable.
        """
        vote = models.Vote(
            segment=self.segment,
            user=self.user,
            role=validated_data['role'],
            value=validated_data['value'],
            revoke=validated_data['revoke'],
        )
        vote.full_clean()
        vote.save()

        if validated_data.get('comment'):
            comment = models.SegmentComment(
                content=validated_data['comment'],
                role=validated_data['role'],
                work=self.segment.work,
                position=self.segment.position,
                vote=vote,
                user=self.user,
            )
            comment.full_clean()
            comment.save()
        else:
            comment = None

        # Update the progress
        # It turned out that the query of the chapter statistics became too
        # complex if we don't denormalise it a bit (by updating the progress).
        # The good thing is that we have to update the segment anyway because
        # of the reason below.
        progress = self.segment.determine_progress(
            content=False, additional=vote
        )
        if progress is None:
            if self.segment.progress >= IN_REVIEW:
                # Allow translators to edit the segment (e.g. when a reviewer
                # - upvoted by mistake and then revokes his vote or
                # - upvoted and another reviewer downvotes)
                self.segment.progress = self.segment.determine_progress(
                    votes=False
                )
        else:
            self.segment.progress = progress

        # Mark the segment as changed to be retrieved when the frontend requests
        # updated segments.
        # I think this is more efficient than looking for updates in segments,
        # comments and votes (also when caching).
        self.segment.save_without_historical_record(
            update_fields=('last_modified', 'progress')
        )

        # Refresh segment to get (updated) statistics
        segment = self.segment.get_fresh_obj_with_stats(self.user)
        return {'vote': vote, 'comment': comment, 'segment': segment}

    class Meta:
        ref_name = 'Vote'
        model = models.Vote
        request_fields = ('role', 'set_to', 'timestamp', 'comment')
        response_fields = (
            'id',
            'type',
            'role',
            'action',
            'assessment',
            'date',
            'user',
        )


def get_history_field(name):
    return models.TranslatedSegment().history.model._meta.get_field(name)


class TranslatedSegmentHistorySerializer(RelativeHyperlinkedSerializer):
    id = serializers.ModelField(model_field=get_history_field('history_id'))
    type = serializers.ReadOnlyField(source=None, default='record')
    date = serializers.ModelField(model_field=get_history_field('history_date'))
    change_reason = serializers.ModelField(
        model_field=get_history_field('history_change_reason')
    )
    user = UserFieldSerializer(source='history_user')
    expires = serializers.SerializerMethodField()
    votes = VoteSerializer(many=True, is_response=True)

    def get_expires(self, obj) -> datetime:
        # These are the segment's votes (not the historical segment's votes).
        # The query is done for the first object at most. Therefore, it doesn't
        # make sense to add it as a Subquery.
        votes = models.Vote.objects.filter(segment_id=obj.id)
        if hasattr(obj, '_most_recent') and not votes.exists():
            return obj.history_date + constants.HISTORICAL_UNIT_PERIOD
        return None

    class Meta:
        model = models.TranslatedSegment.history.model
        fields = (
            'id',
            'relative_id',
            'date',
            'expires',
            'type',
            'change_reason',
            'user',
            'content',
            'votes',
        )
        read_only_fields = fields


class RestoreSerializer(RequestResponseSerializer):
    relative_id = serializers.IntegerField(
        min_value=1, allow_null=True, required=False
    )

    segment = RetrieveTranslatedSegmentSerializer()
    record = TranslatedSegmentHistorySerializer(
        help_text='The new created historical segment if created.'
    )
    deleted_relative_id = serializers.IntegerField(min_value=1)

    class Meta:
        request_fields = ('relative_id',)
        response_fields = ('segment', 'record', 'deleted_relative_id')


class BelongsToSerializer(serializers.Serializer):
    type = serializers.ReadOnlyField(source=None, default='vote')
    id = serializers.PrimaryKeyRelatedField(
        source='vote', read_only=True, pk_field=serializers.IntegerField()
    )


class SegmentCommentSerializer(CommentSerializer):
    type = serializers.ReadOnlyField(source=None, default='comment')
    belongs_to = BelongsToSerializer(
        source='*', read_only=True, help_text='A read-only field'
    )

    def validate_role(self, value):
        self.context['request'].user.check_role(
            value, self.context['view'].kwargs['parent_lookup_work']
        )
        return value

    class Meta(CommentSerializer.Meta):
        model = models.SegmentComment
        fields = CommentSerializer.Meta.fields + ['type', 'role', 'belongs_to']
        extra_kwargs = {'role': {'default': 'translator'}}


class SegmentCommentSegmentSerializer(serializers.Serializer):
    comment = SegmentCommentSerializer()
    segment = RetrieveTranslatedSegmentSerializer()


class VoteCommentSegmentSerializer(serializers.Serializer):
    vote = VoteSerializer(is_response=True)
    comment = SegmentCommentSerializer()
    segment = RetrieveTranslatedSegmentSerializer()


class VoteSegmentSerializer(serializers.Serializer):
    vote = VoteSerializer(is_response=True, source='*')
    segment = LeanTranslatedSegmentSerializer()


class CommentSegmentSerializer(serializers.Serializer):
    comment = SegmentCommentSerializer(source='*')
    segment = LeanTranslatedSegmentSerializer()


class VotesCommentsSegmentsSerializer(serializers.Serializer):
    votes = VoteSegmentSerializer(many=True)
    comments = CommentSegmentSerializer(many=True)
    segments = LeanTranslatedSegmentSerializer(many=True)
