from django.db import models
from django.utils.translation import gettext_lazy as _
from panta.models import OriginalSegment


class Tag(models.Model):
    name = models.CharField(_('name'), max_length=10, unique=True)
    # p, div, span, egw-noauthor-preface
    segments = models.ManyToManyField(
        OriginalSegment, verbose_name=_('segments'), related_name='all_tags'
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('tag')
        verbose_name_plural = _('tags')


class Class(models.Model):
    name = models.CharField(_('name'), max_length=40)
    tag = models.ForeignKey(
        Tag,
        verbose_name=_('tag'),
        on_delete=models.CASCADE,
        related_name='classes',
    )
    segments = models.ManyToManyField(
        OriginalSegment, verbose_name=_('segments'), related_name='all_classes'
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('class')
        verbose_name_plural = _('classes')
        unique_together = ('name', 'tag')


class OriginalSentence(models.Model):
    content = models.TextField(_('content'), unique=True)
    count = models.PositiveSmallIntegerField(_('count'), default=0)
    segments = models.ManyToManyField(
        OriginalSegment,
        through='OriginalSegmentSentenceRelation',
        verbose_name=_('segments'),
        related_name='sentences',
    )
    created = models.DateTimeField(_('date created'), auto_now_add=True)

    def __str__(self):
        return self.content

    class Meta:
        verbose_name = _('original sentence')
        verbose_name_plural = _('original sentences')


class OriginalSegmentSentenceRelation(models.Model):
    segment = models.ForeignKey(OriginalSegment, on_delete=models.CASCADE)
    sentence = models.ForeignKey(OriginalSentence, on_delete=models.CASCADE)
    number = models.PositiveSmallIntegerField()
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('segment', 'number')
