from bs4 import BeautifulSoup

from base.constants import ROLES, UNTRUSTED_HTML_WARNING, get_languages
from base.history import HistoricalRecords
from base.models import TimestampsModel
from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import (
    Case,
    Count,
    ExpressionWrapper,
    F,
    Func,
    OuterRef,
    Prefetch,
    Q,
    Subquery,
    Sum,
    Value,
    When,
)
from django.utils import timezone
from django.utils.text import Truncator
from django.utils.translation import gettext_lazy as _, pgettext_lazy
from panta import queries, validators
from panta.constants import (
    BLANK,
    CHANGE_REASONS,
    IMPORTANT_HEADINGS,
    IN_REVIEW,
    IN_TRANSLATION,
    LANGUAGE_RATIOS,
    RELEASED,
    REQUIRED_APPROVALS,
    REVIEW_DONE,
    TRANSLATION_DONE,
    TRUSTEE_DONE,
)
from panta.utils import get_system_user

from .api.external import DeepLAPI

# from guardian.models import UserObjectPermissionBase,GroupObjectPermissionBase


PROGRESS_STATES = (
    (BLANK, _('blank')),
    (IN_TRANSLATION, _('in translation')),
    (TRANSLATION_DONE, _('translation done')),
    (IN_REVIEW, _('in review')),
    (REVIEW_DONE, _('review done')),
    (TRUSTEE_DONE, _('trustee done')),
    # ('released', _('released')),
)


class VersionModel(models.Model):
    """
    Abstract model activating versioning.
    """

    history = HistoricalRecords(inherit=True)

    class Meta:
        abstract = True


class Trustee(VersionModel):
    """
    Trustee how has control over his works.
    """

    name = models.CharField(_('name'), max_length=100, unique=True)
    description = models.TextField(_('description'))
    code = models.CharField(
        _('code'), max_length=5, unique=True, help_text=_('Cannot be changed!')
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name=_('members'),
        related_name='trustee_memberships',
    )

    def __str__(self):
        return self.name


class Tag(models.Model):
    """
    Tags for tagging.
    """

    name = models.CharField(_('name'), max_length=40, unique=True)
    slug = models.SlugField(_('slug'), max_length=40, unique=True)

    def __str__(self):
        return self.name


class AbstractWorkModel(TimestampsModel, VersionModel):
    """
    Abstract model for original and translated works.
    """

    BOOK = 'book'
    PERIODICAL = 'periodical'
    MANUSCRIPT = 'manuscript'

    types = (
        (BOOK, _('Book')),
        (PERIODICAL, _('Periodical')),
        (MANUSCRIPT, _('Manuscript')),
    )

    title = models.CharField(_('title'), max_length=150, db_index=True)
    subtitle = models.CharField(_('subtitle'), max_length=100, blank=True)
    abbreviation = models.SlugField(
        _('abbreviation'),
        max_length=30,
        help_text=_('Public identifier of this work.'),
    )
    type = models.CharField(_('type'), choices=types, max_length=10)
    description = models.TextField(_('description'), blank=True)
    # TODO use a language field (for flags)?
    language = models.CharField(
        _('language'),
        max_length=7,
        choices=get_languages(lazy=True),
        help_text=_('Note: Most languages will be buggy.'),
    )
    trustee = models.ForeignKey(
        Trustee, verbose_name=_('trustee'), on_delete=models.PROTECT
    )
    private = models.BooleanField(_('private'))

    def __str__(self):
        return self.title

    class Meta(TimestampsModel.Meta):
        abstract = True


class OriginalWork(AbstractWorkModel):
    """
    Original work of a book, an article, a letter...
    """

    key = models.CharField(_('key'), max_length=30, blank=True)
    author = models.ForeignKey(
        'Author', verbose_name=_('author'), on_delete=models.PROTECT
    )
    published = models.PositiveSmallIntegerField(
        _('published in'), null=True, blank=True
    )
    edition = models.CharField(_('edition'), max_length=10, blank=True)
    licence = models.ForeignKey(
        'Licence',
        verbose_name=_('licence'),
        on_delete=models.PROTECT,
        help_text=_('Select the licence you want to publish this work under.'),
    )
    isbn = models.CharField(_('ISBN'), max_length=17, blank=True)
    publisher = models.CharField(_('publisher'), max_length=70, blank=True)
    tags = models.ManyToManyField(
        Tag, verbose_name=_('tags'), related_name='originalworks', blank=True
    )

    ai_user = None
    _table_of_contents = None

    @property
    def table_of_contents(self):
        if self._table_of_contents is not None:
            return self._table_of_contents

        self._table_of_contents = (
            self.segments.filter(tag__in=IMPORTANT_HEADINGS)
            .order_by('position')
            .values('id', 'position', 'tag', 'classes', 'content')
        )
        return self._table_of_contents

    def get_deepl_translation(self, to, positions=None, **params):
        """
        Creates DeepL translations. Adds them as hist. records if applicalbe.
        """
        segments = self.segments.distinct().exclude(
            basetranslations__translation__language=to
        )
        if positions:
            segments = segments.filter(position__in=positions)
        if not segments:
            return (0, 0)
        base_translator, created = BaseTranslator.objects.get_or_create(
            name='DeepL.com', type='ai'
        )
        base_translation, created = BaseTranslation.objects.get_or_create(
            translator=base_translator, language=to
        )
        count = 0
        api = DeepLAPI()
        translations = api.translate_iterable(
            source_lang=self.language.upper(),
            target_lang=to.upper(),
            texts=(s.content for s in segments),
            **params,
        )
        for segment, translation in zip(segments, translations):
            self.save_ai_translation_segment(
                segment=segment,
                to=to,
                content=translation,
                original_id=segment.pk,
                translation=base_translation,
            )
            count += 1
        try:
            twork = TranslatedWork.objects.get(original=self, language=to)
        except TranslatedWork.DoesNotExist:
            pass
        else:
            twork.update_pretranslated()
        return (count, count / len(segments))

    @transaction.atomic
    def save_ai_translation_segment(self, segment, to, **kwargs):
        # Don't create in bulk to have the data in case something fails
        ai_segment = BaseTranslationSegment.objects.create(**kwargs)
        # Create a historical record if the work is translatable
        try:
            human_translation = segment.translations.get(work__language=to)
        except segment.translations.model.DoesNotExist:
            pass
        else:
            if not human_translation.history.exists():
                human_translation.add_to_history(
                    content=ai_segment.content,
                    history_type='+',
                    history_date=ai_segment.created,
                    history_change_reason=CHANGE_REASONS['DeepL'],
                    history_user=self.get_ai_user(),
                )

    def get_ai_user(self):
        if not self.ai_user:
            self.ai_user = get_system_user('AI')
        return self.ai_user

    class Meta(AbstractWorkModel.Meta):
        verbose_name = pgettext_lazy('literary work', 'original work')
        verbose_name_plural = pgettext_lazy('literary works', 'original works')


