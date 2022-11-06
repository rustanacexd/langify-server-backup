from simple_history.admin import SimpleHistoryAdmin

from django.contrib import admin

from . import models


@admin.register(models.StyleGuide)
class StyleGuideAdmin(SimpleHistoryAdmin):
    list_display = ('__str__', 'language', 'last_modified')
    readonly_fields = ('created', 'last_modified')
    search_fields = ('content',)


@admin.register(models.Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'style_guide', 'user', 'created')
    list_filter = ('tags', 'style_guide__language')
    readonly_fields = ('created', 'last_modified')
    search_fields = ('title', 'content')
    filter_horizontal = ('tags',)


@admin.register(models.Tag)
class TagsAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(models.IssueComment)
class IssueCommentAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'user', 'last_modified', 'to_delete')
    search_fields = ('content', '^user__username')
    readonly_fields = ('last_modified', 'created')
