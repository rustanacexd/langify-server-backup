import random
import urllib
from collections import OrderedDict
from datetime import date
from string import ascii_letters, digits

from allauth.account.models import EmailAddress
from django_countries.fields import CountryField
from imagekit.models import ImageSpecField, ProcessedImageField
from randomcolor import RandomColor
from simple_history import register

from base.constants import (
    AVATAR,
    LANGUAGES,
    LANGUAGES_DICT,
    PERMISSIONS,
    UNTRUSTED_HTML_WARNING,
)
from base.history import HistoricalRecords
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import PermissionDenied
from django.db import models
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.translation import (
    gettext,
    gettext_lazy as _,
    gettext_noop,
    pgettext_lazy,
)
from panta.models import TranslatedSegment, TranslatedWork, Trustee

from .thumbnails import USER_AVATAR
from .validators import (
    UnicodeUsernameValidator,
    contains_captialized_word,
    html_free,
    in_last_5_to_110_years,
)

PRIVILEGES = (
    ('student', _('student')),
    ('contrib', _('contributor')),
    ('flagger', _('flagger')),
    ('initiat', _('initiator')),
    ('agreer', _('agreer')),
    ('transla', _('translator')),
    ('voter', _('voter')),
    ('reviewe', _('reviewer')),
    ('mentor', _('mentor')),
    ('moderat', _('moderator')),
    ('guardia', _('guardian')),
    ('amender', _('amender')),
    ('trustee', _('trustee')),
)


def user_avatar_path(instance, filename):
    now = timezone.now()
    # Add the month if a directory has several thousand files.
    # Git limits the number of hash revisions per directory to 6700.
    # https://webmasters.stackexchange.com/a/99644
    return 'users/{}/avatar_{}.jpg'.format(now.year, get_random_string(7))


# TODO Maybe remove
if settings.AUTH_USER_MODEL == 'path.User':
    user_model = AbstractUser
else:

    class AbstractUserProfil(models.Model):
        user = models.OneToOneField(
            settings.AUTH_USER_MODEL, _('user'), unique=True
        )

        @property
        def username(self):
            return self.user.username

        class Meta:
            abstract = True

    user_model = AbstractUserProfil


class Privilege(models.Model):
    """
    Privilege per trustee and language.
    """

    name = models.CharField(max_length=7, choices=PRIVILEGES)
    language = models.CharField(max_length=2)
    trustee = models.ForeignKey(Trustee, on_delete=models.PROTECT)


class OIDCUser(models.Model):
    """ Represents a user managed by an OpenID Connect provider (OP). """

    # An OpenID Connect user is associated with a record in the main user table.
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='oidc_user',
    )

    # The 'sub' value (aka Subject Identifier) is a locally unique and never reassigned identifier
    # within the issuer for the end-user. It is intended to be consumed by relying parties and does
    # not change over time. It corresponds to the only way to uniquely identify users between OIDC
    # provider and relying parties.
    sub = models.CharField(
        max_length=255, unique=True, verbose_name=_('Subject identifier')
    )

    # The content of the userinfo response will be stored in the following field.
    userinfo = JSONField(verbose_name=_('Subject extra data'))

    class Meta:
        verbose_name = _('OpenID Connect user')
        verbose_name_plural = _('OpenID Connect users')

    def __str__(self):
        return str(self.user)