class TranslatedWork(AbstractWorkModel):
    """
    Translation of a book, an article, a letter...
    """

    original = models.ForeignKey(
        OriginalWork,
        verbose_name=_('original'),
        related_name='translations',
        on_delete=models.PROTECT,
        help_text=_('Select the original work.'),
    )
    protected = models.BooleanField(
        _('protected'),
        help_text=_('Gets checked when work is ready for amending.'),
    )
    tags = models.ManyToManyField(
        Tag, verbose_name=_('tags'), related_name='translatedworks', blank=True
    )

    objects = queries.TranslatedWorkQuerySet.as_manager()

    _segments_count = None
    _table_of_contents = None

    @property
    def combined_tags(self):
        return set(self.tags.all()).union(self.original.tags.all())

    @property
    def segments_count(self):
        if self._segments_count is None:
            self._segments_count = self.segments.count()
        return self._segments_count

    @property
    def table_of_contents(self):
        """
        Table of contents in translated (if available) or original language.
        """
        if self._table_of_contents is None:
            self._table_of_contents = self.important_headings.all()
        return self._table_of_contents

    @property
    def required_approvals(self):
        return REQUIRED_APPROVALS.get(self.language)

    def update_pretranslated(self, chapters=True, save=True) -> dict:
        """
        Updates statistics.pretranslated of the work.
        """
        if chapters:
            count = 0
            for chapter in self.important_headings.all():
                count += chapter.update_pretranslated()
        else:
            count = getattr(self, 'pretranslated', None)
            if count is None:
                count = (
                    self.important_headings.aggregate(
                        count=Sum('pretranslated')
                    )['count']
                    or 0
                )
        if self._segments_count is None:
            segments = self.statistics.segments
        else:
            segments = self._segments_count
        if segments:
            percent = count * 100.0 / segments
        else:
            percent = 0
        stats = {'pretranslated_count': count, 'pretranslated_percent': percent}
        if save and self.statistics.pretranslated_count != count:
            for k, v in stats.items():
                setattr(self.statistics, k, v)
            self.statistics.save()
        return stats

    class Meta(AbstractWorkModel.Meta):
        verbose_name = pgettext_lazy('literary work', 'translated work')
        verbose_name_plural = pgettext_lazy(
            'literary works', 'translated works'
        )


# Create direct object permissions
# https://stackoverflow.com/questions/15247075/
# how-can-i-dynamically-create-derived-classes-from-a-base-class
# def set_content_object(self, cls, *args, **kwargs):
#    setattr(self, 'content_object',
# for n in ('OriginalWork', 'TranslatedWork'):
#    name = '{}UserObjectPermission'.format(n)
#    cls = type(name, (UserObjectPermissionBase,) set field
#    setattr(__file__, name, cls)

# TODO
# class OriginalWorkUserObjectPermission(UserObjectPermissionBase):
#    content_object = models.ForeignKey(
#        OriginalWork, on_delete=models.CASCADE)
#
# class OriginalWorkGroupObjectPermission(GroupObjectPermissionBase):
#    content_object = models.ForeignKey(
#        OriginalWork, on_delete=models.CASCADE)
#
# class TranslatedWorkUserObjectPermission(UserObjectPermissionBase):
#    content_object = models.ForeignKey(
#        TranslatedWork, on_delete=models.CASCADE)
#
# class TranslatedWorkGroupObjectPermission(GroupObjectPermissionBase):
#    content_object = models.ForeignKey(
#        TranslatedWork, on_delete=models.CASCADE)


class Author(TimestampsModel, VersionModel):
    """
    Information about an author of a work.
    """

    prefix = models.CharField(
        _('prefix'),
        max_length=20,
        blank=True,
        help_text=_('Titles, in some langauges as suffix.'),
    )
    first_name = models.CharField(_('first name'), max_length=50)
    last_name = models.CharField(_('last name'), max_length=100)
    suffix = models.CharField(_('suffix'), max_length=20, blank=True)
    born = models.DateField(_('date of birth'), null=True, blank=True)
    bio = models.TextField(_('biograpyh'))

    def __str__(self):
        return '{}, {}'.format(self.last_name, self.first_name)

    @property
    def name(self):
        """
        Complete name (with pre- and suffix).
        """
        parts = (self.prefix, self.first_name, self.last_name, self.suffix)
        return ' '.join((p for p in parts if p))

    class Meta:
        verbose_name = _('author')
        verbose_name_plural = _('authors')
        unique_together = ('first_name', 'last_name')


class Licence(TimestampsModel, VersionModel):
    """
    Licence of a work.
    """

    # TODO multilingual?
    title = models.CharField(_('title'), max_length=100, unique=True)
    # TODO Markdown
    description = models.TextField(_('description'))

    def __str__(self):
        return self.title

    class Meta(TimestampsModel.Meta):
        verbose_name = _('licence')
        verbose_name_plural = _('licences')


