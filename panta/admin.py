from simple_history.admin import SimpleHistoryAdmin

from django.contrib import admin
from django.utils.safestring import mark_safe
from django.utils.text import Truncator
from django.utils.translation import ugettext_lazy as _

from . import models


class Content:
    def content_truncated(self, obj):
        return Truncator(obj.content).chars(50)

    content_truncated.admin_order_field = 'content'
    content_truncated.short_description = _('content')


@admin.register(models.OriginalWork)
class WorkAdmin(SimpleHistoryAdmin):
    list_display = ('__str__', 'abbreviation', 'type', 'published')
    list_filter = ('type', 'tags', 'published')
    search_fields = ('=abbreviation', 'title')
    filter_horizontal = ('tags',)


@admin.register(models.TranslatedWork)
class TranslatedWorkAdmin(WorkAdmin):
    list_display = ('__str__', 'abbreviation', 'type', 'language')
    list_filter = ('type', 'language', 'tags', 'original__tags')
    actions = ('update_headings', 'recreate_headings')

    def update_headings(self, request, queryset):
        count = 0
        for work in queryset:
            count += models.ImportantHeading.update(
                models.ImportantHeading.objects.filter(work=work)
            )
        self.message_user(
            request, _('Updated {count} headings.').format(count=count)
        )

    update_headings.short_description = _('Update headings')

    def recreate_headings(self, request, queryset):
        _total, details = models.ImportantHeading.objects.filter(
            work__in=queryset.values('pk')
        ).delete()
        deleted = details['panta.ImportantHeading'] if details else 0
        created = 0
        for work in queryset:
            created += len(models.ImportantHeading.insert(work))
        self.message_user(
            request,
            _('Deleted {} and created {} headings.').format(deleted, created),
        )

    recreate_headings.short_description = _('Recreate headings')


class SegmentAdmin(SimpleHistoryAdmin, Content):
    list_display = (
        '__str__',
        'work',
        'position',
        'tag',
        'classes',
        'content_truncated',
    )
    readonly_fields = ('content_rendered',)
    list_filter = ('work__type', 'tag', 'work__title')
    search_fields = ('content',)
    raw_id_fields = ('work',)

    def content_rendered(self, obj):
        return mark_safe(obj.content)

    content_rendered.short_description = _('rendered')


@admin.register(models.OriginalSegment)
class OriginalSegmentAdmin(SegmentAdmin):
    fields = (
        ('content', 'content_rendered'),
        'work',
        'page',
        'position',
        ('tag', 'classes'),
        ('reference', 'key'),
    )
    readonly_fields = ('content_rendered', 'key')


class VoteInline(admin.TabularInline):
    model = models.Vote
    fields = ('segment', 'role', 'value', 'user', 'date')
    readonly_fields = ('date',)
    raw_id_fields = ('user',)
    extra = 0
    show_change_link = True


@admin.register(models.TranslatedSegment)
class TranslatedSegmentAdmin(SegmentAdmin):
    list_display = SegmentAdmin.list_display + ('ratio', 'last_modified')
    fields = (
        'content',
        'original_content',
        'content_rendered',
        'work',
        'page',
        'position',
        'tag',
        'classes',
        'reference',
        'original',
        'chapter',
        'locked_by',
        'progress',
        'last_modified',
        'created',
    )
    readonly_fields = (
        'original_content',
        'content_rendered',
        'last_modified',
        'created',
    )
    list_filter = ('work__language', 'tag', 'progress', 'work__title')
    raw_id_fields = SegmentAdmin.raw_id_fields + (
        'original',
        'locked_by',
        'chapter',
    )
    list_select_related = ('work', 'original')
    inlines = (VoteInline,)

    def original_content(self, obj):
        return mark_safe(obj.original.content)

    original_content.short_description = _('original')

    def ratio(self, obj):
        if obj.original.content:
            return round(len(obj.content) / len(obj.original.content), 3)
        return ''

    ratio.short_description = _('ratio')


@admin.register(models.Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'segment', 'role', 'revoke', 'user', 'date')
    raw_id_fields = ('segment', 'user', 'historical_segments')
    list_select_related = ('segment', 'user')
    list_filter = ('value', 'role', 'revoke', 'date', 'segment__work')


class BaseTranslationInline(admin.TabularInline):
    model = models.BaseTranslation
    extra = 0


