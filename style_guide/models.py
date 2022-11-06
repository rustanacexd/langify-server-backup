from base.constants import UNTRUSTED_HTML_WARNING, get_languages
from base.history import HistoricalRecords
from base.models import TimestampsModel
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.utils.text import Truncator
from django.utils.translation import gettext_lazy as _
from style_guide import utils


class StyleGuide(TimestampsModel):
    """
    Community style guide content class
    """

    title = models.CharField(_('title'), max_length=150)
    content = models.TextField(
        _('content'), default=utils.get_styleguide_content_from_template
    )
    language = models.CharField(
        _('language'),
        max_length=7,
        choices=get_languages(lazy=True) + [('default', _('Default'))],
        unique=True,
    )

    history = HistoricalRecords()

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.title:
            self.title = utils.get_styleguide_title(self.language)
        self.content = utils.normalize_string(self.content)
        return super().save(*args, **kwargs)

    class Meta(TimestampsModel.Meta):
        verbose_name = _('style guide')
        verbose_name_plural = _('style guides')


class Tag(models.Model):
    """
    Tags for tagging.
    """

    name = models.CharField(_('name'), max_length=40, unique=True)
    slug = models.SlugField(_('slug'), max_length=40, unique=True)

    def __str__(self):
        return self.name


class Issue(TimestampsModel):
    """
    User created issues for community style guides.
    """

    title = models.CharField(
        _('title'), max_length=150, help_text=UNTRUSTED_HTML_WARNING
    )
    content = models.TextField(_('content'), help_text=UNTRUSTED_HTML_WARNING)
    diff = models.TextField(
        _('difference'),
        blank=True,
        default='',
        help_text=UNTRUSTED_HTML_WARNING,
    )
    style_guide = models.ForeignKey(
        StyleGuide,
        verbose_name=_('style guide'),
        related_name='issues',
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('user'),
        related_name='issues',
        on_delete=models.PROTECT,
    )
    tags = models.ManyToManyField(
        Tag, verbose_name=_('tags'), related_name='issues', blank=True
    )
    is_from_style_guide = models.BooleanField(default=False)

    history = HistoricalRecords(
        excluded_fields=('user', 'tags', 'created', 'last_modified')
    )

    def __str__(self):
        return self.title

    class Meta(TimestampsModel.Meta):
        verbose_name = _('issue')
        verbose_name_plural = _('issues')


class IssueComment(TimestampsModel):
    """
    Comment for issues.
    """

    # TODO Markdown
    content = models.TextField(
        'content', max_length=2000, help_text=UNTRUSTED_HTML_WARNING
    )
    issue = models.ForeignKey(
        Issue,
        verbose_name=_('issues'),
        related_name='comments',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    user = models.ForeignKey(
        get_user_model(),
        verbose_name=_('user'),
        related_name='issuecomments',
        on_delete=models.PROTECT,
    )
    to_delete = models.DateTimeField('to delete', blank=True, null=True)

    def __str__(self):
        return Truncator(self.content).chars(10)

    class Meta(TimestampsModel.Meta):
        verbose_name = _('issue comment')
        verbose_name_plural = _('issue comments')


class IssueReaction(TimestampsModel):
    """
    Reaction for issues.
    """

    content = models.CharField(
        'content', max_length=20, help_text=UNTRUSTED_HTML_WARNING
    )
    issue = models.ForeignKey(
        Issue,
        verbose_name=_('reactions'),
        related_name='reactions',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    user = models.ForeignKey(
        get_user_model(),
        verbose_name=_('user'),
        related_name='issuereactions',
        on_delete=models.PROTECT,
    )

    def __str__(self):
        return Truncator(self.content).chars(10)

    class Meta(TimestampsModel.Meta):
        verbose_name = _('issue reaction')
        verbose_name_plural = _('issue reactions')
        unique_together = ('user', 'content', 'issue')