# class Release(TimestampsModel, VersionModel):
#    """
#    Release of a translated work.
#    """
#    #TODO or edition?
#    #TODO do we need last_modified?
#    work = models.ForeignKey(
#        TranslatedWork,
#        verbose_name=_('work'),
#        related_name='releases',
#        on_delete=models.PROTECT,
#    )
#    number = models.SmallIntegerField(_('number'), db_index=True)
#    segments = models.ManyToManyField(
#        'TranslatedSegment',
#        verbose_name=_('segments'),
#    )
#    cachet = models.ManyToManyField(
#        'Cachet', verbose_name=_('labels'), blank=True)
#
#    @property
#    def state(self):
#        """
#        Show the release state human friendly.
#        """
#        if self.number == -10:
#            return _('in translation')
#        elif self.number == -5:
#            return _('in review')
#        else:
#            return _('release %(number)s') % self.number
#
#    def __str__(self):
#        # TODO reduce queries?
#        return '%s-%s %s' % (self.work.language, self.work.abbr, self.state)
#
#    class Meta(TimestampsModel.Meta):
#        verbose_name = _('release')
#        verbose_name_plural = _('releases')
#        unique_together = ('work', 'number')
#        get_latest_by = 'number'


class AbstractSegmentModel(TimestampsModel):
    """
    Abstract segment for original and translated segments.
    """

    position = models.PositiveIntegerField(
        _('position'),
        db_index=True,
        help_text=_('Segments get ordered by their positions.'),
    )
    page = models.CharField(
        _('page'),
        db_index=True,
        max_length=7,  # XXXVIII, Roman numerals possible up to LXXXVII = 87
        validators=[validators.get_bullet_format],
        null=True,
        blank=True,
        help_text=_(
            '(First) page of this segment in the work. '
            'You may use Arabic numerals (1,2,3,...), '
            'Roman numerals (in upper case, e.g. I,II,III,...) or '
            'the alphabet in lower case (a - z).'
        ),
    )
    tag = models.CharField(
        _('tag'), max_length=10, validators=[validators.valid_tag]
    )
    classes = ArrayField(
        models.CharField(max_length=30),
        verbose_name=_('classes'),
        default=list,
        blank=True,
        validators=[validators.valid_classes],
    )
    content = models.TextField(
        _('content'), blank=True, validators=[validators.valid_segment]
    )
    reference = models.CharField(_('reference'), max_length=50)

    def clean(self):
        # if self.tag != 'hr' and not self.content:
        #    raise ValidationError(_('The segment requires content.'))
        pass

    def __str__(self):
        return self.reference

    # TODO How does db_index work on a JsonField?
    # Maybe include position and page also into the JosnField or remove them
    # completely.
    # TODO I could even put the whole content of a book in one
    # JSONField/RangeField if I can retrieve and write only a part of that
    # field. But I guess that's not possible. Or how many KBs does one book
    # have?
    # TODO Note that we might want to cache a segment in memory for the diff
    # saving all few seconds. Therefore we should limit the contnet of one
    # segment to a few KBs.

    class Meta(TimestampsModel.Meta):
        abstract = True
        ordering = ('position',)


class OriginalSegment(AbstractSegmentModel, VersionModel):
    """
    Segment (e.g. chapter) of an original work.
    """

    work = models.ForeignKey(
        OriginalWork,
        verbose_name=_('work'),
        related_name='segments',
        on_delete=models.PROTECT,
    )
    key = models.CharField(_('key'), max_length=30, blank=True)

    # def __str__(self):
    #    return '{} {}'.format(self.work.abbreviation, self.position)

    class Meta(AbstractSegmentModel.Meta):
        verbose_name = _('original segment')
        verbose_name_plural = _('original segments')
        unique_together = ('work', 'position')


class BaseHistoricalTranslatedSegment(models.Model):
    """
    Abstract model for the history of the translated segments.
    """

    relative_id = models.PositiveSmallIntegerField(_('relative ID'), default=1)

    @property
    def created(self):
        return self.history_date

    def save(self, *args, **kwargs):
        # Set relative_id when the object is created, only
        if not self.pk:
            model = apps.get_model('panta', 'HistoricalTranslatedSegment')
            try:
                # Note that this retreives the newest record, not that one
                # with the highest relative_id
                most_recent_record = (
                    model.objects.filter(id=self.id)
                    .only('relative_id')
                    .latest()
                )
            except self.DoesNotExist:
                pass
            else:
                self.relative_id = most_recent_record.relative_id + 1
        super().save(*args, **kwargs)

    class Meta:
        abstract = True
        unique_together = ('id', 'relative_id')


