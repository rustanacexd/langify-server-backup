from django.db import models
from django.db.models import Count, F, OuterRef, Prefetch, Q, Subquery, Sum


def get_vote_subquery(role, user=None):
    from .models import Vote

    filter_fields = {'role': role}
    if user:
        filter_fields.update({'user': user})
    subquery = Subquery(
        Vote.objects.filter(segment=OuterRef('pk'), **filter_fields)
        .values('segment_id')
        .annotate(sum=Sum('value'))
        .values('sum')[:1],
        output_field=models.IntegerField(),
    )
    return subquery


class SubqueryCount(Subquery):
    template = "(SELECT count(*) FROM (%(subquery)s) _count)"
    output_field = models.IntegerField()


class SubquerySum(Subquery):
    template = '(SELECT sum(%(field)s) FROM (%(subquery)s) _sum)'
    output_field = models.IntegerField()


class TranslatedSegmentQuerySet(models.QuerySet):
    def add_2_votes(self):
        """
        Adds 'reviewers_vote' and 'trustees_vote' annotations.
        """
        queryset = self.annotate(
            reviewers_vote=get_vote_subquery('reviewer'),
            trustees_vote=get_vote_subquery('trustee'),
        )
        return queryset

    def add_votes(self):
        """
        Adds 'translators_vote', 'reviewers_vote' and 'trustees_vote'
        annotations.
        """
        queryset = self.annotate(
            translators_vote=get_vote_subquery('translator'),
            reviewers_vote=get_vote_subquery('reviewer'),
            trustees_vote=get_vote_subquery('trustee'),
        )
        return queryset

    def add_stats(self, user):
        """
        Adds numbers of comments and total and user votes in the 3 categories
        and the last commented date.
        """
        from .models import SegmentComment

        history = self.model.history
        queryset = self.add_votes().annotate(
            comments=Count(
                'work__segmentcomments',
                filter=Q(
                    work__segmentcomments__position=F('position'),
                    work__segmentcomments__to_delete__isnull=True,
                ),
                distinct=True,
            ),
            last_comment_date=Subquery(
                SegmentComment.objects.filter(
                    work=OuterRef('work'),
                    position=OuterRef('position'),
                    to_delete__isnull=True,
                )
                .order_by('-created')
                .values('created')[:1]
            ),
            # It turned out that subqueries are faster than counts (because
            # we needed twice as much). For details see the Jupyter notebook
            # on queries.
            user_translator_vote=get_vote_subquery('translator', user),
            user_reviewer_vote=get_vote_subquery('reviewer', user),
            user_trustee_vote=get_vote_subquery('trustee', user),
            historical_records=SubqueryCount(history.filter(id=OuterRef('pk'))),
        )
        return queryset

    def add_base_translations(self, work_id):
        """
        Adds the language specific base translation.
        """
        from .models import BaseTranslationSegment, TranslatedWork

        # Make sure the value is an integer and thereby safe
        work_id = int(work_id)
        queryset = self.prefetch_related(
            Prefetch(
                'original__basetranslations',
                queryset=(
                    BaseTranslationSegment.objects.filter(
                        translation__language=Subquery(
                            TranslatedWork.objects.filter(pk=work_id).values(
                                'language'
                            )[:1]
                        )
                    ).select_related('translation__translator')
                ),
            )
        )
        return queryset

    def for_response(self, work_id, user):
        """
        Adds base translation, statistics and selects related fields
        necessary for an API response.
        """

        queryset = (
            self.add_base_translations(work_id)
            .add_stats(user)
            .select_related('work', 'original', 'chapter')
        )
        return queryset


class TranslatedWorkQuerySet(models.QuerySet):
    def for_response(self):
        from .models import ImportantHeading

        queryset = self.select_related(
            'original', 'statistics'
        ).prefetch_related(
            'tags',
            'original__tags',
            'original__author',
            Prefetch(
                'important_headings',
                queryset=ImportantHeading.objects.order_by('position'),
            ),
        )
        return queryset
