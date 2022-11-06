from drf_yasg.utils import swagger_auto_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework_extensions.mixins import NestedViewSetMixin

from base import constants
from django.http import Http404
from django.utils.decorators import method_decorator
from misc.api import IsOwnerOrReadOnlyPermissions
from panta.api.pagination import CursorCountPagination
from style_guide import models, utils
from style_guide.api import permissions, serializers


class StyleGuideView(viewsets.GenericViewSet, mixins.RetrieveModelMixin):
    """
    Retrieve

    Retrieves style guide object by language
    """

    queryset = models.StyleGuide.objects.all()
    serializer_class = serializers.StyleGuideSerializer
    lookup_field = 'language'

    def retrieve(self, request, *args, **kwargs):
        active_languages = tuple(lang[0] for lang in constants.ACTIVE_LANGUAGES)
        try:
            return super().retrieve(request, args, kwargs)
        except Http404 as e:
            if kwargs[self.lookup_field] in active_languages:
                style_guide, _ = models.StyleGuide.objects.get_or_create(
                    language=kwargs[self.lookup_field]
                )
                serializer = self.get_serializer(style_guide)
                return Response(serializer.data)
            else:
                raise e


@method_decorator(
    name='create',
    decorator=swagger_auto_schema(
        request_body=serializers.IssueRequestSerializer,
        responses={'201': serializers.IssueSerializer()},
    ),
)
class IssueViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    """
    API endpoints for style guide issues.

    list:
    List issues

    Lists issues for a style guide.

    retrieve:
    Retrieve issue

    Retrieves an issue.

    create:
    Create issue

    Creates an issue for a style guide.

    update:
    Update issue

    Updates an issue.

    partial_update:
    Update issue

    Updates an issue.

    destroy:
    Delete issue

    Deletes an issue.
    """

    queryset = (
        models.Issue.objects.all()
        .prefetch_related('tags')
        .select_related('user', 'style_guide')
    )
    serializer_class = serializers.IssueSerializer
    permission_classes = (permissions.IsIssueOwnerOrReviewer,)

    def perform_create(self, serializer):
        style_guide = get_object_or_404(
            models.StyleGuide,
            language=self.kwargs['parent_lookup_style_guide__language'],
        )
        modified = self.request.data.get('style_guide_content', None)
        diff = utils.process_diff(style_guide.content, modified)
        serializer.save(
            user=self.request.user, style_guide=style_guide, diff=diff
        )

    def perform_update(self, serializer):
        style_guide = get_object_or_404(
            models.StyleGuide,
            language=self.kwargs['parent_lookup_style_guide__language'],
        )
        modified = self.request.data.get('style_guide_content', None)
        diff = utils.process_diff(style_guide.content, modified)
        serializer.save(
            user=self.request.user, style_guide=style_guide, diff=diff
        )


@method_decorator(
    name='create',
    decorator=swagger_auto_schema(
        request_body=serializers.IssueCommentRequestSerializer,
        responses={'201': serializers.IssueCommentSerializer()},
    ),
)
class IssueCommentViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    """
    API endpoints for style guide issue comments.

    list:
    List comments

    Lists comments for an issue.

    retrieve:
    Retrieve comment

    Retrieves a comment for an issue.

    create:
    Create comment

    Creates a comment for an issue.

    update:
    Update comment

    Updates a comment for an issue.

    partial_update:
    Update comment

    Updates a comment for an issue.

    destroy:
    Delete comment

    Deletes a comment for an issue.
    """

    queryset = models.IssueComment.objects.all().select_related('user', 'issue')
    serializer_class = serializers.IssueCommentSerializer
    permission_classes = (IsOwnerOrReadOnlyPermissions,)
    pagination_class = CursorCountPagination
    ordering = ('-created',)

    def perform_create(self, serializer):
        issue_id = self.kwargs['parent_lookup_issue']
        serializer.save(user=self.request.user, issue_id=issue_id)


class IssueReactionViewSet(
    NestedViewSetMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """
    API endpoints for style guide issue reaction.

    list:
    List reactions

    Lists reactions for an issue.

    create:
    Create reaction

    Creates a reaction for an issue.

    """

    queryset = models.IssueReaction.objects.all()
    serializer_class = serializers.IssueReactionSerializer
    permission_classes = (IsOwnerOrReadOnlyPermissions,)
    pagination_class = CursorCountPagination
    ordering = ('-created',)

    def perform_create(self, serializer):
        issue_id = self.kwargs['parent_lookup_issue']
        serializer.save(user=self.request.user, issue_id=issue_id)

    def get_serializer_context(self):
        issue_id = self.kwargs['parent_lookup_issue']
        context = super().get_serializer_context()
        context['issue_id'] = issue_id
        context['user'] = self.request.user
        return context

    @action(detail=False, methods=['DELETE'], url_path='delete-reaction')
    def delete_reaction(self, request, *args, **kwargs):
        try:
            issue_reaction = models.IssueReaction.objects.filter(
                user=self.request.user,
                issue=kwargs['parent_lookup_issue'],
                content=request.data['content'],
            ).get()
            issue_reaction.delete()
        except models.IssueReaction.DoesNotExist:
            raise NotFound()

        return Response({}, status=status.HTTP_204_NO_CONTENT)