class TranslatedSegment(AbstractSegmentModel):
    """
    Segment (e.g. chapter) of a translated work.
    """

    work = models.ForeignKey(
        TranslatedWork,
        verbose_name=_('work'),
        related_name='segments',
        on_delete=models.PROTECT,
    )
    original = models.ForeignKey(
        OriginalSegment,
        verbose_name=_('original'),
        related_name='translations',
        on_delete=models.PROTECT,
    )
    # TODO move this to cache completely?
    locked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('locked by'),
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    progress = models.PositiveSmallIntegerField(
        _('progress'), default=BLANK, choices=PROGRESS_STATES
    )

    history = HistoricalRecords(
        bases=[BaseHistoricalTranslatedSegment],
        excluded_fields=[
            'position',
            'page',
            'tag',
            'classes',
            'reference',
            'original',
            'locked_by',
            'progress',
            'created',
            'last_modified',
        ],
        related_name='past',
    )

    chapter = models.ForeignKey(
        'ImportantHeading',
        verbose_name=_('chapter'),
        related_name='segments',
        on_delete=models.SET_NULL,
        null=True,
    )

    objects = queries.TranslatedSegmentQuerySet.as_manager()

    # This can't be set in save_without_historical_record because super()
    # doesn't have this method (which I'd like to call).
    keep_votes_when_skipping_history = True

    # Attribute to let the update endpoint know if it should include the
    # statistics in the response
    votes_moved = False

    progress_states = [s[0] for s in PROGRESS_STATES]

    _last_historical_record = None

    @property
    def last_historical_record(self):
        if not self._last_historical_record:
            obj = (
                self.history.annotate(
                    edits=Count('history_user__historicaltranslatedsegments')
                )
                .select_related('history_user')
                .latest()
            )
            if obj.history_user:
                obj.history_user.edits = obj.edits
            self._last_historical_record = obj
        return self._last_historical_record

    @last_historical_record.setter
    def last_historical_record(self, value):
        self._last_historical_record = value

    def __getattr__(self, name):
        if name in ('translators', 'reviewers', 'trustees'):
            votes = {
                'vote': getattr(self, '{}_vote'.format(name)) or 0,
                'user': getattr(self, 'user_{}_vote'.format(name[:-1])) or 0,
            }
            assert abs(votes['user']) <= 1, 'Somebody voted more than once!'
            return votes
        if hasattr(super(), '__getattr__'):
            return super().__getattr__(name)
        msg = "'{}' object has no attribute '{}'"
        raise AttributeError(msg.format(self.__class__.__name__, name))

    @classmethod
    def from_db(cls, db, field_names, values):
        """
        Records the initial value of field content.
        """
        # https://docs.djangoproject.com/en/dev/ref/models/instances/
        # #customizing-model-loading
        instance = super().from_db(db, field_names, values)
        if 'content' in field_names:
            instance._loaded_content = values[field_names.index('content')]
        return instance

    def get_fresh_obj_with_stats(self, user):
        segment = (
            self.__class__.objects.select_related('locked_by')
            .annotate(edits=Count('locked_by__historicaltranslatedsegments'))
            .for_response(self.work_id, user)
            .get(pk=self.pk)
        )
        if segment.locked_by:
            segment.locked_by.edits = segment.edits
        return segment

    def get_history_for_serializer(self, latest=False):
        vote_qs = Vote.objects.select_related('user').annotate(
            edits=Count('user__historicaltranslatedsegments')
        )
        queryset = (
            self.history.annotate(
                edits=Count('history_user__historicaltranslatedsegments')
            )
            .select_related('history_user')
            .prefetch_related(Prefetch('votes', queryset=vote_qs))
        )

        def assign_edits(obj):
            # https://stackoverflow.com/questions/54065925/
            # add-an-annotation-value-to-select-related
            if obj.history_user:
                obj.history_user.edits = obj.edits
            for v in obj.votes.all():
                v.user.edits = v.edits

        if latest:
            obj = queryset.latest()
            assign_edits(obj)
            return obj
        # Convert the queryset to not be tempted to alter it
        objects = list(queryset)
        for obj in objects:
            assign_edits(obj)
        return objects

    def has_minimum_vote(self, role, minimum):
        return (getattr(self, f'{role}s_vote') or 0) >= minimum

    def can_edit(self, role):
        if role == 'translator':
            permission = self.progress < IN_REVIEW and not (
                self.has_minimum_vote('reviewer', 1)
                or self.has_minimum_vote('trustee', 1)
            )
            return permission
        if role == 'reviewer':
            return not self.has_minimum_vote('trustee', 1)
        if role == 'trustee':
            return True

    def voting_done(self, role):
        required = self.work.required_approvals
        return self.has_minimum_vote(role, required[role])

    def can_vote(self, role):
        """
        Returns a boolean if given role can vote.
        """
        if self.progress == BLANK:
            return False
        if role == 'translator':
            return True
        if role == 'reviewer':
            return self.voting_done('translator')
        if role == 'trustee':
            return self.voting_done('reviewer')

    def determine_progress(self, content=True, votes=True, additional=None):
        """
        Returns the progress state of the segment.
        """
        if content and self.content == '':
            return BLANK

        if votes:
            if additional:
                attr = '{}s_vote'.format(additional.role)
                # Add the value of the additional vote
                value = getattr(self, attr) or 0
                setattr(self, attr, value + additional.value)
            if self.voting_done('trustee'):
                return TRUSTEE_DONE
            if self.voting_done('reviewer'):
                return REVIEW_DONE
            if self.has_minimum_vote('reviewer', 1):
                return IN_REVIEW

        if not content:
            return None
        # Remove HTML tags because we don't have a feature to set reference
        # links yet.
        original = BeautifulSoup(self.original.content, 'html.parser')
        translation = BeautifulSoup(self.content, 'html.parser')

        # The shorter the segment the more tolerance is necessary
        #      Length      | Ratio
        # Orig.   | Trans. | (min.)
        # --------|--------|--------
        # 1       | 1+     | 1
        # 2       | 1+     | 0.5
        # 3       | 1+     | 0.33
        # 4       | 1+     | 0.25
        # 5       | 1+     | 0.2
        # 6..9    | 3+     | 0.5 – 0.33
        # 10      | 5+     | 0.5
        # -> Let's try 0.5 of the required characters are required up to 50
        # characters
        #
        # Future plans: Use statistics of trustee approved segments, either the
        # statistics directly or a mathematical function based on the
        # statistical data.

        length_original = len(original.get_text())
        required = LANGUAGE_RATIOS[self.work.language]
        if length_original <= 50:
            required /= 2
        # todo: Exclude footnotes from calculation if they are in the
        # translation only
        if len(translation.get_text()) / length_original <= required:
            return IN_TRANSLATION
        return TRANSLATION_DONE

    @property
    def chapter_position(self):
        """
        The relative position of the current segment within the chapter.
        """
        if self.chapter_id:
            return self.position - self.chapter.first_position + 1

    @property
    def has_statistics(self):
        return hasattr(self, 'comments')

    def add_to_history(self, history_type='~', add_to=None, save=True, **kw):
        """
        Creates a historical segment. Doesn't save it if 'add_to' is not None.
        """
        obj = self.history.model(
            id=self.pk,
            content=kw.pop('content', self.content),
            work_id=self.work_id,
            chapter_id=self.chapter_id,
            history_type=history_type,
            history_date=kw.pop('history_date', self.last_modified),
            history_relation_id=self.pk,
            **kw,
        )
        if add_to is None:
            if save:
                obj.save()
        else:
            add_to.append(obj)
        return obj

    @transaction.atomic(savepoint=False)
    def save(self, *args, **kwargs):
        """
        Handles votes.

        Adds votes to the new historical record. Moves votes to the new
        historical record if content changed and the work was released.
        """
        # Race conditions
        #
        # Creating the historical record and updating the votes is subject to
        # race conditions:
        # 1) I think it is not guaranteed that the fields of the segment/record
        #    are still up-to-date when the record is created/saved
        # 2) The same might be true for (the number of) votes
        # 3) On the other hand, it might be possible that votes of a newer
        #    version are wrongly retrieved, deleted from the segment and
        #    assigned to the record
        #
        # select_for_update won't help here because it locks the rows of the
        # table only (and doesn't prevent insertions).
        #
        # To work against the race conditions: You can't vote as long as a
        # segment is locked by somebody. This should reduce them to a minimum
        # because it should take a few milliseconds until the users get the
        # information that a segment isn't locked anymore and they send a vote
        # or an edit back.

        # save() changes these values
        pk = self.pk
        # todo: Why does save() retrieve the content when it was deferred
        # before? Even if you call e.g. save(update_fields=['tag'])!
        # I couldn't find an answer quickly and we hardly have this use case.
        # Therefore, I left it as todo.
        # Update: This might be related to
        # https://github.com/treyhunner/django-simple-history/pull/470

        # hasattr(self, 'content') would load the field
        content_used = 'content' in self.__dict__
        self.votes_moved = False

        super().save(*args, **kwargs)

        # Add votes to new historical segment
        if (
            getattr(self, 'skip_history_when_saving', False)
            and self.keep_votes_when_skipping_history
        ):
            votes = self.votes.none()
        else:
            votes = self.votes.all().only('pk', 'segment')
            if votes:
                self.history.latest().votes.set(votes)

        # Remove votes
        if content_used:
            if hasattr(self, '_loaded_content'):
                if self.content != self._loaded_content:
                    if self.progress >= RELEASED:
                        votes.update(segment=None)
                        self.votes_moved = True
                    self._loaded_content = self.content
            elif pk is None:
                self._loaded_content = self.content
            else:
                raise AssertionError(
                    'You try to save `content` without initially retrieving '
                    'it. '
                    'This is not possible because of the vote updates. '
                    'Maybe you have to update your only() or defer() call.'
                )

    class Meta(AbstractSegmentModel.Meta):
        verbose_name = _('translated segment')
        verbose_name_plural = _('translated segments')
        unique_together = ('work', 'position')
        # Needed for the admin panel (select_related)
        index_together = ('position', 'work', 'original')


