from rest_framework import serializers

from base.serializers import CommentSerializer, UserFieldSerializer
from django.db.models import Count
from django.utils.translation import gettext as _
from style_guide import models
from style_guide.utils import DiffParser


class StyleGuideSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.StyleGuide
        fields = ('id', 'title', 'content', 'language')


class IssueSerializer(serializers.ModelSerializer):
    tags = serializers.StringRelatedField(many=True, read_only=True)
    user = UserFieldSerializer(read_only=True)
    style_guide = serializers.StringRelatedField(read_only=True)
    has_conflict = serializers.SerializerMethodField(read_only=True)
    style_guide_content = serializers.SerializerMethodField(allow_null=True)
    _has_conflict = None
    reactions_count = serializers.SerializerMethodField()

    def get_has_conflict(self, obj: models.Issue) -> bool:
        if self._has_conflict is None and obj.diff:
            diff = DiffParser(obj.diff)
            self._has_conflict = diff.has_conflict(obj.style_guide.content)
        else:
            self._has_conflict = False
        return self._has_conflict

    def get_style_guide_content(self, obj: models.Issue) -> str:
        if obj.diff and not self.get_has_conflict(obj):
            diff = DiffParser(obj.diff)
            return diff.apply(obj.style_guide.content)

    class Meta:
        model = models.Issue
        fields = (
            'id',
            'title',
            'content',
            'tags',
            'user',
            'style_guide',
            'created',
            'last_modified',
            'has_conflict',
            'is_from_style_guide',
            'style_guide_content',
            'reactions_count',
        )

    def get_reactions_count(self, obj):
        return obj.reactions.values('content').annotate(count=Count('content'))


class IssueRequestSerializer(serializers.ModelSerializer):
    style_guide_content = serializers.CharField(
        required=False, allow_blank=True
    )
    is_from_style_guide = serializers.BooleanField(
        required=False, default=False
    )

    class Meta:
        model = models.Issue
        fields = (
            'title',
            'content',
            'style_guide_content',
            'is_from_style_guide',
        )


class IssueCommentRequestSerializer(serializers.ModelSerializer):
    delete = serializers.NullBooleanField(
        required=False,
        write_only=True,
        help_text=(
            'True to mark the comment for deletion or false to remove the '
            'mark. Null is ignored.'
        ),
    )

    class Meta:
        model = models.IssueComment
        fields = ('content', 'delete')


class IssueCommentSerializer(CommentSerializer):
    issue = IssueSerializer(read_only=True)

    class Meta:
        model = models.IssueComment
        fields = [
            'id',
            'user',
            'issue',
            'created',
            'last_modified',
            'delete',
            'to_delete',
            'content',
        ]
        read_only_fields = ('to_delete', 'user')


class IssueReactionSerializer(serializers.ModelSerializer):
    def validate(self, data):
        issue_id = self.context['issue_id']
        user = self.context['user']
        if models.IssueReaction.objects.filter(
            content=data['content'], user=user, issue=issue_id
        ).exists():
            raise serializers.ValidationError(
                _("Sorry, you have already used this reaction.")
            )

        return data

    class Meta:
        model = models.IssueReaction
        fields = ['id', 'user', 'issue', 'created', 'last_modified', 'content']
        read_only_fields = ('user', 'issue')
