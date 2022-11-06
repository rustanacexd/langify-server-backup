from django.db.models import Prefetch
from django.db.models.signals import post_save
from django.dispatch import receiver
from misc.utils import add_task_for_comments_deletion

from . import models


@receiver(
    post_save,
    sender=models.TranslatedWork,
    dispatch_uid='create_segments_and_database_cache',
)
def create_segments_and_database_cache(sender, **kwargs):
    """
    Creates segments, headings and statistics of the translated work in advance.

    Also creates historical records for base translations.
    """
    if not kwargs['created'] or kwargs['raw']:
        return
    instance = kwargs['instance']
    if not getattr(instance, '_create_segments', True):
        return

    # Create segments
    ai_segments = models.BaseTranslationSegment.objects.filter(
        translation__language=instance.language,
        translation__translator__type='ai',
    ).select_related('translation__translator')
    prefetch = Prefetch('basetranslations', queryset=ai_segments, to_attr='ai')
    original_segments = models.OriginalSegment.objects.filter(
        work_id=instance.original_id
    ).prefetch_related(prefetch)
    new_segments = []
    for orig_segment in original_segments:
        new_segments.append(
            models.TranslatedSegment(
                position=orig_segment.position,
                page=orig_segment.page,
                tag=orig_segment.tag,
                classes=orig_segment.classes,
                reference=orig_segment.reference,
                work=instance,
                original=orig_segment,
            )
        )
    models.TranslatedSegment.objects.bulk_create(new_segments)

    # Add historical records for segments which have a base translation
    # A second loop because we have the PKs now
    historical_records = []
    for orig_segment, segment in zip(original_segments, new_segments):
        assert isinstance(orig_segment.ai, list)
        if orig_segment.ai:
            assert (
                len(orig_segment.ai) == 1
            ), 'Multiple base translations not supported.'
            segment.add_to_history(
                relative_id=1,
                content=orig_segment.ai[0].content,
                history_type='+',
                history_date=orig_segment.ai[0].last_modified,
                history_change_reason='{} translation'.format(
                    orig_segment.ai[0].translation.translator
                ),
                add_to=historical_records,
            )
    models.TranslatedSegment.history.bulk_create(historical_records)

    # Create headings
    models.ImportantHeading.insert(instance)

    # Create work statistics
    models.WorkStatistics.insert(instance)


@receiver(
    post_save,
    sender=models.SegmentComment,
    dispatch_uid='schedule_segment_comment_deletion',
)
def schedule_segment_comment_deletion(sender, **kwargs):
    """
    Triggers a Celery task if the comment has a TTL.
    """
    add_task_for_comments_deletion(kwargs)
