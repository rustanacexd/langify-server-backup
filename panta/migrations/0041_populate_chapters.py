from django.db import migrations, transaction
from django.db.models import OuterRef, Subquery
from django.utils import timezone


def populate_chapters(apps, schema_editor):
    TranslatedSegment = apps.get_model('panta', 'TranslatedSegment')
    HistoricalTranslatedSegment = apps.get_model(
        'panta', 'HistoricalTranslatedSegment'
    )
    ImportantHeading = apps.get_model('panta', 'ImportantHeading')

    with transaction.atomic():
        TranslatedSegment.objects.update(
            chapter_id=Subquery(
                ImportantHeading.objects.filter(
                    segments__pk=OuterRef('pk')
                ).values('pk')[:1]
            )
        )
        # Change historical data for translated segments
        HistoricalTranslatedSegment.objects.update(
            chapter_id=Subquery(
                ImportantHeading.objects.filter(
                    segments__pk=OuterRef('id')
                ).values('pk')[:1]
            )
        )


class Migration(migrations.Migration):
    dependencies = [('panta', '0040_translatedsegment_chapter')]
    operations = [migrations.RunPython(populate_chapters)]
