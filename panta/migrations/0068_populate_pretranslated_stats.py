from django.db import migrations
from django.db.models import Sum


def populate_pretranslated(apps, schema_editor):
    BaseTranslation = apps.get_model('panta', 'BaseTranslation')
    BaseTranslationSegment = apps.get_model('panta', 'BaseTranslationSegment')
    TranslatedWork = apps.get_model('panta', 'TranslatedWork')

    def update_pretranslated_chapter(chapter):
        """
        Updates the pretranslated field of the chapter.
        """
        originals = chapter.segments.values('original')
        pretranslated = BaseTranslationSegment.objects.filter(
            original__in=originals, translation__language=chapter.work.language
        ).count()
        if chapter.pretranslated != pretranslated:
            chapter.pretranslated = pretranslated
            chapter.save()
        return chapter.pretranslated

    def update_pretranslated_work(work, chapters=True, save=True):
        """
        Updates statistics.pretranslated of the work.
        """
        count = 0
        for chapter in work.important_headings.all():
            count += update_pretranslated_chapter(chapter)
        segments = work.statistics.segments
        if segments:
            percent = count * 100.0 / segments
        else:
            percent = 0
        stats = {'pretranslated_count': count, 'pretranslated_percent': percent}
        if work.statistics.pretranslated_count != count:
            for k, v in stats.items():
                setattr(work.statistics, k, v)
            work.statistics.save()

    languages = BaseTranslation.objects.values_list('language', flat=True)

    works = (
        TranslatedWork.objects.filter(language__in=languages)
        .select_related('statistics')
        .annotate(pretranslated=Sum('important_headings__pretranslated'))
    )
    for work in works:
        update_pretranslated_work(work)


class Migration(migrations.Migration):

    dependencies = [('panta', '0067_auto_20190828_0858')]

    operations = [migrations.RunPython(populate_pretranslated)]
