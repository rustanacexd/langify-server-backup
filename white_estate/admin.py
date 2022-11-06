from django.contrib import admin
from django.db.models import Count, F, Q

from . import models


@admin.register(models.Class)
class ClassAdmin(admin.ModelAdmin):
    ordering = ('name', 'tag__name')
    list_display = ('name', 'tag', 'count')
    readonly_fields = ('name', 'tag', 'segments')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.annotate(count=Count('segments', distinct=True))
        return qs

    def count(self, obj):
        return obj.count


@admin.register(models.Tag)
class TagAdmin(admin.ModelAdmin):
    ordering = ('name',)
    list_display = ('name', 'count', 'inline')
    readonly_fields = ('name', 'segments')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.annotate(
            total_count=Count('segments', distinct=True),
            # segment.tag != tag.name -> tag is inline
            inline_count=Count(
                'segments', filter=~Q(segments__tag=F('name')), distinct=True
            ),
        )
        return qs

    def count(self, obj):
        return obj.total_count

    def inline(self, obj):
        """
        Segments which (should) have the tag at least one time inline.
        """
        return obj.inline_count


@admin.register(models.OriginalSentence)
class SentenceAdmin(admin.ModelAdmin):
    ordering = ('-count',)
    list_display = ('__str__', 'count')
    readonly_fields = ('segments',)
    list_filter = ('segments__work',)