@admin.register(models.BaseTranslator)
class BaseTranslatorAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'type')
    inlines = (BaseTranslationInline,)


@admin.register(models.BaseTranslationSegment)
class BaseTranslationSegmentAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'position', 'translator', 'language')
    list_filter = (
        'original__work__title',
        'translation__translator',
        'translation__language',
    )
    list_select_related = ('original', 'translation__translator')
    raw_id_fields = ('original',)
    readonly_fields = (
        'original_content',
        'human_translation',
        'original_rendered',
        'ai_translation_rendered',
        'human_translation_rendered',
    )

    def position(self, obj):
        return obj.original.position

    position.short_description = _('position')
    position.admin_order_field = 'original__position'

    def translator(self, obj):
        return obj.translation.translator.name

    translator.short_description = _('translator')
    translator.admin_order_field = 'translation__translator__name'

    def language(self, obj):
        return obj.translation.language

    language.short_description = _('language')
    language.admin_order_field = 'translation__language'

    def original_content(self, obj):
        return obj.original.content

    original_content.short_description = _('original content')

    def human_translation(self, obj):
        translations = tuple(
            obj.original.translations.filter(
                work__language=obj.translation.language
            )
        )
        if translations:
            return translations[0].content
        else:
            return self.empty_value_display

    human_translation.short_description = _('human translation')

    def original_rendered(self, obj):
        return mark_safe(obj.original.content)

    original_rendered.short_description = _('original rendered')

    def ai_translation_rendered(self, obj):
        return mark_safe(obj.content)

    ai_translation_rendered.short_description = _('AI translation rendered')

    def human_translation_rendered(self, obj):
        return mark_safe(self.human_translation(obj))

    human_translation_rendered.short_description = _(
        'human translation rendered'
    )


@admin.register(models.SegmentDraft)
class SegmentDraftAdmin(admin.ModelAdmin, Content):
    list_display = (
        '__str__',
        'position',
        'owner',
        'created',
        'content_truncated',
    )
    # list_filter = ('created',)
    search_fields = [
        '=work__abbreviation',
        '^work__title',
        '=position',
        '=segment__reference',
        '^owner__username',
        '^owner__first_name',
        '^owner__last_name',
        'content',
    ]
    raw_id_fields = ('segment', 'owner')


@admin.register(models.SegmentComment)
class SegmentCommentAdmin(admin.ModelAdmin):
    list_display = (
        '__str__',
        'role',
        'work',
        'position',
        'user',
        'last_modified',
        'to_delete',
    )
    search_fields = ('content', '^user__username')
    readonly_fields = ('last_modified', 'created')
    raw_id_fields = ('vote', 'user')


@admin.register(models.ImportantHeading)
class ImportantHeadingAdmin(admin.ModelAdmin):
    list_display = (
        '__str__',
        'number',
        'tag',
        'first_position',
        'segment',
        'segments_count',
        'date',
    )
    list_filter = ('tag', 'work', 'work__language')
    actions = ('update_headings',)
    raw_id_fields = ('segment',)

    def update_headings(self, request, queryset):
        count = models.ImportantHeading.update(queryset)
        self.message_user(
            request, _('Updated {count} headings.').format(count=count)
        )

    update_headings.short_description = _('Update headings')


@admin.register(models.WorkStatistics)
class WorkStatisticsAdmin(admin.ModelAdmin):
    list_display = (
        '__str__',
        'segments',
        'pretranslated_percent',
        'translated_percent',
        'reviewed_percent',
        'authorized_percent',
        'contributors',
        'last_activity',
    )
    list_filter = (
        'work__type',
        'last_activity',
        'work__language',
        'pretranslated_percent',
        'translated_percent',
        'reviewed_percent',
        'authorized_percent',
    )
    search_fields = ('work__title', '=work__abbreviation')


@admin.register(models.Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'slug')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


admin.site.register(models.Author, SimpleHistoryAdmin)
# admin.site.register(models.Cachet, SimpleHistoryAdmin)
# admin.site.register(models.Definition, SimpleHistoryAdmin)
# admin.site.register(models.Issue, SimpleHistoryAdmin)
admin.site.register(models.Licence, SimpleHistoryAdmin)
admin.site.register(models.Reference, SimpleHistoryAdmin)
# admin.site.register(models.Release, SimpleHistoryAdmin)
admin.site.register(models.Trustee, SimpleHistoryAdmin)
