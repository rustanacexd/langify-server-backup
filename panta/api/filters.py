from datetime import timedelta

from django_filters import rest_framework as filters
from drf_yasg import openapi

from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db.models import Case, IntegerField, Q, When
from django.forms import DateTimeField
from django.utils import timezone
from panta import models


class MultipleTagChoiceFilter(filters.ModelMultipleChoiceFilter):
    def filter(self, qs, value):
        if value:
            qs = qs.filter(
                Q(tags__in=value) | Q(original__tags__in=value)
            ).distinct()
        return qs


class WorkOrderingFilter(filters.OrderingFilter):
    def filter(self, qs, value):
        if value and ('priority' in value or '-priority' in value):
            # Order by translated work tagged with "priority"
            qs = qs.annotate(
                priority=Case(
                    When(tags__slug='priority', then=1),
                    default=2,
                    output_field=IntegerField(),
                )
            ).distinct()
        return super().filter(qs, value)


class TranslatedWorkFilter(filters.FilterSet):
    ordering_mapping = (
        ('title', 'title'),
        ('abbreviation', 'abbreviation'),
        ('priority', 'priority'),
        ('statistics__segments', 'segments'),
        ('statistics__pretranslated_percent', 'pretranslated'),
        ('statistics__translated_percent', 'translated'),
        ('statistics__reviewed_percent', 'reviewed'),
        ('statistics__authorized_percent', 'authorized'),
        ('statistics__contributors', 'contributors'),
        ('statistics__last_activity', 'last_activity'),
    )

    type = filters.MultipleChoiceFilter(choices=models.TranslatedWork.types)
    abbreviation = filters.CharFilter(
        field_name='abbreviation', lookup_expr='iexact'
    )
    author = filters.CharFilter(label='Author', field_name='original__author')
    published = filters.RangeFilter(
        label='Published (min/max)', field_name='original__published'
    )
    tag = MultipleTagChoiceFilter(
        label='Tag',
        field_name='tags__slug',
        to_field_name='slug',
        queryset=models.Tag.objects.all(),
    )
    is_pretranslated = filters.BooleanFilter(
        field_name='statistics__pretranslated_percent',
        method='get_boolean_filter',
    )
    is_translated = filters.BooleanFilter(
        field_name='statistics__translated_percent', method='get_boolean_filter'
    )
    is_reviewed = filters.BooleanFilter(
        field_name='statistics__reviewed_percent', method='get_boolean_filter'
    )
    is_authorized = filters.BooleanFilter(
        field_name='statistics__authorized_percent', method='get_boolean_filter'
    )
    ordering = WorkOrderingFilter(fields=ordering_mapping)
    search = filters.CharFilter(label='Search', method='get_search_filter')

    filters_endpoint = (
        '[filters endpoint](#operation/translations_filters_read)'
    )

    openapi_parameters = (
        openapi.Parameter(
            'type',
            openapi.IN_QUERY,
            description=(
                f'You can get them from the {filters_endpoint}. '
                'Filter by multiple values by reusing the same key: '
                '`type=book&type=periodical`. Conjunction: `OR`.'
            ),
            enum=[t[0] for t in models.TranslatedWork.types],
            type=openapi.TYPE_STRING,
        ),
        openapi.Parameter(
            'abbreviation',
            openapi.IN_QUERY,
            description='Case-insensitive',
            type=openapi.TYPE_STRING,
        ),
        openapi.Parameter(
            'published',
            openapi.IN_QUERY,
            description=(
                'You can\'t use this field but `published_min` and '
                '`published_max`. You can get the minimal and maximal values '
                f'from the {filters_endpoint}.'
            ),
            type=openapi.TYPE_INTEGER,
        ),
        openapi.Parameter(
            'tag',
            openapi.IN_QUERY,
            description=(
                f'You can get the values from the {filters_endpoint}. '
                'Filter by multiple values by reusing the same key. '
                'Conjunction: `OR`.'
            ),
            type=openapi.TYPE_STRING,
        ),
        openapi.Parameter(
            'protected', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN
        ),
        openapi.Parameter(
            'private', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN
        ),
        openapi.Parameter(
            'is_pretranslated', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN
        ),
        openapi.Parameter(
            'is_translated', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN
        ),
        openapi.Parameter(
            'is_reviewed', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN
        ),
        openapi.Parameter(
            'is_authorized', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN
        ),
        openapi.Parameter(
            'ordering',
            openapi.IN_QUERY,
            type=openapi.TYPE_ARRAY,
            items=openapi.Items(
                type=openapi.TYPE_STRING, enum=[f[1] for f in ordering_mapping]
            ),
        ),
        openapi.Parameter(
            'search',
            openapi.IN_QUERY,
            description=(
                'Searches the abbreviation and the title of the translation '
                'and of the original. Results are sorted by rank. Terms are '
                'treated as separate keywords.'
            ),
            type=openapi.TYPE_STRING,
        ),
    )

    def get_boolean_filter(self, queryset, name: str, value: bool):
        lookup = {name: 100}
        if value:
            return queryset.filter(**lookup)
        else:
            return queryset.exclude(**lookup)

    def get_search_filter(self, queryset, name, value):
        vector = (
            SearchVector('abbreviation', weight='A')
            + SearchVector('title', weight='B')
            + SearchVector('original__title', weight='C')
        )
        query = SearchQuery(value)
        queryset = (
            queryset.annotate(rank=SearchRank(vector, query))
            .filter(rank__gte=0.1)
            .order_by('-rank')
        )
        return queryset

    class Meta:
        model = models.TranslatedWork
        fields = (
            'title',
            'abbreviation',
            'type',
            'language',
            'author',
            'published',
            'tag',
            'trustee',
            'protected',
            'private',
            'is_pretranslated',
            'is_translated',
            'is_reviewed',
            'is_authorized',
            'ordering',
            'search',
        )


class DaysDurationField(DateTimeField):
    DAYS_DEFAULT = 30

    def to_python(self, value):
        if value in self.empty_values:
            value = self.DAYS_DEFAULT
        try:
            days = int(value)
        except ValueError:
            days = self.DAYS_DEFAULT
        return super().to_python(timezone.now() - timedelta(days=days))


class DaysDurationFilter(filters.DateTimeFilter):
    field_class = DaysDurationField


class LastSegmentsFilterSet(filters.FilterSet):
    days = DaysDurationFilter(
        field_name='past__history_date', lookup_expr='gte'
    )


class LastVotesFilterSet(filters.FilterSet):
    days = DaysDurationFilter(field_name='date', lookup_expr='gte')


class LastCommentsFilterSet(filters.FilterSet):
    days = DaysDurationFilter(field_name='last_modified', lookup_expr='gte')


days_param = openapi.Parameter(
    'days',
    openapi.IN_QUERY,
    description=(
        'Number of days to return objects created/modified within this '
        'period of time.'
    ),
    type=openapi.TYPE_INTEGER,
    default=30,
)