class User(user_model):
    """
    User with profil, reputation and privileges.
    """

    deleted_username = gettext_noop('(deleted user)')

    # Fields inherited from super:
    # - password
    # - groups
    # - user_permissions
    # - is_staff
    # - is_active
    # - is_superuser
    # - last_login
    # - date_joined

    public_id = models.CharField(_('public ID'), max_length=8, unique=True)
    username = models.CharField(
        _('username'),
        max_length=30,
        unique=True,
        help_text=_(
            'Required. 30 characters or fewer. '
            'Letters, digits and ./+/-/_ only.'
        ),
        validators=(UnicodeUsernameValidator(),),
        error_messages={
            'unique': _('A user with that username already exists.')
        },
    )
    first_name = models.CharField(
        _('first name'),
        max_length=30,
        blank=True,
        validators=(html_free, contains_captialized_word),
    )
    last_name = models.CharField(
        _('last name'),
        max_length=150,
        blank=True,
        validators=(html_free, contains_captialized_word),
    )
    pseudonym = models.CharField(
        _('pseudonym'),
        max_length=100,
        blank=True,
        validators=(html_free, contains_captialized_word),
        help_text=_('Use this name instead of the real name.'),
    )
    name_display = models.CharField(
        _('name display'),
        # We don't include the first name here because we want that users are
        # uniquely identifiable in the community as far as possible
        choices=(('full', _('full name')), ('user', _('username'))),
        default='full',
        max_length=5,
        help_text=_('Name that is visible on the website for others.'),
    )
    email = models.EmailField(
        _('e-mail address'),
        unique=True,
        error_messages={'unique': _('This address is used already.')},
    )
    avatar = ProcessedImageField(
        verbose_name=_('image'),
        blank=True,
        null=True,
        help_text=_('Profile image.'),
        upload_to=user_avatar_path,
        processors=USER_AVATAR['processors'],
        format='JPEG',
        options=USER_AVATAR['options'],
    )
    avatar_crop = JSONField(
        verbose_name=_('image crop'), default=dict, blank=True
    )
    address = models.CharField(
        _('address'),
        max_length=50,
        blank=True,
        validators=(html_free, contains_captialized_word),
    )
    address_2 = models.CharField(
        _('address 2'), max_length=50, blank=True, validators=(html_free,)
    )
    zip_code = models.CharField(_('zip code'), max_length=10, blank=True)
    city = models.CharField(
        pgettext_lazy('in an address form', 'city'),
        max_length=50,
        blank=True,
        validators=(html_free, contains_captialized_word),
    )
    state = models.CharField(
        _('state'),
        max_length=50,
        blank=True,
        validators=(html_free, contains_captialized_word),
    )
    country = CountryField(
        _('country'), blank=True, help_text=_('Enter the name of your country.')
    )
    phone = models.CharField(
        _('phone number'), max_length=40, blank=True, validators=(html_free,)
    )
    language = models.CharField(
        _('language'), choices=LANGUAGES, max_length=5, blank=True
    )
    # sex = models.CharField(
    #    _('sex'),
    #    choices=(('f', _('female')), ('m', _('male'))),
    #    max_length=1,
    #    blank=True,
    # )
    born = models.DateField(
        _('date of birth'),
        # TODO add localization
        help_text=_('Format: YYYY-MM-DD, e.g. 1956-01-29.'),
        blank=True,
        null=True,
        validators=(in_last_5_to_110_years,),
    )
    description = models.TextField(
        _('description'),
        max_length=5000,
        blank=True,
        help_text=UNTRUSTED_HTML_WARNING,
    )
    experience = models.TextField(
        _('experience'),
        max_length=5000,
        blank=True,
        help_text=UNTRUSTED_HTML_WARNING,
    )
    education = models.TextField(
        _('education'),
        max_length=5000,
        blank=True,
        help_text=UNTRUSTED_HTML_WARNING,
    )
    privileges = models.ManyToManyField(
        Privilege,
        verbose_name=_('privileges'),
        related_name='users',
        blank=True,
    )
    flags = models.ManyToManyField(
        'self', through='FlagUser', symmetrical=False, related_name='flagged_by'
    )
    is_verified = models.BooleanField(_('is verified'), default=False)
    subscribed_edits = models.BooleanField(default=True)

    show_full_name = models.BooleanField(_('show full name'), default=False)
    show_country = models.BooleanField(_('show country'), default=False)
    show_age = models.BooleanField(_('show age'), default=False)
    show_description = models.BooleanField(_('show description'), default=False)
    show_experience = models.BooleanField(_('show experience'), default=False)
    show_education = models.BooleanField(_('show education'), default=False)

    history = HistoricalRecords(excluded_fields=['public_id'])

    thumbnail_sizes = (60, 120, 300)

    avatar_60 = ImageSpecField(
        source='avatar', id='path:thumbnails:user_thumbnail_60'
    )
    avatar_120 = ImageSpecField(
        source='avatar', id='path:thumbnails:user_thumbnail_120'
    )
    avatar_300 = ImageSpecField(
        source='avatar', id='path:thumbnails:user_thumbnail_300'
    )

    work = None  # Used to get reputation based permissions
    _edits = None

    @property
    def name(self):
        # TODO Allow user to select what to show: user name, first name, ...
        if self.is_active:
            return self.username
        else:
            return gettext(self.deleted_username)

    @property
    def age(self):
        # explicitly return None when born is not set
        if not self.born:
            return None

        b = self.born
        t = date.today()
        # https://stackoverflow.com/a/9754466
        return t.year - b.year - ((t.month, t.day) < (b.month, b.day))

    @property
    def roles(self):
        """
        Returns a list of OrderedDicts with language, role and edits.
        """
        # Determine roles
        roles_dict = OrderedDict()
        for r in self.reputations.all().order_by('language'):
            if r.score >= PERMISSIONS['trustee']:
                role = 'trustee'
            elif r.score >= PERMISSIONS['review_translation']:
                role = 'reviewer'
            elif r.score >= PERMISSIONS['add_translation']:
                role = 'translator'
            else:
                continue
            roles_dict[r.language] = role

        # Edits per language based on segments, not on the history
        edits = TranslatedSegment.objects.filter(
            pk__in=self.historicaltranslatedsegments.values('id')
        ).aggregate(
            **{
                l: Count('pk', filter=Q(work__language=l), distinct=True)
                for l in roles_dict
            }
        )

        # Build list with OrderedDicts
        roles_list = []
        for l, r in roles_dict.items():
            # Filter out languages without edits
            if edits[l]:
                roles_list.append(
                    OrderedDict(
                        (
                            ('language', LANGUAGES_DICT[l]),
                            ('role', r),
                            ('edits', edits[l]),
                        )
                    )
                )

        return roles_list

    @property
    def user_role_default_language(self):
        """
        Returns user role in their default language.
        """
        if not self.language:
            return
        reputation_score = self.get_reputation(self.language)
        return self.get_role_from_reputation(reputation_score)

    @property
    def permissions(self):
        """
        Returns all reputation based permissions of the user.
        """
        permissions = OrderedDict()
        no_score_permissions = OrderedDict(
            (name, minimum <= 1) for name, minimum in PERMISSIONS.items()
        )
        reputations = {r.language: r.score for r in self.reputations.all()}
        for language_code, language in LANGUAGES:
            score = reputations.get(language_code)
            if score is None:
                permissions.update({language_code: no_score_permissions})
            else:
                language_permissions = OrderedDict()
                for name, minimum in PERMISSIONS.items():
                    language_permissions.update({name: score >= minimum})
                permissions.update({language_code: language_permissions})
        return permissions

    @property
    def edits(self):
        if self._edits is None:
            self._edits = self.historicaltranslatedsegments.count()
        return self._edits

    @edits.setter
    def edits(self, value):
        self._edits = value

    @classmethod
    def from_db(cls, db, field_names, values):
        """
        Records the inital field value of last_login.
        """
        # https://docs.djangoproject.com/en/dev/ref/models/instances/
        # #customizing-model-loading
        instance = super().from_db(db, field_names, values)
        instance._loaded_last_login = values[field_names.index('last_login')]
        return instance

    def __init__(self, *args, **kwargs):
        # I can't set the ImageSpecFields dynamically with setattr.
        # Maybe I can ask somewhere how to do that.
        # Or maybe move the thumbnails into the DRF serializer
        # but then you have to care what to do with the thumbnails yourself.

        super().__init__(*args, **kwargs)

        # Note: This solution should not be used if multiple people are
        # likely to update the same model instance at the same time.
        # (In this case wrap save into a transaction.atomic and look up
        # the original value there.)
        # See https://stackoverflow.com/a/1361547
        self._old_avatar = self.avatar
        self._old_avatar_crop = self.avatar_crop

    def clean(self):
        super().clean()
        same_crop = self._old_avatar_crop == self.avatar_crop
        if self._old_avatar != self.avatar and same_crop:
            self.avatar_crop = {}

    def get_avatar(self):
        """
        Returns a thumbnail URL or SVG avatar, grey if the user is inactive.
        """
        if not self.is_active:
            # A grey avatar
            color = '#e6e6e6'
        elif self.avatar_60:
            return self.avatar_60.url
        else:
            color = RandomColor(self.username).generate()[0]
        return 'data:image/svg+xml;utf8,{}'.format(
            # TODO re-add \' to safe when we don't use local storage anymore
            urllib.parse.quote(AVATAR.format(color=color), safe=' /:=%')
        )

    def get_reputation(self, language: str) -> int:
        """
        Returns the reputation score for a given language from cache or DB.
        """
        score = getattr(self, f'reputation_{language}', None)
        if score is None:
            # Give the user a reputation of 5 if it doesn't exist for given
            # language yet.
            # A temporary workaround until we have some algorithm to let users
            # start with a language.
            reputation, created = self.reputations.get_or_create(
                language=language, defaults={'score': 5, 'user': self}
            )
            score = reputation.score
            # try:
            #     score = self.reputations.get(language=language).score
            # except ObjectDoesNotExist:
            #     score = 1
            setattr(self, f'reputation_{language}', score)
        return score

    def get_role_from_reputation(self, reputation_score):
        """
        Get role from reputation score
        """
        if reputation_score >= PERMISSIONS['trustee']:
            role = 'trustee'
        elif reputation_score >= PERMISSIONS['review_translation']:
            role = 'reviewer'
        elif reputation_score >= PERMISSIONS['add_translation']:
            role = 'translator'
        else:
            return

        return role

    def has_required_reputation(self, action, work):
        score = self.get_reputation(self.get_language_of(work))
        return score >= PERMISSIONS[action]

    def check_perms(self, work, *permissions):
        """
        Checks that the user has the permissions for the work.
        """
        for perm in permissions:
            if not self.has_required_reputation(perm, work):
                # todo: Provide an error code
                msg = _(
                    'A reputation of {score} is required for the privilege '
                    '"{name}".'
                )
                raise PermissionDenied(
                    msg.format(score=PERMISSIONS[perm], name=perm)
                )

    def check_role(self, role, work):
        """
        Raises PermissionDenied if the user doesn't have given role.
        """
        if role == 'translator':
            # Should be handled in the permissions
            return
        elif role == 'reviewer':
            self.check_perms(work, 'review_translation')
        elif role == 'trustee':
            # if not self.has_perm('panta.vote_as_trustee'.format(
            #    self.get_language_of(work))):
            #    raise PermissionDenied
            self.check_perms(work, 'trustee')
        else:
            raise ValueError('The role "{}" is invalid.'.format(role))

    def set_public_id(self):
        self.public_id = ''.join(
            [random.choice(ascii_letters + digits) for ch in range(8)]
        )

    def get_language_of(self, work):
        if isinstance(work, TranslatedWork):
            self.work = work
        elif self.work is None or self.work.pk != int(work):
            try:
                self.work = TranslatedWork.objects.only('language').get(pk=work)
            except TranslatedWork.DoesNotExist:
                # Happens when rendering the OpenAPI schema
                return '--'
        return self.work.language

    def flag(self, user, reason=None):
        flagged, created = FlagUser.objects.update_or_create(
            flagger=self, flagged=user, defaults={'reason': reason}
        )
        return flagged

    def unflag(self, user):
        FlagUser.objects.filter(flagger=self, flagged=user).delete()
        return

    def save(self, *args, **kwargs):
        """
        Adds public ID. Doesn't create a historical record when user logs in.
        """
        if self._state.adding:
            self.set_public_id()
        elif self.last_login != self._loaded_last_login:
            # Make it possible to still use save_without_historical_record
            # (which also deletes the attribute).
            # Maybe the behavior of simple history should be changed to not
            # deleting the attribute but setting it to false. (Behavior in
            # v2.3.)
            # save_without_historical_record() can't be used because it calls
            # save() again.
            self.delete_skip_history = not hasattr(
                self, 'skip_history_when_saving'
            )
            self.skip_history_when_saving = True
        super().save(*args, **kwargs)
        if getattr(self, 'delete_skip_history', False):
            del self.skip_history_when_saving
            self.delete_skip_history = False
        self._loaded_last_login = self.last_login


class Reputation(models.Model):
    """
    Reputation per language.
    """

    score = models.PositiveIntegerField(_('score'), default=1)
    language = models.CharField(_('language'), choices=LANGUAGES, max_length=5)
    user = models.ForeignKey(
        User,
        verbose_name=_('user'),
        related_name='reputations',
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = _('reputation')
        verbose_name_plural = _('reputations')
        unique_together = ('user', 'language')
        index_together = unique_together


class FlagUser(models.Model):
    flagger = models.ForeignKey(
        User, related_name='flagger_user', on_delete=models.CASCADE
    )
    flagged = models.ForeignKey(
        User, related_name='flagged_user', on_delete=models.CASCADE
    )
    reason = models.CharField(null=True, blank=True, max_length=200)

    def __str__(self):
        return f'Flagger: {self.flagger} - Flagged: {self.flagged}'


register(
    EmailAddress,
    app=__package__,
    records_class=HistoricalRecords,
    excluded_fields=('primary',),
)
