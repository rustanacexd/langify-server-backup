from allauth.account.admin import EmailAddressAdmin
from allauth.account.models import EmailAddress
from simple_history.admin import SimpleHistoryAdmin

from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import UserChangeForm as DjangoUserChangeForm
from django.db.models import F
from django.utils.translation import gettext_lazy as _

from . import models

USER_FIELDS = (
    'username',
    'first_name',
    'last_name',
    'pseudonym',
    'name_display',
    'is_active',
    'is_staff',
    'is_superuser',
    'email',
    'avatar',
    'avatar_crop',
    'address',
    'address_2',
    'zip_code',
    'city',
    'state',
    'country',
    'phone',
    'language',
    'born',
    'privileges',
    'subscribed_edits',
    'user_permissions',
    'groups',
)


class UserCreationForm(forms.ModelForm):
    """
    A form for creating new users with password confirmation.
    """

    # TODO Maybe use Django's form here? (Why didn't I do that?)
    password_1 = forms.CharField(
        label=_('Password'), widget=forms.PasswordInput
    )
    password_2 = forms.CharField(
        label=_('Password confirmation'), widget=forms.PasswordInput
    )

    class Meta:
        model = models.User
        fields = USER_FIELDS

    def clean_password_2(self):
        # Check that the two password entries match
        password_1 = self.cleaned_data.get('password_1')
        password_2 = self.cleaned_data.get('password_2')
        if password_1 and password_2 and password_1 != password_2:
            raise forms.ValidationError(_('Passwords don\'t match'))
        return password_2

    def save(self, commit=True):
        # Save the provided password in hashed format
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password_1'])
        if commit:
            user.save()
        return user


class UserChangeForm(DjangoUserChangeForm):
    """
    A form for updating users. Includes all the fields on
    the user, but replaces the password field with admin's
    password hash display field.
    """

    class Meta(DjangoUserChangeForm.Meta):
        model = models.User
        fields = USER_FIELDS


class ReputationInline(admin.TabularInline):
    model = models.Reputation
    extra = 0


class UserRoleDefaultLanguageFilter(admin.SimpleListFilter):
    title = 'User Role Default Language'
    parameter_name = 'user_role_default_language'

    def lookups(self, request, model_admin):
        return (
            ('translator', 'Translator'),
            ('reviewer', 'Reviewer'),
            ('trustee', 'Trustee'),
        )

    def queryset(self, request, queryset):
        def _get_ids(role):
            return [
                user.id
                for user in models.User.objects.filter(is_active=True).exclude(
                    language__isnull=True
                )
                if user.user_role_default_language == role
            ]

        value = self.value()
        if value == 'translator':
            return queryset.filter(id__in=_get_ids('translator'))
        elif value == 'reviewer':
            return queryset.filter(id__in=_get_ids('reviewer'))
        elif value == 'trustee':
            return queryset.filter(id__in=_get_ids('trustee'))
        return queryset


@admin.register(models.User)
class UserAdmin(DjangoUserAdmin, SimpleHistoryAdmin):
    # The forms to add and change user instances
    form = UserChangeForm
    add_form = UserCreationForm
    inlines = (ReputationInline,)

    # The fields to be used in displaying the User model.
    # These override the definitions on the base UserAdmin
    # that reference specific fields on auth.User.
    list_display = (
        'username',
        'email',
        'first_name',
        'last_name',
        'is_active',
        'date_joined',
        'language',
        'reputation_score',
    )
    list_filter = (
        'is_active',
        'is_superuser',
        'language',
        UserRoleDefaultLanguageFilter,
    )
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (
            _('Personal info'),
            {
                'fields': (
                    'first_name',
                    'last_name',
                    'pseudonym',
                    'email',
                    'avatar',
                    'avatar_crop',
                    'address',
                    'address_2',
                    'zip_code',
                    'city',
                    'state',
                    'country',
                    'phone',
                    'language',
                    'born',
                    'description',
                    'experience',
                    'education',
                    'is_verified',
                    'subscribed_edits',
                    'show_full_name',
                    'show_country',
                    'show_age',
                    'show_description',
                    'show_experience',
                    'show_education',
                    'public_id',
                )
            },
        ),
        (
            _('Permissions'),
            {
                'fields': (
                    'is_active',
                    'is_staff',
                    'is_superuser',
                    'privileges',
                    'groups',
                    'user_permissions',
                )
            },
        ),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    # add_fieldsets is not a standard ModelAdmin attribute. UserAdmin
    # overrides get_fieldsets to use this attribute when creating a user.
    add_fieldsets = (
        (None, {'fields': ('username', 'password_1', 'password_2', 'email')}),
    )
    readonly_fields = ('public_id', 'last_login', 'date_joined')
    search_fields = (
        'username',
        'first_name',
        'last_name',
        'email',
        'public_id',
    )
    filter_horizontal = ('privileges', 'groups', 'user_permissions')

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if not request.path == '/admin/path/user/':
            return queryset

        queryset = queryset.prefetch_related('reputations')
        queryset = queryset.filter(
            reputations__language=F('language')
        ).annotate(_rep_score=F('reputations__score'))

        return queryset

    def reputation_score(self, obj):
        return obj._rep_score

    reputation_score.admin_order_field = '_rep_score'


admin.site.unregister(EmailAddress)


@admin.register(EmailAddress)
class SimpleHistoryEmailAddressAdmin(EmailAddressAdmin, SimpleHistoryAdmin):
    pass


admin.site.register(models.FlagUser)
