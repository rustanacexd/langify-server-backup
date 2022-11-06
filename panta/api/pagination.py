from collections import OrderedDict

from drf_yasg import openapi
from rest_framework import pagination
from rest_framework.response import Response

from django.utils.translation import ugettext_lazy as _


class PositionPagination(pagination.LimitOffsetPagination):
    """
    Pagination with the smallest and a relative highest position as values.
    """

    # Adapted from DRF 3.8.2

    limit_query_description = _(
        'The first position not included anymore counted from the smallest to '
        'return for the page.'
    )
    offset_query_param = 'position'
    offset_query_description = _(
        'The smallest position to return for the page.'
    )
    max_limit = 1000

    def paginate_queryset(self, queryset, request, view=None):
        self.limit = self.get_limit(request)
        if self.limit is None:
            return None

        self.offset = self.get_offset(request)
        self.request = request

        # Offset + limit is the maximum position value
        queryset = queryset.filter(
            position__gte=self.offset, position__lt=self.offset + self.limit
        )
        return queryset

    def get_paginated_response(self, data):
        return Response(OrderedDict([('results', data)]))


class CursorCountPagination(pagination.CursorPagination):
    """
    Cursor pagination which counts the queryset.
    """

    def paginate_queryset(self, queryset, *args, **kwargs):
        self.queryset = queryset
        return super().paginate_queryset(queryset, *args, **kwargs)

    def get_paginated_response(self, data):
        """
        Returns the response of the page including a count on the first page.
        """
        previous = self.get_previous_link()
        if previous is None:
            count = self.queryset.count()
        else:
            count = None
        return Response(
            OrderedDict(
                [
                    ('next', self.get_next_link()),
                    ('previous', previous),
                    ('count', count),
                    ('results', data),
                ]
            )
        )


class HistoryPagination(CursorCountPagination):
    ordering = '-history_date'

    def paginate_queryset(self, queryset, *args, **kwargs):
        """
        Mark the most recent record to set the expiry date correctly.
        """
        query_list = super().paginate_queryset(queryset, *args, **kwargs)
        if not self.has_previous and query_list:
            query_list[0]._most_recent = True
        return query_list


class LimitPagination(pagination.LimitOffsetPagination):
    """
    Used only for limiting requests
    """

    max_limit = 50
    default_limit = 5


limit_param = openapi.Parameter(
    'limit',
    openapi.IN_QUERY,
    description='Number of results to return per type.',
    type=openapi.TYPE_INTEGER,
    default=5,
)