class Vote(models.Model):
    """
    Vote by translator, reviewer or trustee.
    """

    # I decided to not use simple_history to track changes because
    # 1. votes will be cached, most of the hits will be for writing
    # 2. writing means 3 - 5 db hits with a history table
    # 3. a bigger table (meaning longer read queries) should not be problematic
    #    because of caching
    # 4. I'll need similar code to implement caching I need now without history
    # For details see the Jupyter notebook on queries.
    segment = models.ForeignKey(
        TranslatedSegment,
        verbose_name=_('segment'),
        related_name='votes',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    # This is a many to many relation because we can have several historical
    # records with the same votes after restoring an older version and
    # editing it. Not copying the vote prevents having copies of the same vote
    # in the timeline. We could filter them out but I think this implementation
    # is a DRY and thereby the best solution.
    historical_segments = models.ManyToManyField(
        TranslatedSegment.history.model,
        verbose_name=_('historical segment'),
        related_name='votes',
        blank=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('user'),
        related_name='votes',
        on_delete=models.PROTECT,
    )
    role = models.CharField(_('role'), choices=ROLES, max_length=10)
    value = models.SmallIntegerField(
        _('value'), choices=((-2, '-2'), (-1, '-1'), (1, '+1'), (2, '+2'))
    )
    revoke = models.BooleanField(
        _('revoke'),
        default=False,
        help_text=_(
            'Only true if this vote resets the total vote of the user, '
            'segment and role to 0, not in case of opposite votes.'
        ),
    )
    date = models.DateTimeField(_('date'), default=timezone.now)

    @property
    def created(self):
        return self.date

    @property
    def action(self):
        if self.revoke:
            assert abs(self.value) == 1, 'Revokes should have a value == 1'
            self.assessment = 0
            if self.value == 1:
                return 'revoked disapproval'
            return 'revoked approval'
        else:
            if self.value >= 1:
                self.assessment = 1
                return 'approved'
            self.assessment = -1
            return 'disapproved'

    def __str__(self):
        return str(self.value) if self.value < 0 else '+{}'.format(self.value)

    class Meta:
        verbose_name = _('vote')
        verbose_name_plural = _('votes')
        get_latest_by = 'date'
        # TODO in every language!
        # permissions = (('vote_as_trustee', _('Can vote as trustee')),)


class BaseTranslator(TimestampsModel):
    name = models.CharField(_('name'), max_length=40, unique=True)
    type = models.CharField(
        _('type'),
        max_length=5,
        choices=(
            ('hb', 'human being'),
            ('tm', 'translation memory'),
            ('ai', 'artificial intelligence'),
        ),
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('base translator')
        verbose_name_plural = _('base translators')


class BaseTranslation(TimestampsModel):
    """
    AI and imported translations to work on.
    """

    translator = models.ForeignKey(
        BaseTranslator, verbose_name=_('translator'), on_delete=models.PROTECT
    )
    language = models.CharField(
        _('language'),
        max_length=7,
        choices=get_languages(lazy=True),
        db_index=True,
    )

    def __str__(self):
        return '{} – {}'.format(self.translator, self.get_language_display())

    class Meta:
        verbose_name = _('base translation')
        verbose_name_plural = _('base translations')
        unique_together = ('translator', 'language')


class BaseTranslationSegment(TimestampsModel):
    original = models.ForeignKey(
        OriginalSegment,
        verbose_name=_('original'),
        related_name='basetranslations',
        on_delete=models.PROTECT,
    )
    translation = models.ForeignKey(
        BaseTranslation,
        verbose_name=_('translation'),
        related_name='translations',
        on_delete=models.PROTECT,
    )
    content = models.TextField(_('content'))

    def __str__(self):
        return str(self.original)

    class Meta:
        verbose_name = _('base translation segment')
        verbose_name_plural = _('base translation segments')
        unique_together = ('original', 'translation')


class SegmentDraft(models.Model):
    """
    Draft of a translated segment.
    """

    # Which values to store
    #
    # API
    # The API should be structured in a way which is easy to comprehend in
    # order to reduce mistakes.
    # Therefore it's better to post drafts at the segment URL rather having a
    # flat and indepentent draft API.
    # Thereby you have the work id and the position but not the segment ID.
    #
    # Usage
    # 1. Creation by API (a lot, may be cached and stored every minute or so)
    #     - work ID, position
    # 2. Retreive for commits (often, may be cached completely)
    #     - creation, owner, segment
    # 3. Edits which need reviews (often, may be cached)
    # 4. List drafts of a segment for a user (sometimes, may be cached)
    #     - work ID, position
    # 5. Delete obsolete drafts (sometimes)
    #     - creation
    # 6. Health checks (sometimes)
    #     - segment
    #
    # Conclusion
    # Store work ID and position, excluding position ID.
    # TODO As soon as cache is active. Rethink reviews (3.) and maybe
    # permissions before.
    # TODO or maybe keep it. I could also do a check if position, work and
    # segment match with post requests. But I think this is overkill.

    created = models.DateTimeField(_('date created'), default=timezone.now)
    # snapshots = ArrayField(
    #    JSONField(), <- bad idea
    #    verbose_name=_('snapshots'),
    #    default=list,
    # )
    content = models.TextField(_('content'), blank=True)
    segment = models.ForeignKey(
        TranslatedSegment,
        verbose_name=_('segment'),
        related_name='drafts',
        on_delete=models.PROTECT,
    )
    # TODO remove work or segment
    work = models.ForeignKey(
        TranslatedWork,
        verbose_name=_('work'),
        related_name='drafts',
        on_delete=models.PROTECT,
    )
    position = models.PositiveIntegerField(_('position'), db_index=True)
    # @property
    # def position(self):
    #    return self.segment.position

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('owner'),
        related_name='drafts',
        on_delete=models.CASCADE,
    )

    def clean(self):
        """
        Don't allow new drafts on obsolete content.
        """
        if self.owner_id != self.segment.locked_by_id:
            raise ValidationError(
                _('This segment is currently locked by another user.')
            )

    def __str__(self):
        # return '{} {}'.format(self.work.abbreviation, self.owner)
        return self.segment.reference

    class Meta(TimestampsModel.Meta):
        verbose_name = _('translated segment draft')
        verbose_name_plural = _('translated segment drafts')


class SegmentComment(TimestampsModel):
    """
    Comment refering to a segment.
    """

    # issue = models.ForeignKey(
    #    Issue,
    #    verbose_name=_('issue'),
    #    related_name='comments',
    #    on_delete=models.PROTECT,
    # )
    work = models.ForeignKey(
        TranslatedWork,
        verbose_name=_('work'),
        related_name='segmentcomments',
        on_delete=models.PROTECT,
    )
    position = models.PositiveIntegerField(_('position'), db_index=True)
    # TODO Markdown
    content = models.TextField(
        _('content'), max_length=2000, help_text=UNTRUSTED_HTML_WARNING
    )
    role = models.CharField(_('role'), choices=ROLES, max_length=10)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('user'),
        related_name='segmentcomments',
        on_delete=models.PROTECT,
    )
    vote = models.ForeignKey(
        Vote,
        verbose_name=_('vote'),
        related_name='segmentcomments',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    to_delete = models.DateTimeField(_('to delete'), null=True, blank=True)

    def __str__(self):
        return Truncator(self.content).chars(10)

    @property
    def segment(self):
        segment = (
            TranslatedSegment.objects.filter(
                work_id=self.work_id, position=self.position
            )
            .select_related('chapter', 'work', 'original')
            .get()
        )
        return segment

    class Meta(TimestampsModel.Meta):
        verbose_name = _('segment comment')
        verbose_name_plural = _('segment comments')


# TODO OriginalReference in order to be able to join them and get the correct
# reference automatically in an paragraph while translating?
class Reference(TimestampsModel, VersionModel):
    """
    Information about a work.
    """

    title = models.CharField(_('title'), max_length=100, blank=True)
    type = models.CharField(_('type'), max_length=20, blank=True)
    abbreviation = models.CharField(
        _('abbreviation'),
        max_length=15,
        db_index=True,
        blank=True,
        # TODO check for unique
    )
    # TODO order last name, first name?
    author = models.CharField(_('author'), max_length=100, blank=True)
    published = models.CharField(_('published in'), max_length=11, blank=True)
    language = models.CharField(
        _('language'),
        max_length=7,
        choices=get_languages(lazy=True),
        db_index=True,
    )

    def __str__(self):
        return self.title or self.abbreviation

    class Meta:
        verbose_name = _('reference')
        verbose_name_plural = _('references')
        # unique_together = ('title', 'author', 'published', 'language')


# class Issue(TimestampsModel, VersionModel):
#    """
#    Discussion for a translation.
#    """
#    headline = models.CharField(_('headline'), max_length=100)
#    work = models.ForeignKey(
#        TranslatedWork,
#        verbose_name=_('work'),
#        on_delete=models.CASCADE,
#    )
#
#    def __str__(self):
#        return self.headline
#
#    class Meta(TimestampsModel.Meta):
#        verbose_name = _('issue')
#        verbose_name_plural = _('issues')

# class Cachet(VersionModel, models.Model):
#    """
#    A label describing the quality of a translation.
#    """
#    title = models.CharField(_('title'), max_length=20, unique=True)
#    kind = models.CharField(
#        _('kind'),
#        max_length=2,
#        choices=(('tr', _('trustee')), ('rv', _('reviewer'))),
#    )
#            # TODO Talk about these choices with Lukas
#    description = models.TextField(_('description'))
#
#    # TODO We could also implement that hardcoded (a class), also Badges.
#
#    def __str__(self):
#        return self.title
#
#    class Meta:
#        verbose_name = _('cachet')
#        verbose_name_plural = _('cachets')
#
# class Definition(VersionModel, models.Model):
#    """
#    A definition for the glossary.
#    """
#    phrase = models.CharField(
#        _('phrase'), max_length=100, db_index=True, unique=True)
#    # TODO markdown
#    # TODO trustee specific?
#    explanation = models.TextField(_('explanation'))
#
#    def __str__(self):
#        return self.phrase
#
#    class Meta:
#        verbose_name = _('definition')
#        verbose_name_plural = _('definitions')

# TODO Publisher? Who will maintain that? The Guardians of the work
# or the publisher?
# In latter case I'd create a model.


# Models for caching
# ==================


class ImportantHeading(models.Model):
    # Not using a materialized view here because
    # - you cannot update it subsequently what I prefer because most chapters
    #   won't change every hour
    # - it's hard to implement the headings include feature on SQL level

    segment = models.OneToOneField(
        TranslatedSegment,
        verbose_name=_('segment'),
        related_name='important_heading',
        on_delete=models.CASCADE,
    )
    number = models.PositiveSmallIntegerField(
        _('number'), null=True, blank=True
    )
    first_position = models.PositiveIntegerField(
        _('first position'), null=True, blank=True
    )
    position = models.PositiveIntegerField(_('position'))
    tag = models.CharField(_('tag'), max_length=10)
    classes = ArrayField(
        models.CharField(max_length=30),
        verbose_name=_('classes'),
        default=list,
        blank=True,
    )
    content = models.TextField(_('content'))
    pretranslated = models.PositiveSmallIntegerField(
        _('pretranslated'), null=True, blank=True
    )
    translation_done = models.PositiveSmallIntegerField(
        _('translaton done'), null=True, blank=True
    )
    review_done = models.PositiveSmallIntegerField(
        _('review done'), null=True, blank=True
    )
    trustee_done = models.PositiveSmallIntegerField(
        _('trustee done'), null=True, blank=True
    )
    work = models.ForeignKey(
        TranslatedWork,
        verbose_name=_('work'),
        related_name=_('important_headings'),
        on_delete=models.CASCADE,
    )
    segments_count = models.PositiveIntegerField(
        _('segments count'), null=True, blank=True
    )
    date = models.DateTimeField(
        _('date'),
        help_text=_(
            'last_modified of the segment in the current chapter with the most '
            'recent modification when last updated.'
        ),
    )

    class Meta:
        verbose_name = _('important heading')
        verbose_name_plural = _('important headings')
        unique_together = (('work', 'number'),)
        # An 'ordering' leads to an unexpected 'LEFT OUTER JOIN' when you
        # group votes by chapter (in Django 2.0)

    @classmethod
    def insert(cls, work, save=True):
        """
        Creates important headings for given work.
        """
        # Assumes that every work begins with a heading

        # Prepare segments
        chapters = []
        prev_heading = None
        prev_position = work.segments_count + 1
        prev_level = 0
        headings = tuple(cls.get_headings(work))
        multiple_headings = len(headings) > 1
        one_h1 = len([True for h in headings if h.tag == 'h1']) == 1
        few = 3

        for h in headings:
            is_first = h is headings[-1]

            if is_first:
                # Exclude the title
                exclude_title = h.tag == 'h1' and one_h1 and multiple_headings
                # Exclude year in manuscripts
                exclude_year = (
                    work.type == work.MANUSCRIPT
                    and h.original.content.isdigit()
                )
                if exclude_title or exclude_year:
                    prev_heading.segments_count += prev_position - 1
                    prev_heading.first_position = 1
                    continue

            # Include segments of the previous chapter in the current chapter
            # if these are a few only and the current heading is higher in
            # hierarchy
            level = int(h.tag[1])
            if h.position < prev_position - few or level >= prev_level:
                h.segments_count = prev_position - h.position
                h.first_position = h.position
                prev_heading = h
            else:
                prev_heading.segments_count += prev_position - h.position
                prev_heading.first_position = h.position
                h.segments_count = None
                h.first_position = None

            chapters.append(h)
            prev_position = h.position
            prev_level = level

        # Build headings
        chapters.reverse()
        objects = []
        last_number = 0

        for h in chapters:
            if h.first_position:
                last_number += 1
                number = last_number
            else:
                number = None
            objects.append(
                cls(
                    segment=h,
                    number=number,
                    first_position=h.first_position,
                    position=h.position,
                    tag=h.tag,
                    classes=h.classes,
                    work=work,
                    segments_count=h.segments_count,
                    date=h.last_modified,
                )
            )

        if not save:
            return objects

        with transaction.atomic():
            # Save headings
            objects = cls.objects.bulk_create(objects)

            # Add segments
            for obj in objects:
                if obj.first_position:
                    # Add the 'chapter' to all segments from 'first_position'
                    # to the end of the chapter
                    segments = work.segments.filter(
                        position__gte=obj.first_position,
                        position__lt=obj.first_position + obj.segments_count,
                    )
                    segments.update(chapter_id=obj.pk)
                    TranslatedSegment.history.filter(
                        id__in=segments.values('pk')
                    ).update(chapter=obj)

            # Add content and statistics

            if BaseTranslation.objects.filter(language=work.language).exists():
                # Have to do it after creating the segments
                for heading in objects:
                    heading.update_pretranslated()

            # It turned out that it is too complex to add them directly because
            # of the last chapter: How to get the end of it for the filtering?
            cls.update(cls.objects.filter(pk__in=[o.pk for o in objects]))

        return objects

    @classmethod
    def get_headings(cls, work):
        """
        Returns a queryset of segments containing headings.
        """
        headings = (
            work.segments.filter(tag__in=IMPORTANT_HEADINGS)
            .order_by('-position')
            .only(
                'pk',
                'position',
                'tag',
                'classes',
                'original',
                'work',
                'last_modified',
            )
        )
        if work.type == work.MANUSCRIPT:
            headings = headings.select_related('original')
        return headings

    @classmethod
    def update(cls, queryset=None):
        """
        Updates the content and the statistics.

        To update more fields, simply delete all rows of the work.
        """
        queryset = queryset or cls.objects.distinct().filter(
            Q(segment__last_modified__gt=F('date'))
            | Q(segments__last_modified__gt=F('date'))
        )
        count = queryset.update(
            content=Subquery(
                # 'content' can't be used directly because it's a field
                # https://code.djangoproject.com/ticket/28072
                TranslatedSegment.objects.filter(pk=OuterRef('segment_id'))
                .annotate(
                    proper_content=Func(
                        Case(
                            When(~Q(content=''), then='content'),
                            default='original__content',
                        ),
                        Value('<[^>]+>'),
                        Value(''),
                        Value('g'),
                        function='regexp_replace',
                    )
                )
                .values('proper_content')[:1]
            ),
            translation_done=cls.get_statistics_subquery(TRANSLATION_DONE),
            review_done=cls.get_statistics_subquery(REVIEW_DONE),
            trustee_done=cls.get_statistics_subquery(TRUSTEE_DONE),
            date=Case(
                When(
                    ~Q(first_position=None),
                    then=Subquery(
                        TranslatedSegment.objects.filter(
                            chapter_id=OuterRef('pk')
                        )
                        .order_by('-last_modified')
                        .values('last_modified')[:1]
                    ),
                ),
                default=Subquery(
                    TranslatedSegment.objects.filter(
                        important_heading=OuterRef('pk')
                    ).values('last_modified')[:1]
                ),
            ),
        )
        return count

    @classmethod
    def get_statistics_subquery(cls, progress):
        subquery = Case(
            When(
                ~Q(first_position=None),
                then=queries.SubqueryCount(
                    TranslatedSegment.objects.filter(
                        chapter_id=OuterRef('pk'), progress__gte=progress
                    )
                ),
            )
        )
        return subquery

    def update_pretranslated(self):
        """
        Updates the pretranslated field of the chapter.
        """
        originals = self.segments.values('original')
        pretranslated = BaseTranslationSegment.objects.filter(
            original__in=originals, translation__language=self.work.language
        ).count()
        if self.pretranslated != pretranslated:
            self.pretranslated = pretranslated
            self.save()
        return self.pretranslated

    def __str__(self):
        return self.content


class WorkStatistics(models.Model):
    work = models.OneToOneField(
        TranslatedWork,
        verbose_name=_('work'),
        related_name='statistics',
        on_delete=models.CASCADE,
    )
    segments = models.PositiveIntegerField(_('segments'))
    pretranslated_count = models.PositiveIntegerField(
        _('pretranslated'), default=0
    )
    translated_count = models.PositiveIntegerField(_('translated'), default=0)
    reviewed_count = models.PositiveIntegerField(_('reviewed'), default=0)
    authorized_count = models.PositiveIntegerField(_('authorized'), default=0)
    pretranslated_percent = models.DecimalField(
        _('pretranslated (%)'), default=0, max_digits=5, decimal_places=2
    )
    translated_percent = models.DecimalField(
        _('translated (%)'), default=0, max_digits=5, decimal_places=2
    )
    reviewed_percent = models.DecimalField(
        _('reviewed (%)'), default=0, max_digits=5, decimal_places=2
    )
    authorized_percent = models.DecimalField(
        _('authorized (%)'), default=0, max_digits=5, decimal_places=2
    )
    contributors = models.PositiveSmallIntegerField(
        _('contributors'), default=0
    )
    last_activity = models.DateTimeField(
        _('last activity'),
        null=True,
        blank=True,
        help_text=_('`last_modified` of the last modified segment.'),
    )

    @classmethod
    def insert(cls, work):
        """
        Creates a statistics row for given translated work.
        """
        params = work.update_pretranslated(chapters=False, save=False)
        instance = cls.objects.create(
            work=work, segments=work.segments_count, **params
        )
        return instance

    @classmethod
    def update(cls, queryset=None) -> int:
        """
        Updates statistics for given queryset or all rows.
        """
        queryset = queryset or cls.objects.distinct().filter(
            Q(work__important_headings__date__gt=F('last_activity'))
            | Q(last_activity=None)
        )
        count = queryset.update(
            translated_count=cls.get_query_count('translation'),
            reviewed_count=cls.get_query_count('review'),
            authorized_count=cls.get_query_count('trustee'),
            translated_percent=cls.get_query_percent('translation'),
            reviewed_percent=cls.get_query_percent('review'),
            authorized_percent=cls.get_query_percent('trustee'),
            contributors=queries.SubqueryCount(
                get_user_model()
                .objects.filter(
                    historicaltranslatedsegments__work_id=OuterRef('work_id')
                )
                .distinct()
            ),
            last_activity=Subquery(
                ImportantHeading.objects.filter(work_id=OuterRef('work_id'))
                .order_by('-date')
                .values('date')[:1]
            ),
        )
        return count

    @classmethod
    def get_query_count(cls, task):
        query = queries.SubquerySum(
            ImportantHeading.objects.filter(work_id=OuterRef('work_id')),
            field=f'{task}_done',
        )
        return query

    @classmethod
    def get_query_percent(cls, task):
        query = ExpressionWrapper(
            cls.get_query_count(task) * 100.0 / F('segments'),
            output_field=models.DecimalField(),
        )
        return query

    @classmethod
    def update_pretranslated(cls, *languages):
        """
        Updates the pretranslated stats fields for all works in given languages.
        """
        works = (
            TranslatedWork.objects.filter(language__in=languages)
            .select_related('statistics')
            .annotate(pretranslated=Sum('important_headings__pretranslated'))
        )
        for work in works:
            work.update_pretranslated()

    def __str__(self):
        return f'{self.work.title} ({self.work.language})'

    class Meta:
        verbose_name = _('work statistics')
        verbose_name_plural = _('work statistics')
