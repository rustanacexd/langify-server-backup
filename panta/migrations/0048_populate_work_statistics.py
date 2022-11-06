from django.db import migrations, transaction
from django.db.models import (
    Count,
    DecimalField,
    ExpressionWrapper,
    F,
    OuterRef,
    Subquery,
)
from panta import queries


def populate_work_of_historical_segments(apps, schema_editor):
    TranslatedSegment = apps.get_model('panta', 'TranslatedSegment')
    HistoricalTranslatedSegment = apps.get_model(
        'panta', 'HistoricalTranslatedSegment'
    )
    HistoricalTranslatedSegment.objects.update(
        work_id=Subquery(
            TranslatedSegment.objects.filter(pk=OuterRef('id')).values(
                'work_id'
            )[:1]
        )
    )


def add_work_statistics(apps, schema_editor):
    ImportantHeading = apps.get_model('panta', 'ImportantHeading')
    TranslatedWork = apps.get_model('panta', 'TranslatedWork')
    WorkStatistics = apps.get_model('panta', 'WorkStatistics')
    User = apps.get_model('path', 'User')

    def get_query_count(task):
        query = queries.SubquerySum(
            ImportantHeading.objects.filter(work_id=OuterRef('work_id')),
            field=f'{task}_done',
        )
        return query

    def get_query_percent(task):
        query = ExpressionWrapper(
            get_query_count(task) * 100.0 / F('segments'),
            output_field=DecimalField(),
        )
        return query

    works = TranslatedWork.objects.all().annotate(
        segments_count=Count('segments')
    )

    statistics = (
        WorkStatistics(work=w, segments=w.segments_count) for w in works
    )

    with transaction.atomic():
        WorkStatistics.objects.bulk_create(statistics)

        WorkStatistics.objects.update(
            translated_count=get_query_count('translation'),
            reviewed_count=get_query_count('review'),
            authorized_count=get_query_count('trustee'),
            translated_percent=get_query_percent('translation'),
            reviewed_percent=get_query_percent('review'),
            authorized_percent=get_query_percent('trustee'),
            contributors=queries.SubqueryCount(
                User.objects.filter(
                    historicaltranslatedsegments__work_id=OuterRef('work_id')
                ).distinct()
            ),
            last_activity=Subquery(
                ImportantHeading.objects.filter(work_id=OuterRef('work_id'))
                .order_by('-date')
                .values('date')[:1]
            ),
        )


class Migration(migrations.Migration):

    dependencies = [
        ('panta', '0047_auto_20190507_1402'),
        ('path', '0020_auto_20190408_1001'),
    ]

    operations = [
        migrations.RunPython(populate_work_of_historical_segments),
        migrations.RunPython(add_work_statistics),
    ]
