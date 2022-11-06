from simple_history.admin import SimpleHistoryAdmin

from django.contrib import admin
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from frontend_urls import PAGE

from . import models


class AttachmentInline(admin.TabularInline):
    model = models.Attachment
    extra = 0


@admin.register(models.Page)
class PageAdmin(SimpleHistoryAdmin):
    list_display = ('slug', 'public', 'contact_button')
    fieldsets = (
        (None, {'fields': ('slug', 'public', 'contact_button', 'content')}),
        (
            'Rendered',
            {
                'classes': ('collapse',),
                'fields': ('rendered', 'protected', 'interpreted'),
            },
        ),
    )
    readonly_fields = (
        'rendered',
        'protected',
        'interpreted',
        'last_modified',
        'created',
    )
    search_fields = ('content',)
    inlines = (AttachmentInline,)

    def interpreted(self, obj):
        return mark_safe(obj.rendered)

    interpreted.short_description = _('interpreted')

    def view_on_site(self, obj):
        page_url = PAGE.format(slug=obj.slug)
        return f'/{page_url}'

    def get_readonly_fields(self, request, obj=None):
        default_readonly_fields = super().get_readonly_fields(request, obj)
        if request.user.is_superuser or obj is None:
            return default_readonly_fields
        return default_readonly_fields + ('slug',)


@admin.register(models.DeveloperComment)
class DeveloperCommentAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'user', 'last_modified', 'to_delete')
    search_fields = ('content', '^user__username')
    readonly_fields = ('last_modified', 'created')
