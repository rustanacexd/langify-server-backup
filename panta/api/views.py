from copy import deepcopy

from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from rest_framework import (
    filters,
    generics,
    mixins,
    pagination,
    status,
    viewsets,
)
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny, DjangoObjectPermissions
from rest_framework.response import Response
from rest_framework.serializers import ValidationError
from rest_framework.views import APIView
from rest_framework_extensions.mixins import NestedViewSetMixin

from base.constants import get_languages
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import (
    Count,
    Max,
    Min,
    OuterRef,
    Prefetch,
    Q,
    Subquery,
    prefetch_related_objects,
)
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.decorators.cache import cache_control
from panta import constants, models
from panta.management import Segments
from panta.utils import assign_progress

from . import permissions, serializers
from .filters import (
    LastCommentsFilterSet,
    LastSegmentsFilterSet,
    LastVotesFilterSet,
    TranslatedWorkFilter,
    days_param,
)
from .pagination import (
    CursorCountPagination,
    HistoryPagination,
    LimitPagination,
    PositionPagination,
    limit_param,
)

User = get_user_model()


class TrusteeViewSet(
    NestedViewSetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    API endpoint for trustees.
    """

    queryset = models.Trustee.objects.all()
    serializer_class = serializers.TrusteeSerializer
    filter_backends = (
        DjangoFilterBackend,
        # filters.DjangoObjectPermissionsFilter,
        filters.OrderingFilter,
    )
    filterset_fields = ('name', 'members')
    permission_classes = (permissions.ObjectPermissions,)
    ordering_fields = ('name',)
    ordering = ('name',)


class LanguageView(APIView):
    """
    List languages

    Lists all possible languages of translations and a count of the works.
    """

    permission_classes = (AllowAny,)

    @swagger_auto_schema(
        responses={200: serializers.LanguageCountSerializer(many=True)},
        security=[],
    )
    def get(self, request, format=None):
        languages = get_languages(exclude=('en',))
        aggs = {l[0]: Count('pk', filter=Q(language=l[0])) for l in languages}
        counts = models.TranslatedWork.objects.aggregate(**aggs)

        serializer = serializers.LanguageCountSerializer(
            [{'code': c, 'name': n, 'count': counts[c]} for c, n in languages],
            many=True,
        )
        return Response(serializer.data)


class OriginalWorkViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    """
    API endpoint for original books or articles.

    list:
    Lists original books and articles, no authentication requried.

    retrieve:
    Retrieves an original book or article, no authentication requried.
    """

    queryset = models.OriginalWork.objects.all().prefetch_related('tags')
    serializer_class = serializers.OriginalWorkSerializer
    filter_backends = (
        DjangoFilterBackend,
        # filters.DjangoObjectPermissionsFilter,
        filters.OrderingFilter,
    )
    filterset_fields = ('language', 'author', 'published', 'trustee', 'private')
    permission_classes = (permissions.WorkPermissions,)
    ordering_fields = ('title', 'abbreviation', 'author')
    ordering = ('title',)


@method_decorator(name='retrieve', decorator=swagger_auto_schema(security=[]))
class TranslatedWorkViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    """
    API endpoint for translated books or articles.

    list:
    List works

    Lists translated books and articles. (No authentication required.)

    *Growing Together Series* books are added as dummies.

    *Table of contents* takes missing headings from the original.

    **Available filter fields**

    See below ("query parameters").

    Example http://example.com/api/products/?category=clothing&in_stock=true

    **Available sorting fields**

    See below (`ordering`).

    Example http://example.com/api/users/?ordering=account,-username

    **Search**

    For details see below.

    Example http://example.com/api/users/?search=russell

    create:
    Create work

    Creates a book or article with empty paragraphs corresponding to the
    original.

    retrieve:
    Retrieve work

    Retrieves a translated book or article, no authentication required.

    *Table of contents* takes missing headings from the original.

    update:
    Update work

    Updates a book or article.

    partial_update:
    Update work

    Updates a book or article.

    delete:
    Delete a work

    Deletes a work that doesn't have any segments or other objects depending on
    it.
    """

    queryset = models.TranslatedWork.objects.for_response().all()
    serializer_class = serializers.TranslatedWorkSerializer
    filter_backends = (
        DjangoFilterBackend,
        # filters.DjangoObjectPermissionsFilter,
    )
    filterset_class = TranslatedWorkFilter
    permission_classes = (permissions.WorkPermissions,)

    @cache_control(max_age=600, public=True)
    @swagger_auto_schema(
        security=[], manual_parameters=TranslatedWorkFilter.openapi_parameters
    )
    def list(self, request, *args, **kwargs):
        # Adds missing Growing Together works
        # This method should be removed as soon as not needed anymore
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        # NOTE: This does not respect other filters
        language_filter = 'language' in request.query_params
        protected = request.query_params.get('protected', True)
        if protected in (0, '0', 'false', 'False'):
            protected = False
        if language_filter and protected:
            works = (
                models.OriginalWork.objects.filter(
                    tags__name='Growing Together Series'
                )
                .select_related('author')
                .prefetch_related('tags')
                .annotate(segments_count=Count('segments'))
            )
            abbreviations = [o.abbreviation for o in page]
            for work in works:
                if work.abbreviation not in abbreviations:
                    work.statistics = {
                        'pretranslated_count': 0,
                        'translated_count': 0,
                        'reviewed_count': 0,
                        'authorized_count': 0,
                        'segments': work.segments_count,
                        'contributors': 0,
                    }
                    work.required_approvals = {
                        'translator': 0,
                        'reviewer': 0,
                        'trustee': 0,
                    }
                    work.protected = True
                    work.language = request.query_params['language']
                    work.original = work
                    work.combined_tags = work.tags.all()
                    work._table_of_contents = ()
                    page.append(work)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @swagger_auto_schema(
        responses={
            200: (
                '*An object with `prior` and `current` containing a segment '
                'object if requested or fail messages*'
            ),
            400: '*Validation errors*',
        }
    )
    @action(
        methods=['post'],
        detail=True,
        serializer_class=serializers.TranslatedSegmentSwitchedSerializer,
        permission_classes=(permissions.TranslatedSegmentPermissions,),
        url_path='switched-segments',
    )
    def switched_segments(self, request, pk=None):
        """
        Switched segments

        Unlocks the prior and responses with the prior and current segment
        (if specified).

        Responses with a *200 OK* even if there was an issue with a segment.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        prior_segment_pk = serializer.validated_data.get('prior_segment_id')
        current_segment_pk = serializer.validated_data.get('current_segment_id')

        # Unlock segment
        # Only unlock a specific segment (and not all) because the user could
        # work in multiple browser windows and these segments should stay
        # locked.
        if prior_segment_pk is not None:
            prior_segment = models.TranslatedSegment.objects.filter(
                work_id=pk, pk=prior_segment_pk, locked_by_id=request.user.pk
            )
            result = Segments().conclude(prior_segment)
        else:
            result = {'new': 0}

        # Response
        # TODO Filter for private works! Maybe with privileges.
        # Also at other places.
        queryset = (
            models.TranslatedSegment.objects.filter(
                work_id=pk, pk__in=(prior_segment_pk, current_segment_pk)
            )
            .select_related('original', 'chapter')
            .add_votes()
            .add_base_translations(pk)
        )
        if result['new'] > 0:
            # The current segment actually doesn't need stats but it is probably
            # more performant to do one query with stats than to have 2 queries
            # (one with stats and one without)
            queryset = queryset.add_stats(request.user)
        segments = {s.pk: s for s in queryset}
        context = {
            'request': self.request,
            'format': self.format_kwarg,
            'view': self,
        }
        # Prior segment
        prior_segment = segments.get(prior_segment_pk)
        if prior_segment:
            serializer = serializers.RetrieveTranslatedSegmentSerializer(
                prior_segment, context=context
            )
            prior = serializer.data
        else:
            prior = _('Prior segment not specified or not part of the work.')
        # Current segment
        current_segment = segments.get(current_segment_pk)
        if current_segment:
            serializer = serializers.RetrieveTranslatedSegmentSerializer(
                current_segment, context=context
            )
            current = serializer.data
        else:
            current = _(
                'Current segment not specified or not part of the work.'
            )
        return Response({'prior': prior, 'current': current})


class TranslatedWorkFiltersView(generics.RetrieveAPIView):
    serializer_class = serializers.TranslatedWorkFiltersSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ('language',)

    def get_queryset(self):
        pass

    @cache_control(max_age=600, public=True)
    def get(self, request, *args, **kwargs):
        """
        Query filters

        Retrieves available filter values for translated works for `type`,
        `tag`, `published_min` and `published_max`.

        You can filter by language to get language specific results (e.g.
        `language=tr`).
        """
        language = request.query_params.get('language')
        works = models.TranslatedWork.objects.all()
        tags = models.Tag.objects.all().order_by('name')
        if language:
            works = works.filter(language=language)
            tags = tags.distinct().filter(
                Q(translatedworks__language=language)
                | Q(originalworks__translations__language=language)
            )

        types = models.TranslatedWork.types
        count_lookups = {
            t[0]: Count('pk', filter=Q(type=t[0]), distinct=True) for t in types
        }
        aggregations = works.aggregate(
            min=Min('original__published'),
            max=Max('original__published'),
            **count_lookups,
        )
        type_dicts = [
            {'slug': t[0], 'name': t[1], 'count': aggregations[t[0]]}
            for t in types
        ]
        serializer = self.get_serializer(
            {'types': type_dicts, 'tags': tags, 'years': aggregations}
        )
        return Response(serializer.data)


class OriginalSegmentViewSet(
    NestedViewSetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    # mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    API endpoint for original paragraphs.
    """

    queryset = models.OriginalSegment.objects.all()
    lookup_field = 'position'
    lookup_value_regex = r'\d+'
    serializer_class = serializers.OriginalSegmentSerializer
    permission_classes = (permissions.OriginalSegmentPermissions,)
    pagination_class = PositionPagination


@method_decorator(
    name='partial_update',
    decorator=swagger_auto_schema(
        responses={
            200: serializers.UpdateTranslatedSegmentSerializer(
                is_response=True
            ),
            400: '*Validation errors*',
            403: (
                '*Votes of a higher role block editing*\n\n'
                '- Translators: `progress == "in review" or reviewers_vote >= '
                '  1 or trustees_vote >= 1`\n'
                '- Reviewers: `trustees_vote >= 1`\n'
                '- Trustees: *can always edit*'
            ),
        }
    ),
)
@method_decorator(name='partial_update', decorator=transaction.atomic)
class TranslatedSegmentViewSet(
    NestedViewSetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    API endpoint for translated paragraphs.

    list:
    List segments

    Lists segments of a work.

    retrieve:
    Retrieve segment

    Retrieves a heading or paragraph.

    partial_update:
    Update content

    Creates a draft and updates the segment. Sanitizes the content.

    Adds votes to the latest historical segment. Moves votes to the latest
    historical segment if `progress == RELEASED`.

    Checks that `lastModified` is equal to (or newer than) the date in the
    database to prevent overriding newer content with older content. Therefore,
    this key should not be changed by the frontend! The error message says that
    the "data was just updated automatically". This check is not done if the
    segment is locked by the user.

    Error response contains the `segment` in case the time stamp is outdated or
    somebody else works on the segment.

    destroy:
    Delete content

    Deletes the content of the segment and creates a seperate historical
    record if the content of the most recent historical record isn't empty.

    Responses with a *400 Bad Request* if the segment is locked by
    another user.
    """

    queryset = models.TranslatedSegment.objects.all()
    lookup_field = 'position'
    lookup_value_regex = r'\d+'
    serializer_class = serializers.RetrieveTranslatedSegmentSerializer
    filter_backends = (DjangoFilterBackend,)
    # TODO decide if needed: To include classes see
    # https://django-filter.readthedocs.io/en/master/
    # ref/filterset.html#customise-filter-generation-with-filter-overrides
    # AssertionError:
    # AutoFilterSet resolved field 'classes' with 'exact' lookup to an
    # unrecognized field type ArrayField. Try adding an override to
    # 'Meta.filter_overrides'.
    filterset_fields = {
        'last_modified': ('exact', 'lt', 'gt', 'lte', 'gte'),
        'page': ('exact', 'lte', 'gte'),
        'tag': ('exact', 'startswith'),
        'reference': ('exact', 'startswith'),
    }
    permission_classes = (permissions.TranslatedSegmentPermissions,)
    pagination_class = PositionPagination

    def get_queryset(self, *, annotations=False):
        qs = super().get_queryset()
        if annotations or self.request.method == 'GET':
            work_id = self.get_parents_query_dict()['work']
            qs = qs.for_response(work_id, self.request.user)
        elif self.request.method in ('POST', 'PUT', 'PATCH'):
            # TODO select_for_update for DELETE?
            qs = qs.select_related('work').add_votes().select_for_update()
            if self.request.method == 'PATCH':
                qs = qs.only(
                    'pk',
                    'position',
                    'content',
                    'work',
                    'locked_by',
                    'progress',
                    'last_modified',
                )
        return qs

    def add_last_historical_segment(self, queryset):
        history_manager = models.TranslatedSegment.history
        objects = list(queryset)

        # History
        pks = [s.pk for s in objects]
        historical_records = history_manager.filter(id__in=pks)
        last_records = (
            historical_records.filter(
                history_date=Subquery(
                    history_manager.filter(id=OuterRef('id'))
                    .values('id')
                    .annotate(last_record=Max('history_date'))
                    .values('last_record')[:1]
                )
            )
            .select_related('history_user')
            .only('id', 'history_date', 'history_user')
            .annotate(edits=Count('history_user__historicaltranslatedsegments'))
        )
        last_records = {o.id: o for o in last_records}

        for o in objects:
            record = last_records.get(o.pk)
            o.last_historical_record = record
            if record and record.history_user:
                record.history_user.edits = record.edits

        return objects

    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return serializers.UpdateTranslatedSegmentSerializer
        return super().get_serializer_class()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(
                self.add_last_historical_segment(page), many=True
            )
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(
            self.add_last_historical_segment(queryset), many=True
        )
        return Response(serializer.data)

    def perform_destroy(self, instance):
        """
        Clear content and create a historical record if the latest isn't empty.
        """
        if instance.locked_by_id in (None, self.request.user.pk):
            instance.content = ''
            instance.locked_by = None
            instance.changeReason = constants.CHANGE_REASONS['delete']
            if instance.history.latest().content == '':
                instance.save_without_historical_record()
            else:
                instance.save()
        else:
            raise ValidationError(
                _('Operation failed. The segment is currently locked.')
            )

    @swagger_auto_schema(
        responses={
            200: serializers.RestoreSerializer(is_response=True),
            400: '*Validation errors*',
        }
    )
    @action(
        methods=['post'],
        detail=True,
        serializer_class=serializers.RestoreSerializer,
    )
    def restore(self, request, parent_lookup_work=None, position=None):
        """
        Restore translation

        Restores a translation from the history (including votes, recalculates
        the progress).

        Adds a historical record if the chosen one isn't the most recent one.

        Allows to undo: contributors can restore the last historical record
        that isn't hot to delete the last (and hot) historical record and
        edits of the segment if the user is the author of the edits.
        To restore other historical records, you need proper privileges.

        An empty `POST` results in resetting the segment to the initial version
        (i.e. no content).

        Responses with a *200 OK* if

        - restoring was successful (with the object below) or
        - there is nothing to restore (with a text message). Thereby,
          prevents restoring the same historical record multiple times.

        Responses with a *400 Bad Request* if

        - the historical record is the most recent one and the segment is
        locked and not locked by the user and or
        - the segment is locked by anybody or
        - the review process has begun and `relativeId == null`.
        """
        # Edge cases (which actually can't happen):
        # - If there are several historical records in the hot period you can
        #   delete the newest only, one after the other
        # - If the segment content changed but is not locked you get the
        #   message "Nothing to restore."
        serializer = self.get_serializer_class()(data=request.data)
        serializer.is_valid(raise_exception=True)
        deleted_relative_id = None
        failed_response = Response(
            _('Operation failed. The segment is currently locked.'),
            status=status.HTTP_400_BAD_REQUEST,
        )

        with transaction.atomic():
            segment = self.get_object()
            if segment.locked_by_id and segment.locked_by_id != request.user.pk:
                return failed_response

            relative_id = serializer.validated_data.get('relative_id')
            try:
                most_recent_record = segment.history.latest()
            except segment.history.model.DoesNotExist:
                most_recent_record = None
                hot_and_owned = None
            else:
                is_hot = (
                    most_recent_record.history_date
                    + constants.HISTORICAL_UNIT_PERIOD
                ) >= timezone.now()
                is_owner = most_recent_record.history_user_id == request.user.pk
                hot_and_owned = is_hot and is_owner

            def reset_segment_content():
                if segment.locked_by is None:
                    return Response(_('Nothing to restore.'))
                segment.locked_by = None
                segment.save_without_historical_record()

            def delete_record_and_reset_content():
                most_recent_record.delete()
                # todo: Following behaviour is not consistent with the function
                # above
                segment.locked_by = None
                segment.save_without_historical_record()
                return most_recent_record.relative_id

            def reset_segment(historical_record, action):
                change_reason = constants.CHANGE_REASONS[action]
                if action == 'restore':
                    permission = 'restore_translation'
                    change_reason = change_reason.format(
                        id=historical_record.relative_id
                    )
                else:
                    permission = 'delete_translation'
                request.user.check_perms(segment.work, permission)
                # Don't reset a segment multiple times
                if most_recent_record.history_change_reason == change_reason:
                    if action == 'restore':
                        msg = _('Historical record restored already.')
                    else:
                        msg = _('Content was removed already.')
                    return Response(msg)

                if segment.locked_by:
                    return failed_response
                segment.changeReason = change_reason
                # Save and add a new historical record
                segment.save()
                segment.new_record = segment.get_history_for_serializer(
                    latest=True
                )
                # Restore votes
                if action == 'restore':
                    # Prevent having a segment multiple votes of the same user
                    users = historical_record.votes.values_list('user_id')
                    segment.votes.filter(user_id__in=users).update(segment=None)
                    # This has to be done after saving the segment. Otherwise,
                    # the votes might be removed again.
                    historical_record.votes.update(segment=segment)
                    # Reevaluate progress (necessary e.g. when you restore a
                    # segment with a review that was released in between).
                    # However, there is a funny edge case: A translator restores
                    # a segment because it is similar to the version he likes.
                    # But he wants to change something afterwards. This is not
                    # possible when the restored segment has a review because
                    # a translator has no permission to edit such segment.
                    qs = models.TranslatedSegment.objects.filter(pk=segment.pk)
                    assign_progress(qs)

            response = None

            # Undo everything or delete content
            if relative_id is None:
                if segment.progress >= constants.IN_REVIEW:
                    msg = _(
                        'Sorry, you cannot delete the content because the '
                        'segment was reviewed already.'
                    )
                    raise ValidationError(msg)

                segment.content = ''

                if hot_and_owned and segment.history.count() == 1:
                    # Reset segment content and delete historical record
                    # This creates no new record. Therefore, the check
                    # count == 1 is necessary here!
                    deleted_relative_id = delete_record_and_reset_content()
                elif most_recent_record is None:
                    # Reset segment content only
                    response = reset_segment_content()
                    # Delete floating record
                    deleted_relative_id = 1
                else:
                    try:
                        # Reset, adds historical record
                        historical_record = segment.history.get(
                            relative_id=most_recent_record.relative_id - 1
                        )
                    except segment.history.model.DoesNotExist:
                        # Reset segment content only (to last content)
                        segment.content = most_recent_record.content
                        response = reset_segment_content()
                        # Delete floating record
                        deleted_relative_id = most_recent_record.relative_id + 1
                    else:
                        response = reset_segment(historical_record, 'delete')

            # Restore or undo last changes
            else:
                historical_record = get_object_or_404(
                    segment.history, relative_id=relative_id
                )
                # At this point we know that most_recent_record != None
                segment.content = historical_record.content

                # Undo, deletes edits
                # Reset segment content only
                if historical_record.pk == most_recent_record.pk:
                    response = reset_segment_content()
                    # Delete floating record
                    if not hot_and_owned:
                        deleted_relative_id = most_recent_record.relative_id + 1

                        # In the other case, no new floating record was created
                        # This is a special case where you can undo changes
                        # to the last version in the history but it is the same
                        # historical segment in the timeline.

                # Reset segment content and delete historical record
                elif hot_and_owned and (
                    historical_record.relative_id
                    >= (most_recent_record.relative_id - 1)
                ):
                    deleted_relative_id = delete_record_and_reset_content()

                # Restore, adds historical record
                else:
                    response = reset_segment(historical_record, 'restore')

        # Response
        new_record = getattr(segment, 'new_record', None)
        # Get the segment with updated statistics
        segment = self.get_queryset(annotations=True).get(pk=segment.pk)
        serializer = serializers.RestoreSerializer(
            {
                'segment': segment,
                'record': new_record,
                'deleted_relative_id': deleted_relative_id,
            },
            context={
                'request': self.request,
                'format': self.format_kwarg,
                'view': self,
            },
            is_response=True,
        )
        return response or Response(serializer.data)

    @swagger_auto_schema(
        responses={
            201: serializers.VoteCommentSegmentSerializer,
            400: '*Validation Errors*',
        }
    )
    @action(
        methods=['post'],
        detail=True,
        serializer_class=serializers.VoteSerializer,
    )
    @transaction.atomic
    def vote(self, request, parent_lookup_work=None, position=None):
        """
        Votes

        Votes for translators, reviewers and trustees.

        `setTo` can have the following effects:

        1. `-1` sets the user's vote to *disapproval*
        2. `0` revokes the user's vote (equal to *not voted*)
        3. `1` sets the user's vote to *approval*

        This is represented by *one* vote object in the timeline in any of the
        three cases.

        Comments are separated into their own objects and created after the
        votes.

        Updates the segment's `progress` and touches the segment to get
        retrieved when requesting changed segments.

        Responses with a *400 Bad Request* (meaning that comments are also
        rejected) if

        - the segment doesn't have enough votes in the previous category
        - the segment is locked by somebody
        - the user voted already in this category and with this assessment
        - the time stamp is older than the database entry to prevent voting a
          text that the user doesn't see, the error message says that the "data
          was just updated automatically"
        - the segment is empty
        - revoking a *not voted* state
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        objects = serializer.save()
        serializer = serializers.VoteCommentSegmentSerializer(objects)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@method_decorator(
    name='get',
    decorator=swagger_auto_schema(
        operation_id='Translated Segments',
        operation_description=(
            'Lists translated segments by its language and original '
            'reference.'
        ),
    ),
)
class TranslatedSegmentByReferenceView(generics.ListAPIView):
    """
    List

    Lists translated segments by its language and original reference.
    """

    queryset = models.TranslatedSegment.objects.all()
    serializer_class = serializers.RetrieveTranslatedSegmentSerializer
    permission_classes = (permissions.TranslatedSegmentPermissions,)

    def get_queryset(self):
        queryset = (
            self.queryset.filter(
                work__language=self.kwargs['language'],
                original__reference=self.kwargs['reference'],
            )
            .select_related('chapter')
            .add_stats(self.request.user)
        )
        return queryset


class TimelineView(
    NestedViewSetMixin, mixins.ListModelMixin, viewsets.GenericViewSet
):
    """
    Timeline

    Lists the objects of the timeline of a given segment chronologically.
    """

    # TODO Check permissions!

    # todo: Maybe exclude objects which are older than 5 years or so
    # or which were made before the last two releases
    pagination_class = None

    @swagger_auto_schema(
        responses={
            200: (
                '*An array of '
                '[historical records]'
                '(#operation/translations_segments_history_list), '
                '[votes](#operation/translations_segments_vote) and '
                '[comments](#operation/translations_segments_comment_read)*'
            )
        }
    )
    def list(self, request, *args, **kwargs):
        segment = get_object_or_404(
            models.TranslatedSegment, **self.get_parents_query_dict()
        )
        # Comments
        objects = list(
            models.SegmentComment.objects.filter(
                Q(to_delete__isnull=True) | Q(user=request.user),
                **self.get_parents_query_dict(),
            )
            .annotate(edits=Count('user__historicaltranslatedsegments'))
            .select_related('vote', 'user')
        )
        for obj in objects:
            obj.user.edits = obj.edits
        # Historical records
        history = segment.get_history_for_serializer()
        # todo: When we add pagination to this endpoint, I could check that
        # _most_recent is set to True on the first page only (but I think it's
        # not mandatory, i.e. it doesn't cause an error in back- nor frontend).
        # See panta.api.pagination.HistoryPagination.paginate_queryset
        if history:
            history[0]._most_recent = True
            objects.extend(history)
            # Prepare objects for another 'prefetch_related'
            history = deepcopy(history)
            for r in history:
                r._prefetched_objects_cache = {}
        # Votes
        votes = list(
            segment.votes.annotate(
                edits=Count('user__historicaltranslatedsegments')
            ).select_related('user')
        )
        vote_pks = []
        for vote in votes:
            vote_pks.append(vote.pk)
            vote.user.edits = vote.edits
        objects.extend(votes)
        # Prevent votes from getting duplicated in timeline
        vote_qs = (
            models.Vote.objects.exclude(pk__in=vote_pks)
            .select_related('user')
            .annotate(edits=Count('user__historicaltranslatedsegments'))
        )
        prefetch_related_objects(history, Prefetch('votes', queryset=vote_qs))
        for record in history:
            objects.extend(record.votes.all())
        # Sort
        objects.sort(key=lambda o: o.created, reverse=True)
        # Serialize
        serialized_objects = []
        for obj in objects:
            # Comments
            if hasattr(obj, 'to_delete'):
                serializer = serializers.SegmentCommentSerializer(obj)
            # Historical records
            elif hasattr(obj, 'history_user'):
                serializer = serializers.TranslatedSegmentHistorySerializer(obj)
            # Votes
            else:
                serializer = serializers.VoteSerializer(obj, is_response=True)
            serialized_objects.append(serializer.data)
        return Response(serialized_objects)

    def get_queryset(self):
        """
        Returns None. Overridden to prevent AssertionError.
        """
        return


class TranslatedSegmentHistoryViewSet(
    NestedViewSetMixin, mixins.ListModelMixin, viewsets.GenericViewSet
):
    """
    API endpoint for the translated segments history.

    list:
    History

    Lists the historical records of a segment.

    A cursor paginated list beginning with the newest historical records.
    It includes a `count` field with a value on the first page.
    """

    queryset = models.TranslatedSegment.history.all()
    serializer_class = serializers.TranslatedSegmentHistorySerializer
    pagination_class = HistoryPagination
    ordering = '-history_date'

    def get_queryset(self):
        segment = get_object_or_404(
            models.TranslatedSegment, **self.get_parents_query_dict()
        )
        # filter should ensure the queryset is re-evaluated on each request
        # todo: This should be something like
        # return segment.get_history_for_serializer() (but that's a list)
        return self.queryset.filter(id=segment.id)


class SegmentDraftHistoryViewSet(
    NestedViewSetMixin, mixins.ListModelMixin, viewsets.GenericViewSet
):
    """
    API endpoint for the segment draft history.

    list:
    List drafts

    Lists the drafts of a segment of the authenticated user.
    """

    queryset = models.SegmentDraft.objects.all()
    serializer_class = serializers.SegmentDraftSerializer
    pagination_class = pagination.CursorPagination
    ordering = '-created'

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        return queryset.filter(owner_id=self.request.user.pk)


@method_decorator(
    name='partial_update',
    decorator=swagger_auto_schema(
        responses={
            200: serializers.SegmentCommentSegmentSerializer(),
            400: '*Validation errors*',
        }
    ),
)
class SegmentCommentViewSet(
    NestedViewSetMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    API endpoint for comments.

    list:
    List comments

    Lists comments of a segment. Excludes trashed comments when another user
    created them.

    A cursor paginated list beginning with the newest comments.
    It includes a `count` field with a value on the first page.

    create:
    Create comment

    Creates a comment for a segment. Touches the segment to get retrieved when
    requesting changed segments.

    retrieve:
    Retrieve comment

    Retrieves a comment. Excludes trashed comments when another user created
    them.

    update:
    Update comment

    Updates a comment created by the authenticated user.

    partial_update:
    Update comment

    Updates a comment created by the authenticated user.
    """

    queryset = models.SegmentComment.objects.all()
    serializer_class = serializers.SegmentCommentSerializer
    permission_classes = (permissions.SegmentCommentPermissions,)
    pagination_class = CursorCountPagination
    ordering = ('-created',)

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.method == 'GET':
            queryset = queryset.filter(
                Q(to_delete__isnull=True) | Q(user=self.request.user)
            )
        return queryset

    @swagger_auto_schema(
        responses={
            200: serializers.SegmentCommentSegmentSerializer(),
            400: '*Validation errors*',
        }
    )
    def create(self, request, *args, **kwargs):
        # Overridden to add the segment to the response
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        objects = self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        response = Response(
            serializers.SegmentCommentSegmentSerializer(objects).data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )
        return response

    def perform_create(self, serializer):
        work_id = self.kwargs['parent_lookup_work']
        segment = models.TranslatedSegment.objects.filter(
            work_id=work_id, position=self.kwargs['parent_lookup_position']
        )
        if not segment.exists():
            raise NotFound()
        comment = serializer.save(
            work_id=work_id,
            position=self.kwargs['parent_lookup_position'],
            user=self.request.user,
        )
        # Mark the segment as changed to be retrieved when the frontend requests
        # updated segments.
        segment.update(last_modified=timezone.now())
        segment = segment.for_response(work_id, self.request.user).get()
        return {'comment': comment, 'segment': segment}

    @swagger_auto_schema(
        responses={
            200: serializers.SegmentCommentSegmentSerializer(),
            400: '*Validation errors*',
        }
    )
    def update(self, request, *args, **kwargs):
        # Half of this is copied from DRF 3.9
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=partial
        )
        serializer.is_valid(raise_exception=True)
        comment = serializer.save()

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        work_id = self.kwargs['parent_lookup_work']
        segment = models.TranslatedSegment.objects.for_response(
            work_id, request.user
        ).get(work_id=work_id, position=self.kwargs['parent_lookup_position'])
        serializer = serializers.SegmentCommentSegmentSerializer(
            {'comment': comment, 'segment': segment}
        )
        return Response(serializer.data)


class AuthorViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    """
    API endpoint for authors.
    """

    queryset = models.Author.objects.all()
    serializer_class = serializers.AuthorSerializer
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter)
    filterset_fields = ('prefix', 'first_name', 'last_name', 'suffix', 'born')
    permission_classes = (DjangoObjectPermissions,)
    ordering_fields = ('prefix', 'first_name', 'last_name', 'suffix', 'born')
    ordering = ('last_name',)


class LicenceViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    """
    API endpoint for licences.
    """

    queryset = models.Licence.objects.all()
    serializer_class = serializers.LicenceSerializer
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter)
    filterset_fields = ('title',)
    permission_classes = (DjangoObjectPermissions,)
    ordering_fields = ('title',)
    ordering = ('title',)


class ReferenceViewSet(NestedViewSetMixin, viewsets.ModelViewSet):
    """
    API endpoint for references.
    """

    queryset = models.Reference.objects.all()
    serializer_class = serializers.ReferenceSerializer
    permission_classes = (DjangoObjectPermissions,)


class LastActivitiesViewSet(viewsets.GenericViewSet):
    """
    API endpoints for last activities.
    """

    serializer_class = serializers.VotesCommentsSegmentsSerializer
    filter_backends = (DjangoFilterBackend,)

    def get_segments(self, user):
        queryset = models.TranslatedSegment.objects.filter(
            past__history_user=user
        ).select_related('chapter', 'work', 'original')
        return queryset

    def get_votes(self, user):
        queryset = models.Vote.objects.filter(user=user).select_related(
            'segment',
            'segment__chapter',
            'segment__work',
            'segment__original',
            'user',
        )
        return queryset

    def get_comments(self, user):
        queryset = (
            models.SegmentComment.objects.filter(user=user)
            .select_related('user')
            .order_by('-last_modified')
        )
        return queryset

    @swagger_auto_schema(
        manual_parameters=[limit_param],
        responses={200: serializers.VotesCommentsSegmentsSerializer},
    )
    def list(self, request, *args, **kwargs):
        """
        Last activities

        Lists last activities of the user.
        """
        limit = LimitPagination().get_limit(request)

        segments = (
            self.get_segments(request.user)
            .filter(
                past__history_id__in=Subquery(
                    models.TranslatedSegment.history.distinct('chapter_id')
                    .filter(history_user=request.user)
                    .order_by('chapter_id', '-history_date')
                    .values('history_id')
                )
            )
            .order_by('-past__history_date')[:limit]
        )
        votes = (
            self.get_votes(request.user)
            .filter(
                id__in=Subquery(
                    models.Vote.objects.distinct('segment__chapter_id')
                    .filter(user=request.user)
                    .order_by('segment__chapter_id', '-date')
                    .values('pk')
                )
            )
            .order_by('-date')[:limit]
        )
        comments = self.get_comments(request.user)[:limit]

        serializer = self.get_serializer(
            {'votes': votes, 'comments': comments, 'segments': segments}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        manual_parameters=[days_param],
        responses={200: serializers.LeanTranslatedSegmentSerializer(many=True)},
    )
    @action(
        methods=['get'],
        detail=False,
        serializer_class=serializers.LeanTranslatedSegmentSerializer,
        queryset=models.TranslatedSegment.objects.all(),
    )
    def segments(self, request):
        """
        Segments

        Lists segments that the user edited sorted by date (the newest first).
        """

        self.filterset_class = LastSegmentsFilterSet
        segments = self.filter_queryset(
            self.get_segments(request.user).order_by('-past__history_date')
        )
        serializer = self.get_serializer(segments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        manual_parameters=[days_param],
        responses={200: serializers.VoteSegmentSerializer(many=True)},
    )
    @action(
        methods=['get'],
        detail=False,
        serializer_class=serializers.VoteSegmentSerializer,
        queryset=models.Vote.objects.all(),
    )
    def votes(self, request):
        """
        Votes

        Lists votes of the user sorted by date (the newest first).
        """

        self.filterset_class = LastVotesFilterSet
        votes = self.filter_queryset(
            self.get_votes(request.user).order_by('-date')
        )
        serializer = serializers.VoteSegmentSerializer(votes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        manual_parameters=[days_param],
        responses={200: serializers.CommentSegmentSerializer(many=True)},
    )
    @action(
        methods=['get'],
        detail=False,
        serializer_class=serializers.CommentSegmentSerializer,
        queryset=models.SegmentComment.objects.all(),
    )
    def comments(self, request):
        """
        Comments

        Lists comments of the user sorted by date (the newest first).
        """

        self.filterset_class = LastCommentsFilterSet
        comments = self.filter_queryset(self.get_comments(request.user))
        serializer = serializers.CommentSegmentSerializer(comments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
